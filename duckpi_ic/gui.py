from datetime import datetime
from logging import getLogger
import os
from pathlib import Path
import re
from tempfile import gettempdir, TemporaryDirectory
from tkinter import (
    filedialog,
    N,
    W,
    E,
    S,
    BooleanVar,
    DoubleVar,
    StringVar,
)
from tkinter.messagebox import showinfo
from tkinter.simpledialog import Dialog
from typing import Any, Dict, List, Optional

import customtkinter
from picamera2 import Preview as PreviewType
from PIL import Image
from schema import SchemaError
import yaml

from duckpi_ic.ic import (
    Cameras,
    DuckCam,
    move_actuator,
    home_actuator,
    run_experiment,
    get_actuator_position,
)
from duckpi_ic.settings import settings
from duckpi_ic.util import validate_config

logger = getLogger(__name__)

PYTHON_BINARY_PATH = settings.PYTHON_BINARY_PATH

SESSION_FILENAME = datetime.now().strftime("%m-%d-%Y-%H-%M-%S")
SESSION_DIR = Path(gettempdir()) / "duckpi_gui_session"
SESSION_DIR.mkdir(exist_ok=True)
NEW_SESSION_PATH = SESSION_DIR / SESSION_FILENAME
existing_session = list(str(f) for f in SESSION_DIR.glob("*"))


def to_int(text: str):
    intval_ = 0
    try:
        intval_ = int(text)
    except ValueError:
        pass
    return intval_


root = customtkinter.CTk()

customtkinter.set_appearance_mode("dark")  # Modes: system (default), light, dark
customtkinter.set_default_color_theme("blue")
root.grid_rowconfigure(0, weight=1)  # configure grid system
root.grid_columnconfigure(0, weight=1)
root.title("Set Up An Experiment")
root.geometry("800x950")


class SessionDialog(Dialog):
    def __init__(self, parent, title: str, sessions: List[str], new_session_path: Path):
        self.sessions = sessions
        self.new_session_path = new_session_path
        self.parent = parent
        self.parent.lift()
        super().__init__(parent, title)

    def body(self, frame):
        session_names = ", ".join(self.sessions)
        customtkinter.CTkLabel(
            frame,
            text=f"Active session(s) found: {session_names}. \n Please delete them or exit.",
            text_color="black",
        ).grid(column=0, row=0)

    def cancel(self):
        root.destroy()

    def delete(self):
        for session in self.sessions:
            os.remove(session)
        self.new_session_path.touch()
        self.parent.focus_set()
        self.destroy()

    def buttonbox(self):
        cancel_button = customtkinter.CTkButton(
            self, text="Exit", width=8, command=self.cancel
        )
        cancel_button.pack(side="left")
        delete_button = customtkinter.CTkButton(
            self, text="Delete", width=8, command=self.delete
        )
        delete_button.pack(side="right")


if len(existing_session):
    dialogue = SessionDialog(
        root, "Active session found!", existing_session, NEW_SESSION_PATH
    )
else:
    NEW_SESSION_PATH.touch()


tab_control = customtkinter.CTkTabview(master=root)
tab1 = tab_control.add("Config")
tab2 = tab_control.add("Preview")
tab_control.set("Config")
# ensure tab/content fills the window
tab_control.grid(row=0, column=0, padx=20, pady=20, sticky=(N, S, E, W))


def check_num(newval):
    return re.match(r"^[0-9]*$", newval) is not None and len(newval) <= 5


# Validation
check_num_wrapper = (root.register(check_num), "%P")


def delete_current_session(pth: Path):
    try:
        _pth = str(pth)
        os.remove(_pth)
    # not sure why this might happen but we want to exit in any case
    except FileNotFoundError as e:
        logger.exception(e)

    root.destroy()


def get_image_pos(image_name: Path):
    _, cam, stage, row, _, _ = os.path.basename(str(image_name)).split("_")

    return f"{stage}_{row}_{cam}"


class SaveSuccessDialog(Dialog):
    def __init__(self, parent, title, executable_path: str, yaml_path: str):
        self.command = f"{executable_path} {yaml_path}"
        self.parent = parent
        super().__init__(parent, title)

    def body(self, frame):

        t = customtkinter.CTkTextbox(frame, height=200)
        t.insert(
            1.0,
            f"The job can be configured with the following command:\n{self.command}",
        )
        t.pack()

        # t.configure(bg=self.parent.cget("bg"), relief="flat")
        t.configure(state="disabled")


