#! /usr/bin/env python3

"""
Sometimes there are problems turning on a camera immediately after it has been turned
off. This typically doesn't happen because the cameras are turned off and on in sequence
(i.e., the same camera isn't usually switched on twice in a row). But if this does happen,
the camera will timeout. This script will take a test photo with cameras A-D,
so that taking a sequence of photos starting with camera A should work again.

Make sure that the virtual environment is activated before running:
`source /home/minor/duckpi-image-capture/.venv/activate`

Note that the files are deleted as soon as the program exits.
"""
import logging
from os import listdir
from tempfile import TemporaryDirectory

from duckpi_ic.ic import take_stills, Cameras
from duckpi_ic.util import set_logger_debug

dp_logger = logging.getLogger("duckpi_ic")

set_logger_debug(dp_logger)

error_count = 0
with TemporaryDirectory() as tmpdirname:
    for camera in Cameras._member_names_:
        try:
            take_stills(camera, tmpdirname, 1)
        except Exception as e:
            dp_logger.exception(e)
            error_count += 1

    print(f"Took {len(listdir(tmpdirname))} photos with {error_count} errors")
