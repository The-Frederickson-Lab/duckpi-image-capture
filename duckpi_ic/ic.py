"""Contains code for moving actuator, camera selection, and image capture"""

from enum import Enum
import logging
import os
from pathlib import Path
import shutil
import sys
from tempfile import mkstemp
import time
import traceback
from typing import List, Optional

from fabric import Connection as FabricConnection
from picamera2 import Picamera2
import RPi.GPIO as gp
from zaber_motion import Library, Units
from zaber_motion.ascii import Axis, Connection
from zaber_motion.units import LengthUnits


from duckpi_ic.settings import settings
from duckpi_ic.util import (
    read_and_validate_config,
    send_error_email,
    send_success_email,
    set_logger_debug,
)


logger = logging.getLogger(__name__)

Library.enable_device_db_store()

DEVICE_PORT = settings.DEVICE_PORT


# camera order from door: C (2), A (0), B (1), D (3)
# maybe? seems different when we use picamera2
class Cameras(Enum):
    A = 0
    B = 1
    C = 2
    D = 3


class DuckCam(Picamera2):
    def __init__(self, cam: Cameras, tuning=None):
        setup_gpio_pins()
        start_camera(cam.name)

        super().__init__(
            camera_num=cam.value,
            tuning=tuning,
        )

    def stop(self):
        logger.debug("Cleaning up pins")
        gp.cleanup()
        super().stop()


def set_axis_defaults(
    axis: Axis,
    acceleration: int = 2,
    deceleration: int = 2,
    max_speed: int = 20,
) -> None:
    """Set actuator defaults

    :param axis: the axis whose settings we want to set
    :type axis: Axis
    :param acceleration: defaults to 2
    :type acceleration: int, optional
    :param deceleration:  defaults to 2
    :type deceleration: int, optional
    :param device_port: defaults to DEVICE_PORT
    :type device_port: str, optional
    :param max_speed: defaults to 20
    :type max_speed: int, optional
    """
    # set to gentle maximum speed
    axis.settings.set("maxspeed", max_speed, Units.VELOCITY_MILLIMETRES_PER_SECOND)
    # set to gentle acceleration
    axis.settings.set("motion.accelonly", acceleration, Units.NATIVE)
    # set to gentle deceleration
    axis.settings.set("motion.decelonly", deceleration, Units.NATIVE)


def home_actuator(device_port: str = DEVICE_PORT) -> None:
    """Set actuator to default position

    :param device_port: The actuator's port, defaults to DEVICE_PORT
    :type device_port: str, optional
    """
    logger.debug("Resetting the actuator position")
    with Connection.open_serial_port(device_port) as connection:
        device_list = connection.detect_devices()
        axis = device_list[0].get_axis(1)
        set_axis_defaults(axis)
        axis.home()
        time.sleep(1)


def get_actuator_position(
    unit: LengthUnits = Units.LENGTH_MILLIMETRES, device_port: str = DEVICE_PORT
) -> float:
    """Get the current position of the actuator

    :param unit: The units to use, defaults to Units.LENGTH_MILLIMETRES
    :type unit: Unit, optional
    :param device_port: The device port, defaults to DEVICE_PORT
    :type device_port: str, optional
    :return: The actuator position
    :rtype: float
    """
    with Connection.open_serial_port(device_port) as connection:
        device_list = connection.detect_devices()
        axis = device_list[0].get_axis(1)
        return axis.get_position(unit=unit)


def move_actuator(
    distance: int,
    unit: Optional[LengthUnits] = None,
    device_port: str = DEVICE_PORT,
) -> float:
    """Move the actuator forward by the provided distance

    :param distance: How far to move the actuator
    :type distance: int
    :param unit: The unit of distance, defaults to Units.LENGTH_MILLIMETRES
    :type unit: LengthUnits, optional
    :param device_port: The actuator's port, defaults to DEVICE_PORT
    :type device_port: str, optional
    """
    with Connection.open_serial_port(device_port) as connection:
        device_list = connection.detect_devices()
        axis = device_list[0].get_axis(1)
        set_axis_defaults(axis)

        if unit is None:
            unit = Units.LENGTH_MILLIMETRES

        logger.debug(f"Moving actuator {distance} {unit}")
        axis.move_relative(distance, unit)
        time.sleep(1)
        return axis.get_position(unit=unit)