class StageEntry:
    def __init__(self, frame: customtkinter.CTkFrame, base_row: int, base_col: int):
        self.distance_from_home = StringVar()

        self.distance_from_home_entry = customtkinter.CTkEntry(
            frame,
            width=50,
            textvariable=self.distance_from_home,
            validate="key",
            validatecommand=check_num_wrapper,
        )
        self.distance_from_home_entry.grid(
            column=base_col + 1, row=base_row, sticky=(W), padx=5
        )

        customtkinter.CTkLabel(frame, text="Distance from home").grid(
            column=base_col, row=base_row, sticky=W
        )

        self.row_count = StringVar()
        self.row_count_entry = customtkinter.CTkEntry(
            frame,
            width=50,
            textvariable=self.row_count,
            validate="key",
            validatecommand=check_num_wrapper,
        )
        self.row_count_entry.grid(
            column=base_col + 1, row=base_row + 1, sticky=(W), padx=5
        )
        customtkinter.CTkLabel(frame, text="Row count").grid(
            column=base_col, row=base_row + 1, sticky=W
        )

        self.distance_between_rows = StringVar()
        self.distance_between_rows_entry = customtkinter.CTkEntry(
            frame,
            width=50,
            textvariable=self.distance_between_rows,
            validate="key",
            validatecommand=check_num_wrapper,
        )
        self.distance_between_rows_entry.grid(
            column=base_col + 1, row=base_row + 2, sticky=(W), padx=5
        )
        customtkinter.CTkLabel(frame, text="Distance between rows").grid(
            column=base_col, row=base_row + 2, sticky=W
        )


