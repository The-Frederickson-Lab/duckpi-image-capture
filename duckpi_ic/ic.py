"""Contains code for moving actuator, camera selection, and image capture"""

from enum import Enum
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import mkstemp
import time
import traceback
from typing import List

from fabric import Connection as FabricConnection
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


DEVICE_PORT = "/dev/ttyUSB0"


# camera order from door: C (2), A (0), B (1), D (3)
class Cameras(Enum):
    A = 0
    B = 1
    C = 2
    D = 3


def set_axis_defaults(
    axis: Axis,
    acceleration: int = 2,
    deceleration: int = 2,
    max_speed: int = 20,
):
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


def home_actuator(device_port: str = DEVICE_PORT):
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


def move_actuator(
    distance: int,
    unit: LengthUnits = Units.LENGTH_MILLIMETRES,
    device_port: str = DEVICE_PORT,
):
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
        logger.debug(f"Moving actuator {distance} {unit}")
        axis.move_relative(distance, unit)


def setup_gpio_pins():
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


def start_camera(camera_id: str):
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


def _take_still(camera_id: str, output_directory: str, filename: str) -> str:
    """Take a still photo, camera is expected to have been started already

    :param camera_id: The camera id
    :type camera_id: Literal[&quot;A&quot;, &quot;B&quot;, &quot;C&quot;, &quot;D&quot;]
    :param output_directory: Where to save the output
    :type output_directory: str

    :return: The path of the image
    :rtype: str
    """

    Path(os.path.join(output_directory, f"camera{camera_id}")).mkdir(
        parents=True, exist_ok=True
    )

    output_file_path = f"{output_directory}/camera{camera_id}/{filename}"
    capture_image_command = f"sudo libcamera-still -n -t 10000 --camera {Cameras[camera_id].value} -o {output_file_path}"
    subprocess.run(
        capture_image_command.split(), capture_output=True, check=True, timeout=25
    )

    return output_file_path


def take_stills(
    camera_id: str, output_directory: str, filename: str, img_count: int
) -> List[str]:
    """Rest pins, start camera, take, and save photo

    :param camera_id: The camera to use
    :type camera_id: Literal[&quot;A&quot;, &quot;B&quot;, &quot;C&quot;, &quot;D&quot;]
    :param output_directory: Where to save the image
    :type output_directory: str

    :return: The path of the image
    :rtype: str
    """
    image_paths = []
    try:
        setup_gpio_pins()
        start_camera(camera_id)
        for img_num in range(0, img_count):
            logger.debug(f"Taking image number {img_num + 1}")
            img_path = _take_still(camera_id, output_directory, filename)
            image_paths.append(img_path)
    except Exception as e:
        logger.exception(e)
        raise
    finally:
        logger.debug("cleaning up pins")
        gp.cleanup()

    return image_paths


def make_filename(camera: str, stage: int, row: int):
    ts = time.strftime("%Y%m%d-%H%M%S")
    return f"cam_{camera}_{stage}_{row}_{ts}.jpg"


def move_files_to_remote(c: FabricConnection, local_paths: List[str], name: str):
    remote_save_dir = settings.REMOTE_SAVE_DIR
    assert remote_save_dir
    relpaths = [os.path.sep.join(p.split(os.path.sep)[-2:]) for p in local_paths]
    remote_root = os.path.join(remote_save_dir, name)
    failures = []
    for relpath, local_path in zip(relpaths, local_paths):
        try:
            logger.debug(f"Moving {local_path} to {os.path.join(remote_root, relpath)}")
            c.put(local_path, os.path.join(remote_root, relpath))
            SUCCESS = True
        except Exception as e:
            logger.exception(e)
            failures.append(local_path)
            SUCCESS = False
        if SUCCESS:
            logger.debug(f"deleting {local_path}")
            os.remove(local_path)
    return failures


def update_first_last(first_last: List[str], local_paths: List[str]):
    first, last = first_last
    if os.stat(first).st_size == 0:
        shutil.copy2(local_paths[0], first)
    else:
        shutil.copy2(local_paths[-1], last)


def get_first_last_tmp_paths() -> List[str]:
    _, tmp1 = mkstemp(suffix=".jpg")
    _, tmp2 = mkstemp(suffix=".jpg")
    return [tmp1, tmp2]


def ensure_remote_dirs_exist(remote_host_name, experiment_name):
    remote_save_dir = settings.REMOTE_SAVE_DIR
    assert remote_save_dir
    with FabricConnection(remote_host_name) as c:
        with c.cd(remote_save_dir):
            c.run(f"mkdir -p {experiment_name}")
            for cam in Cameras:
                c.run(f"mkdir -p camera{cam}")


def run_experiment(
    config_path: str, test: bool = False, debug: bool = False
) -> List[str]:
    """Perform a run of the experiment

    :param config_path: The path to the experiment configuration
    :type config_path: str
    :param test: Whether or not this is a dry run (in which case no emails will be sent), defaults to False
    :type test: bool, optional
    :param debug: Whether to print debugging messages, defaults to False
    :type debug: bool, optional
    """

    if debug:
        set_logger_debug(logger)

    experiment_config = read_and_validate_config(config_path)
    remote_host_name = settings.REMOTE_HOST_NAME
    assert remote_host_name

    experiment_name = experiment_config["name"]

    first_last = get_first_last_tmp_paths()

    local_save_dir = os.path.join(experiment_config["output_dir"], experiment_name)

    if not test:
        ensure_remote_dirs_exist(remote_host_name, experiment_name)

    try:
        home_actuator()

        for i, stage in enumerate(experiment_config["stages"]):
            # stage_distance is relative to previous row
            move_actuator(
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

                    filename = make_filename(camera.name, i + 1, row + 1)
                    local_paths = take_stills(
                        camera.name,
                        local_save_dir,
                        filename,
                        experiment_config["number_of_images"],
                    )

                    update_first_last(first_last, local_paths)

                    if not test:
                        with FabricConnection(remote_host_name) as c:
                            unmoved = move_files_to_remote(
                                c, local_paths, experiment_name
                            )

    except Exception as e:
        # TODO: move into function
        logger.exception(e)
        exc_type, exc_value, exc_traceback = sys.exc_info()
        trace = "\n".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        )
        msg = "Error Message: " + "\n\n" + str(e) + "\n\n" + trace
        if not test:
            send_error_email(
                experiment_config["emails"],
                experiment_name,
                msg,
                [p for p in first_last if p is not None],
            )
        raise

    finally:
        home_actuator()

    if not test:
        logger.debug("Sending success email")
        send_success_email(
            experiment_config["emails"],
            experiment_config["name"],
            first_last,
        )

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
        required=True,
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
