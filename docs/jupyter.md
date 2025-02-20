# Using duckpi-ic in a jupyter notebook

It can be useful to take photos and debug settings in a jupyter notebook interface.

Currently notebooks are stored in the `~/notebooks` directory on the Frederickson Lab pi's.

The easiest way to access and use them is with the VS Code jupyter extension, which allows you to run jupyter notebooks inside vscode over ssh.

There are a few step to setting this up:

1. Set up SSH on your VS Code instance. First, install the (Remote SSH Extension)[https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-ssh]. Then open the command pallate (`ctl + smift + p`) and search `ssh`. You should see `Remote-SSH Add New SSH Host` on the menu. Select this. It will prompt you to enter the username and IP of the host (i.e., the pi) and give a name to the connection (e.g. `pi-44`). Make sure that you are connected to the VPN if necessary before attempting to SSH in.

2. SSH into the pi using VS Code. Once the host has been set up, open up the command pallate again and search for `Remote-SSH Connect to Host`. Select the host you just configured. A new VS Code window will open. If your SSH is password protected, you will see a (small) prompt to enter it at the top of the VS Code window.

3. Open the home folder on the pi. If this is your first time connecting with VS Code or you haven't set up a default workspace, you will need to open a directory in order to browse files. Open the file explorer with `ctl+shift+e`. You should see a button that says "Open Folder". Click it. You should be prompted to open the home directory for the user. Click OK.

4. If you would like to use an existing notebook, navigate to the `notebooks` directory and select one. If you don't have the VS Code Jupyter extension installed, you will be prompted to install it, otherwise you'll need to install it manually.

5. Select the python kernel. In the upper right of the window, you should see some text that says "Select Kernel." This is basically telling the notebook which python environment to use. In order to use the `duckpi-ic` package, you'll need to select the virtual environment into which it has been installed. When you click "Select Kernel," you might see an option that starts with `.venv`. If you do, select it, and you should be good to go. If not, you may need to activate the environment.

6. Make sure the virtual environment is active. Open a terminal, navigate to the directory where the `duckpi-image-capture` library is installed, and run `poetry env activate` from a terminal. This should activate the environment, and you should now see it on the 'Select Kernel' menu in VS Code.