class YAMLSpec:
    def __init__(self, frame: customtkinter.CTkFrame):
        self.parent = frame.winfo_toplevel()
        self.frame = frame
        self.name = StringVar()
        name_entry = customtkinter.CTkEntry(frame, width=250, textvariable=self.name)
        customtkinter.CTkLabel(frame, text="Name").grid(column=0, row=1, sticky=W)
        name_entry.grid(column=1, row=1, sticky=(W), columnspan=4)

        self.output_dir = StringVar()
        output_dir_entry = customtkinter.CTkEntry(
            frame,
            width=250,
            textvariable=self.output_dir,
        )
        customtkinter.CTkLabel(frame, text="Output directory").grid(
            column=0, row=2, sticky=W, columnspan=4
        )
        output_dir_entry.grid(column=1, row=2, sticky=(W), columnspan=4)

        self.emails = StringVar()
        emails_entry = customtkinter.CTkEntry(
            frame, width=250, textvariable=self.emails
        )
        customtkinter.CTkLabel(frame, text="Emails").grid(column=0, row=3, sticky=(W))
        emails_entry.grid(column=1, row=3, sticky=(W), columnspan=4)

        self.number_of_images = StringVar()
        # key means validate on keypress
        number_of_images_entry = customtkinter.CTkEntry(
            frame,
            width=50,
            textvariable=self.number_of_images,
            validate="key",
            validatecommand=check_num_wrapper,
        )

        customtkinter.CTkLabel(frame, text="Number of Images").grid(
            column=0, row=4, sticky=W
        )
        number_of_images_entry.grid(column=1, row=4, sticky=(W))

        customtkinter.CTkLabel(frame, text="Stage 1").grid(column=0, row=5, sticky=W)

        self.stage_1_entries = StageEntry(frame, base_row=6, base_col=0)

        customtkinter.CTkLabel(frame, text="Stage 2").grid(column=2, row=5, sticky=W)

        self.stage_2_entries = StageEntry(frame, base_row=6, base_col=2)

        customtkinter.CTkLabel(frame, text="Stage 3").grid(column=4, row=5, sticky=W)

        self.stage_3_entries = StageEntry(frame, base_row=6, base_col=4)

        self.yaml_result = customtkinter.CTkTextbox(frame, width=550, height=250)

        self.yaml_result.grid(column=0, row=17, pady=10, columnspan=5)

        customtkinter.CTkButton(frame, text="Test", command=self.run_job).grid(
            column=0, row=18
        )
        customtkinter.CTkButton(frame, text="View", command=self.view_yaml).grid(
            column=2, row=18
        )
        customtkinter.CTkButton(frame, text="Save", command=self.save_yaml).grid(
            column=4, row=18
        )

        name_entry.focus()
        root.bind("<Return>", lambda x: self.view_yaml())

    def _build_yaml(self, config_dict: Optional[Dict[str, Any]] = None):
        if config_dict is None:
            config_dict = self._build_config_dict()
        return yaml.dump(
            dict(config_dict), sort_keys=False, default_flow_style=False, indent=1
        )

    def _build_config_dict(self):
        config_dict = {
            "name": self.name.get().strip(),
            "output_dir": self.output_dir.get().strip(),
            "emails": self.emails.get().split(","),
            "number_of_images": to_int(self.number_of_images.get()),
            "stages": [],
        }

        config_dict["stages"].append(
            {
                "stage_distance": {
                    "length": to_int(self.stage_1_entries.distance_from_home.get())
                },
                "rows": to_int(self.stage_1_entries.row_count.get()),
                "row_distance": {
                    "length": to_int(self.stage_1_entries.distance_between_rows.get())
                },
            }
        )

        stage_2_count = to_int(self.stage_2_entries.row_count.get())

        if stage_2_count > 0:
            config_dict["stages"].append(
                {
                    "stage_distance": {
                        "length": to_int(self.stage_2_entries.distance_from_home.get())
                    },
                    "rows": stage_2_count,
                    "row_distance": {
                        "length": to_int(
                            self.stage_2_entries.distance_between_rows.get()
                        )
                    },
                }
            )

        stage_3_count = to_int(self.stage_3_entries.row_count.get())

        if stage_3_count > 0:
            config_dict["stages"].append(
                {
                    "stage_distance": {
                        "length": to_int(self.stage_3_entries.distance_from_home.get())
                    },
                    "rows": stage_3_count,
                    "row_distance": {
                        "length": to_int(
                            self.stage_3_entries.distance_between_rows.get()
                        )
                    },
                }
            )
        return config_dict

    def _validate_yml(self):
        config_dict = self._build_config_dict()
        try:
            validate_config(config_dict)
        except SchemaError as e:
            showinfo(
                title="Invalid Config!",
                message="\n".join([e for e in e.errors if e]),
            )

            return False

        return True

    def save_yaml(self):

        if not self._validate_yml():
            return

        yml_str = self._build_yaml()

        filepath = filedialog.asksaveasfilename(
            title="Select where to save the configuration",
            defaultextension=".yml",
            parent=self.parent,
        )

        Path(filepath).parent.mkdir(exist_ok=True, parents=True)

        if filepath:
            with open(filepath, "w") as f:
                f.write(yml_str)
            SaveSuccessDialog(self.parent, "Success!", PYTHON_BINARY_PATH, filepath)

    def view_yaml(self):

        config_yaml = self._build_yaml()

        self.yaml_result.delete("1.0", "end")
        self.yaml_result.insert("1.0", config_yaml)

    def run_job(self):
        if not self._validate_yml():
            return

        with TemporaryDirectory() as t:
            config_dict = self._build_config_dict()
            config_dict["output_dir"] = t
            config_dict["number_of_images"] = 1
            yml_str = self._build_yaml(config_dict)
            yml_path = Path(t) / "config.yml"
            with open(yml_path, "w") as f:
                f.write(yml_str)
            exp_name = config_dict["name"].strip()
            save_dir = Path(t) / exp_name
            logger.info("Running experiment...")
            run_experiment(str(yml_path), test=True, debug=True)
            frm = customtkinter.CTkScrollableFrame(self.frame, height=300)
            frm.grid(row=19, column=0, columnspan=6, sticky=(N, S, E, W))
            imgs = sorted(list(save_dir.rglob("*.jpg")), key=get_image_pos)
            for i, pth in enumerate(imgs):
                img = Image.open(pth)
                img.resize((140, 140))
                tk_img = customtkinter.CTkImage(dark_image=img, size=(140, 140))
                lbl = customtkinter.CTkLabel(
                    frm, image=tk_img, text=get_image_pos(pth), compound="top"
                )
                row, col = i // 4, i % 4
                lbl.grid(row=row, column=col, padx=5, pady=5)


