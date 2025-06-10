from os import path

from yaml import safe_load
import pytest
from schema import SchemaError

from duckpi_ic.util import validate_config


# note that MAX_DIST is set in conftest.py
def test_can_validate():
    with open(
        path.join(path.dirname(__file__), "fixtures", "test_config_stage_2_short.yml")
    ) as f:
        short_config = safe_load(f)

    with open(
        path.join(path.dirname(__file__), "fixtures", "test_config_stage_2_long.yml")
    ) as f:
        long_config = safe_load(f)

    with open(
        path.join(path.dirname(__file__), "fixtures", "test_config_stage_2_normal.yml")
    ) as f:
        good_config = safe_load(f)

    assert validate_config(good_config)

    with pytest.raises(SchemaError):
        # stage 1 here would overlap into stage 2
        validate_config(long_config)
        # stage 2 here would exceded MAX_DISTANCE
        validate_config(short_config)
