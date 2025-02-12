from os import path

from yaml import safe_load

from duckpi_ic.util import validate_config


def test_can_validate():
    with open(path.join(path.dirname(__file__), "fixtures", "test_config.yml")) as f:
        config = safe_load(f)

    assert validate_config(config)