class Preview:
    def __init__(self, frame: customtkinter.CTkFrame):
        self.frame = frame
        self.distance_to_move_actuator = StringVar()
        self.actuator_position = DoubleVar()
        self.actuator_position.set(get_actuator_position())
        self.actuator_moving = BooleanVar()
        self.selected_camera = StringVar()

        self.selected_camera_instance = None

        camera_label = customtkinter.CTkLabel(
            self.frame,
            text="Select a Camera",
        )
        camera_label.grid(
            column=0,
            row=0,
            padx=5,
            pady=15,
        )

        self.move_actuator_button = customtkinter.CTkButton(
            self.frame,
            text="Move Actuator",
            command=lambda: self.move_actuator(
                to_int(self.distance_to_move_actuator.get())
            ),
            state="disabled",
        )

        self.move_actuator_button.grid(column=0, row=1, sticky=E, padx=5, pady=15)

        self.home_actuator_button = customtkinter.CTkButton(
            self.frame,
            text="Home Actuator",
            command=self.home_actuator,
            state="disabled",
        )

        self.home_actuator_button.grid(
            column=0,
            row=2,
            sticky=E,
            padx=5,
            pady=15,
        )

        self.camera_list = [cam.name for cam in Cameras]

        self.camera_menu = customtkinter.CTkOptionMenu(
            self.frame,
            values=self.camera_list,
            variable=self.selected_camera,
            command=self.set_selected_camera,
        )

        self.camera_menu.grid(column=1, row=0, padx=5, pady=15, columnspan=2)

        customtkinter.CTkEntry(
            self.frame,
            width=50,
            textvariable=self.distance_to_move_actuator,
            validate="key",
            validatecommand=check_num_wrapper,
        ).grid(column=1, row=1, pady=15, sticky=E)

        customtkinter.CTkLabel(
            self.frame,
            width=50,
            text="mm",
        ).grid(column=2, row=1, pady=15, sticky=W)

        customtkinter.CTkLabel(self.frame, width=50, text="Distance from home:").grid(
            column=3, row=1, padx=5, pady=15, sticky=W
        )

        customtkinter.CTkLabel(
            self.frame, width=50, textvariable=self.actuator_position
        ).grid(column=4, row=1, pady=15, sticky=W)

        self.preview_button = customtkinter.CTkButton(
            self.frame,
            text="Start Preview",
            command=self.start_preview,
            state="disabled",
        )

        self.preview_button.grid(column=4, row=0, padx=5, pady=5, sticky=W)

        self.reset_button = customtkinter.CTkButton(
            self.frame, text="Stop Preview", command=self.reset, state="disabled"
        )

        self.reset_button.grid(column=4, row=4, sticky=E, padx=5, pady=15)

    def set_selected_camera(self, camera):
        if camera in self.camera_list:
            self.preview_button.configure(state="normal")
            self.selected_camera.set(camera)

    def home_actuator(self):
        home_actuator()
        self.distance_to_move_actuator.set("")

    def move_actuator(self, distance: int = 0):
        if distance > 0:
            position = move_actuator(distance)
            self.actuator_position.set(round(position))
            self.distance_to_move_actuator.set("")

    def start_preview(self):
        logger.info("starting preview....")
        if (
            self.selected_camera.get() in self.camera_list
            and self.selected_camera_instance is None
        ):
            self.preview_button.configure(state="disabled")
            self.camera_menu.configure(state="disabled")
            self.reset_button.configure(state="normal")
            self.move_actuator_button.configure(state="normal")
            self.home_actuator_button.configure(state="normal")
            self.selected_camera_instance = DuckCam(Cameras[self.selected_camera.get()])
            self.selected_camera_instance.start_preview(PreviewType.QT)
            self.selected_camera_instance.start()
            logger.info("preview started....")

    def reset(self):
        self.distance_to_move_actuator.set("")
        self.home_actuator()
        self.selected_camera.set("")
        if self.selected_camera_instance:
            logger.info("closing camera instance")
            self.selected_camera_instance.close()
            self.selected_camera_instance = None
        self.actuator_position.set(get_actuator_position())
        self.camera_menu.configure(state="normal")
        self.reset_button.configure(state="disabled")
        self.move_actuator_button.configure(state="disabled")
        self.home_actuator_button.configure(state="disabled")


YAMLSpec(tab1)
Preview(tab2)

root.protocol("WM_DELETE_WINDOW", lambda: delete_current_session(NEW_SESSION_PATH))

root.mainloop()
