# Duckpi Image Capture

## Overview

This is a work-in-progress python package for running experiments in the Frederickson Lab.

## Installation

The package is meant to be run on a RaspberryPI 4 with (currently) `python3.9` installed. The recommended installation method is to use `poetry` and a virtual environment. Under the current configularion, the virtual environment will be placed in the project root directory.

To install `poetry` on the Pi, first install `pipx` with the following commands:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

This will install pipx for the current user. You can then run `pipx install poetry` to install `poetry` itself.

Note that the python `fabric` package requires `libffi-dev` and `libssl-dev`, which can be installed with `sudo apt-get install libffi-dev libssl-dev` as well as rust, which can be installed with `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`. To verify that rust is installed run `rustc --version`. If not found, try opening a new terminal.

Note also that `fabric` will use the `config` file in `~/.ssh` to configure connections to the remote host, so make sure that the remote host has an entry in `~/.ssh/config` before running an experiment that saves results to remote.

The `picamera2` package should also be installed. It is best to do so with `apt` rather than `poetry` in order to avoid system dependency issues. You can do this with `sudo apt install python3-picamera2`.

Note that `Pillow` will need the `libjpeg-dev` dependency installed.


## Using the GUI

The GUI can be accessed via SSH. In order to use the GUI remotely on your home machine, you must include `X11` forwarding in your SSH command. Typically this is done by adding the `-X` switch, so that your command might look something like `ssh -X user@host /path/to/venv/python /path/to/gui.py`. There are a number of things you can do to make this process a bit more convenient:

1. Set up passwordless SSH. If you haven't already done so, you can SSH in using your local key pair instead of a password. There is a walkthrough [here](https://www.ssh.com/academy/ssh/copy-id).
2. Use an SSH config file. If you have to do a lot of SSHing, it can be convenient to set up aliases rather than writing the full command every time. An entry for a Pi might look like this:

    ```
    Host pi-18
      HostName <ip-address>
      User my-username
      ForwardX11 yes
    ```

    Then you can SSH in by just typing `ssh pi-18`. You can find more information [here](https://docs.alliancecan.ca/wiki/SSH_configuration_file).
3. Use a script to launch the GUI. Currently there are scripts in the Pi home directories called `start-gui`. Once you have your key-based SSH login and config set up (with, say, `pi-18` as an alias), you can launch the GUI by entering `ssh pi-18 ./start-gui`.

## Notes

[ImagingSystemCode_22-8-24_aquascape_full.py](ImagingSystemCode_22-8-24_aquascape_full.py) is an archive of the image capture script currently on pi 44.
