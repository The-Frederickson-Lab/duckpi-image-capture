from dataclasses import dataclass
from os import path, getenv

from dotenv import load_dotenv

load_dotenv(path.join(path.dirname(path.dirname(__file__)), ".env"))

REMOTE_SAVE_DIR = getenv("REMOTE_SAVE_DIR")
assert REMOTE_SAVE_DIR
REMOTE_HOST_NAME = getenv("REMOTE_HOST_NAME")
assert REMOTE_HOST_NAME
SMTP_SERVER = getenv("SMTP_SERVER")
assert SMTP_SERVER
SMTP_PORT = getenv("SMTP_PORT")
assert SMTP_PORT
GMAIL_USERNAME = getenv("GMAIL_USERNAME")
assert GMAIL_USERNAME
GMAIL_PASSWORD = getenv("GMAIL_PASSWORD")
assert GMAIL_PASSWORD
ADMIN_EMAIL = getenv("ADMIN_EMAIL")
assert ADMIN_EMAIL


@dataclass
class _Settings:
    REMOTE_SAVE_DIR = REMOTE_SAVE_DIR
    REMOTE_HOST_NAME = REMOTE_HOST_NAME
    SMTP_SERVER = SMTP_SERVER
    SMTP_PORT = SMTP_PORT
    GMAIL_USERNAME = GMAIL_USERNAME
    GMAIL_PASSWORD = GMAIL_PASSWORD
    ADMIN_EMAIL = ADMIN_EMAIL


settings = _Settings()