def move_actuator_relative(distance: int, unit: Optional[LengthUnits] = None) -> None:
    """Calculate relative distance after subtracting distance already covered

    :param distance: The distance from home
    :type distance: int
    :param unit: The unit to use, defaults to Units.LENGTH_MILLIMETRES
    :type unit: LengthUnits, optional
    """
    if unit is None:
        unit = Units.LENGTH_MILLIMETRES

    current_pos = round(get_actuator_position(unit))
    _distance = round(distance - current_pos)

    move_actuator(_distance, unit)


def setup_gpio_pins() -> None:
    """Put GPIO pins in default configuration"""
    logger.debug("setting up gpio pins")
    gp.cleanup()
    gp.setwarnings(True)
    gp.setmode(gp.BOARD)
    gp.setup(7, gp.OUT)
    gp.setup(11, gp.OUT)
    gp.setup(12, gp.OUT)
    gp.setup(15, gp.OUT)
    gp.setup(16, gp.OUT)
    gp.setup(21, gp.OUT)
    gp.setup(22, gp.OUT)
    gp.output(11, True)
    gp.output(12, True)
    gp.output(15, True)
    gp.output(16, True)
    gp.output(21, True)
    gp.output(22, True)


def start_camera(camera_id: str) -> None:
    """Start the indicated camera

    :param camera_id: The string identifier of the camera
    :type camera_id: Literal[&quot;A&quot;, &quot;B&quot;, &quot;C&quot;, &quot;D&quot;]
    :raises ValueError: If an invalid identifier was passed
    """

    if camera_id not in Cameras._member_names_:
        raise ValueError(f"{','.join(Cameras._member_names_)}, received {camera_id}")

    if camera_id == "A":
        logger.debug("Starting camera A")
        gp.output(7, False)
        gp.output(11, False)
        gp.output(12, True)
    elif camera_id == "B":
        logger.debug("Starting camera B")
        gp.output(7, True)
        gp.output(11, False)
        gp.output(12, True)
    elif camera_id == "C":
        logger.debug("Starting camera C")
        gp.output(7, False)
        gp.output(11, True)
        gp.output(12, False)
    elif camera_id == "D":
        logger.debug("Starting camera D")
        gp.output(7, True)
        gp.output(11, True)
        gp.output(12, False)

    time.sleep(1)


def take_stills(
    camera: Cameras, output_directory: str, base_filename: str, img_count: int
) -> List[str]:
    """Rest pins, start camera, take, and save photo

    :param camera: The camera to use
    :type camera: Cameras
    :param output_directory: Where to save the image
    :type output_directory: str
    :param base_filename: Path of the main local storage directory for this experiment
    :type base_filename: str
    :param img_count: The number of images to capture
    :type base_filename: int

    :return: The paths of the images
    :rtype: List[str]
    """

    output_file_path = os.path.join(
        output_directory, f"camera{camera.name}", make_filename_ts(base_filename)
    )

    Path(output_file_path).parent.mkdir(exist_ok=True, parents=True)

    logger.debug(f"Saving {img_count} images to {output_file_path}")

    with DuckCam(camera) as cam:
        cam.start_and_capture_files(
            name=output_file_path, num_files=img_count, show_preview=False
        )

    return [output_file_path.format(i) for i in range(img_count)]


def make_filename_base(camera: str, stage: int, row: int) -> str:
    return f"cam_{camera}_{stage}_{row}"


def make_filename_ts(filename_base) -> str:
    ts = time.strftime("%Y%m%d-%H%M%S")
    return f"{filename_base}_{ts}" + "_{:d}.jpg"


def move_files_to_remote(
    c: FabricConnection, local_paths: List[str], name: str
) -> List[str]:
    remote_save_dir = settings.REMOTE_SAVE_DIR
    relpaths = [os.path.sep.join(p.split(os.path.sep)[-2:]) for p in local_paths]
    remote_root = os.path.join(remote_save_dir, name)
    failures = []
    for relpath, local_path in zip(relpaths, local_paths):
        try:
            logger.debug(f"Moving {local_path} to {os.path.join(remote_root, relpath)}")
            c.put(local_path, os.path.join(remote_root, relpath))
            # logger.debug(f"deleting {local_path}")
            # os.remove(local_path)
        except Exception as e:
            logger.exception(e)
            failures.append(local_path)
    return failures


def update_first_last(first_last: List[str], local_paths: List[str]) -> None:
    first, last = first_last
    if os.stat(first).st_size == 0:
        shutil.copy2(local_paths[0], first)
    else:
        shutil.copy2(local_paths[-1], last)


def get_first_last_tmp_paths() -> List[str]:
    _, tmp1 = mkstemp(suffix=".jpg")
    _, tmp2 = mkstemp(suffix=".jpg")
    return [tmp1, tmp2]


