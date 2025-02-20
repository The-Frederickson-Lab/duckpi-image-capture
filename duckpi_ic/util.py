from email.message import EmailMessage
import logging
from os import path, getenv
import smtplib
from typing import Optional, List, Union


from schema import Schema, And, Optional
from yaml import safe_load


def set_logger_debug(logger: logging.Logger):
    if len(logger.handlers) == 0:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


def read_and_validate_config(config_path: str):
    with open(config_path) as f:
        config = safe_load(f)

    validate_config(config)

    return config


def validate_config(config: dict):
    length_schema = Schema({"length": int, Optional("units"): str})

    schema = Schema(
        {
            "name": And(str, len),
            "output_dir": And(str, len, path.exists),
            "number_of_images": (int),
            "emails": [And(str, len)],
            "stages": [
                Schema(
                    {
                        "row_distance": length_schema,
                        "rows": int,
                        "stage_distance": length_schema,
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
    import dotenv

    dotenv.load_dotenv(path.join(path.dirname(path.dirname(__file__)), ".env"))

    SMTP_SERVER = getenv("SMTP_SERVER")
    SMTP_PORT = getenv("SMTP_PORT")
    GMAIL_USERNAME = getenv("GMAIL_USERNAME")
    GMAIL_PASSWORD = getenv("GMAIL_PASSWORD")
    ADMIN_EMAIL = getenv("ADMIN_EMAIL")

    assert SMTP_SERVER
    assert SMTP_PORT
    assert GMAIL_USERNAME
    assert GMAIL_PASSWORD
    assert ADMIN_EMAIL

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
    image_paths: List[str],
):
    message = f"{experiment_name} ran successfully."
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
