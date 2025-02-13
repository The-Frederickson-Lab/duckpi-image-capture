from os import path
import logging

from schema import Schema, And, Optional
from yaml import safe_load


def set_logger_debug(logger: logging.Logger):
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