def cleanup_first_last(filepaths: List[str]):
    for file in filepaths:
        logger.debug(f"Removing {file}")
        os.remove(file)


def send_email(
    success: bool,
    emails: List[str],
    experiment_name: str,
    message: str,
    first_last: List[str],
) -> None:
    fn = send_success_email if success else send_error_email

    fn(
        emails,
        experiment_name,
        message,
        first_last,
    )


def ensure_remote_dirs_exist(remote_host_name, experiment_name) -> None:
    remote_save_dir = settings.REMOTE_SAVE_DIR
    with FabricConnection(remote_host_name) as c:
        with c.cd(remote_save_dir):
            c.run(f"mkdir -p {experiment_name}")
            with c.cd(experiment_name):
                for cam in Cameras:
                    c.run(f"mkdir -p camera{cam.name}")


def make_unmoved_msg(unmoved_files: List[str]) -> str:
    msg = ""

    if len(unmoved_files):
        msg = (
            "The following files could not be saved remotely\n\n"
            + "\n".join(unmoved_files)
            + "\n\n"
        )

    return msg


def run_experiment(
    config_path: str,
    test: bool = False,
    debug: bool = False,
) -> List[str]:
    """Perform a run of the experiment

    :param config_path: The path to the experiment configuration
    :type config_path: str
    :param test: Whether or not this is a dry run (in which case no emails will be sent), defaults to False
    :type test: bool, optional
    :param debug: Whether to print debugging messages, defaults to False
    :type debug: bool, optional

    :return: The paths of the first and last images (only if testing)
    :rtype: List[str]
    """

    if debug:
        set_logger_debug(logger)

    experiment_config = read_and_validate_config(config_path)
    remote_host_name = settings.REMOTE_HOST_NAME

    experiment_name: str = experiment_config["name"]

    first_last = get_first_last_tmp_paths()

    local_save_dir: str = os.path.join(experiment_config["output_dir"], experiment_name)

    if not test:
        ensure_remote_dirs_exist(remote_host_name, experiment_name)

    unmoved_files = []

    email_msg = ""

    SUCCESS = True

    try:
        home_actuator()

        for i, stage in enumerate(experiment_config["stages"]):
            # stage_distance is distance from home, so we need to calculate relative to current position
            move_actuator_relative(
                stage["stage_distance"]["length"], stage["stage_distance"].get("units")
            )
            for row in range(stage["rows"]):
                # row_distance is relative to previous row and assumes distance is uniform between rows
                # don't move actuator on first row, since it's assumed the initial distance
                # is covered by stage_distance
                if row > 0:
                    move_actuator(
                        stage["row_distance"]["length"],
                        stage["row_distance"].get("units"),
                    )
                for camera in Cameras:

                    base_filename = make_filename_base(camera.name, i + 1, row + 1)
                    local_paths = take_stills(
                        camera,
                        local_save_dir,
                        base_filename,
                        experiment_config["number_of_images"],
                    )

                    update_first_last(first_last, local_paths)

                    if not test:
                        with FabricConnection(remote_host_name) as c:
                            logger.debug("Sending files to remote server")
                            _unmoved = move_files_to_remote(
                                c, local_paths, experiment_name
                            )

                            unmoved_files.extend(_unmoved)

    except Exception as e:
        logger.exception(e)
        exc_type, exc_value, exc_traceback = sys.exc_info()
        trace = "\n".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        )

        SUCCESS = False

        email_msg = str(e) + "\n\n" + trace

        raise

    finally:
        time.sleep(1)
        home_actuator()

        if not test:

            logger.debug(f"Sending {'success' if SUCCESS else 'error'} email")

            if SUCCESS:
                email_msg = "The experiment ran successfully."

            unmoved_msg = make_unmoved_msg(unmoved_files)

            message = unmoved_msg + email_msg

            send_email(
                SUCCESS,
                experiment_config["emails"],
                experiment_name,
                message,
                first_last,
            )

            cleanup_first_last(first_last)

    return first_last


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        prog="duckpi_ic.ic",
        description="Perform a run of a duckweed experiment",
    )

    parser.add_argument(
        "config_path",
        type=str,
        help="Path to a yml file that contains the configuration for the run",
    )

    parser.add_argument(
        "-t",
        "--test",
        default=False,
        action="store_true",
        help="Perform a dry-run (don't send any emails or sync to remote server)",
    )

    parser.add_argument(
        "-d",
        "--debug",
        default=False,
        action="store_true",
        help="Print debugging messages",
    )

    args = vars(parser.parse_args())

    run_experiment(**args)
