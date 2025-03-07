from dataclasses import dataclass
from os import path, getenv

from dotenv import load_dotenv

load_dotenv(path.join(path.dirname(path.dirname(__file__)), ".env"))

ADMIN_EMAIL = getenv("ADMIN_EMAIL")
assert ADMIN_EMAIL
DEVICE_PORT = getenv("DEVICE_PORT")
assert DEVICE_PORT
GMAIL_USERNAME = getenv("GMAIL_USERNAME")
assert GMAIL_USERNAME
GMAIL_PASSWORD = getenv("GMAIL_PASSWORD")
assert GMAIL_PASSWORD
PYTHON_BINARY_PATH = getenv("PYTHON_BINARY_PATH")
assert PYTHON_BINARY_PATH
REMOTE_SAVE_DIR = getenv("REMOTE_SAVE_DIR")
assert REMOTE_SAVE_DIR
REMOTE_HOST_NAME = getenv("REMOTE_HOST_NAME")
assert REMOTE_HOST_NAME
SMTP_SERVER = getenv("SMTP_SERVER")
assert SMTP_SERVER
SMTP_PORT = getenv("SMTP_PORT")
assert SMTP_PORT


@dataclass
class _Settings:
    ADMIN_EMAIL = ADMIN_EMAIL
    DEVICE_PORT = DEVICE_PORT
    GMAIL_PASSWORD = GMAIL_PASSWORD
    GMAIL_USERNAME = GMAIL_USERNAME
    PYTHON_BINARY_PATH = PYTHON_BINARY_PATH
    REMOTE_HOST_NAME = REMOTE_HOST_NAME
    REMOTE_SAVE_DIR = REMOTE_SAVE_DIR
    SMTP_PORT = SMTP_PORT
    SMTP_SERVER = SMTP_SERVER


settings = _Settings()
