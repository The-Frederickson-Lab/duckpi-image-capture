from email.message import EmailMessage
import logging
from os import path
import smtplib
from typing import Optional, List, Union

from schema import Schema, And, Optional, SchemaError
from yaml import safe_load

from duckpi_ic.settings import settings


def set_logger_debug(logger: logging.Logger):
    logger.handlers.clear()
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(name)s %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


def read_and_validate_config(config_path: str):
    with open(config_path) as f:
        config = safe_load(f)

    validate_config(config)

    return config


def validate_config(config: dict):

    max_dist = settings.MAX_DISTANCE
    if max_dist:
        max_dist = int(max_dist)
    else:
        max_dist = None

    prev_stage_length = 0
    for i, stage in enumerate(config["stages"]):
        stage_distance = stage["stage_distance"]["length"]
        if stage_distance < prev_stage_length:
            raise SchemaError(
                autos=None,
                errors=[
                    f"Size of stage {i-1} {prev_stage_length} is longer than `distance_from_home` of next stage ({stage_distance})!"
                ],
            )
        row_distance = stage["row_distance"]["length"] * stage["rows"]
        stage_span = row_distance + stage_distance
        if max_dist is not None and stage_span > max_dist:
            raise SchemaError(
                autos=None, errors=[f"Stages exceed max length of {max_dist}!"]
            )
        prev_stage_length = stage_span

    def make_length_schema(field_name: str):
        return Schema(
            {
                "length": And(
                    int, lambda n: n > 0, error=f"{field_name} must be greater than 0."
                ),
                Optional("units"): str,
            }
        )

    schema = Schema(
        {
            "name": And(str, len, error="`name` is required and must be a string."),
            "output_dir": And(
                str,
                lambda n: len(n) >= 1,
                path.exists,
                error="`output_dir` is required and must exist.",
            ),
            "number_of_images": And(
                int,
                lambda n: n > 0,
                error="`number_of_images` is required and must be greater than 0.",
            ),
            "emails": [
                And(
                    str,
                    lambda x: len(x) > 5,
                    error="At least one email is required!",
                )
            ],
            "stages": [
                Schema(
                    {
                        "row_distance": make_length_schema("`row_distance`"),
                        "rows": And(
                            int,
                            lambda n: n > 0,
                            error="`rows` is required and must be greater than 0",
                        ),
                        # this could be zero, but will fail above validation
                        "stage_distance": Schema(
                            {
                                "length": int,
                                Optional("units"): str,
                            }
                        ),
                    }
                )
            ],
        },
        ignore_extra_keys=True,
    )

    return schema.validate(config)


def _send_gmail(
    recipients: List[str],
    subject: str,
    content: str,
    attachment_paths: Union[List[str], None] = None,
):

    SMTP_SERVER = settings.SMTP_SERVER
    SMTP_PORT = settings.SMTP_PORT
    GMAIL_USERNAME = settings.GMAIL_USERNAME
    GMAIL_PASSWORD = settings.GMAIL_PASSWORD
    ADMIN_EMAIL = settings.ADMIN_EMAIL

    msg = EmailMessage()
    msg["Subject"] = subject

    msg["From"] = ADMIN_EMAIL
    msg["To"] = ", ".join(recipients)
    msg.set_content(content)

    if attachment_paths:
        for file in attachment_paths:
            with open(file, "rb") as fp:
                img_data = fp.read()
            msg.add_attachment(
                img_data, maintype="image", subtype="jpeg", filename=path.basename(file)
            )

    with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as session:
        session.ehlo()
        session.starttls()
        session.ehlo()

        session.login(GMAIL_USERNAME, GMAIL_PASSWORD)

        session.send_message(msg)


def send_success_email(
    recipients: List[str],
    experiment_name: str,
    message: str,
    image_paths: List[str],
):
    subject = f"{experiment_name.title()} Success"
    return _send_gmail(recipients, subject, message, image_paths)


def send_error_email(
    recipients: List[str],
    experiment_name: str,
    error_message: str,
    image_paths: List[str],
):
    message = (
        f"{experiment_name} name encountered an error."
        + f"\n\nError message: {error_message}"
    )
    subject = f"{experiment_name.title()} Error"
    return _send_gmail(recipients, subject, message, image_paths)
