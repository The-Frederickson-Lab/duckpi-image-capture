# Duckpi Image Capture

## Overview

This is a work-in-progress python package for running experiments in the Frederickson Lab.

## Installation

The package is meant to be run on a RaspberryPI 4 with (currently) `python3.9` installed. The recommended installation method is to use `poetry` and a virtual environment. Under the current configularion, the virtual environment will be placed in the project root directory.

Note that the python `fabric` package requires `libffi-dev` and `libssl-dev`, which can be installed with `sudo apt-get install libffi-dev libssl-dev` as well as rust, which can be installed with `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`. To verify that rust is installed run `rustc --version`. If not found, try opening a new terminal.

Note also that `fabric` will use the `config` file in `~/.ssh` to configure connections to the remote host, so make sure that the remote host has an entry in `~/.ssh/config` before running an experiment that saves results to remote.

## Notes

[ImagingSystemCode_22-8-24_aquascape_full.py](ImagingSystemCode_22-8-24_aquascape_full.py) is an archive of the image capture script currently on pi 44.
