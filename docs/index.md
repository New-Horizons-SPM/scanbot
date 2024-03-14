# Scanbot       [![DOI](https://zenodo.org/badge/487719232.svg)](https://zenodo.org/badge/latestdoi/487719232)

## Featured
* [React Implementation of Scanbot](./featured/#web-app)<br>
* [Scanbot meets ChatGPT](./featured/#scanbot-meets-chatgpt)

## Functional Overview
Scanbot is a collection of several automated STM and nc-AFM data acquisition commands compatible with Nanonis V5 SPM control software. It can help with:

* STM
    - Bias dependent imaging with drift correction
    - Automated sample surveying (NxN grid)
* nc-AFM
    - z-dependent nc-AFM
    - nc-AFM registration
* Automation
    - Tip shaping
    - Full control over the coarse motors
* Hooks
    - Scanbot has a number of built-in [hooks](./hooks) to let you customise key functionality.
    
## Installation

1. <details>
    <summary>Web App</summary>
    Scanbot has been implemented as a web application using [React](https://react.dev/).
    
    On Windows, the easiest way to use it is by [downloading and running the .exe](https://firebasestorage.googleapis.com/v0/b/scanbot-46390.appspot.com/o/scanbot-react%2FScanbot_V4.1.zip?alt=media&token=c0fca54e-619f-418c-9c06-f77d5ddc4ea6).
    
    Alternatively, you can install Scanbot from its source:

    1. Clone the [nanonisTCP interface](https://github.com/New-Horizons-SPM/nanonisTCP), navigate to the root directory and run ```pip install .```
    2. Clone the [Scanbot repository](https://github.com/New-Horizons-SPM/scanbot)
    3. Install node.js from [here](https://nodejs.org/en) or if you're using anaconda, run conda install conda-forge::nodejs
    4. Navigate to ```/scanbot/scanbot/App``` and run ```npm install```
    5. From the same directory, run ```npm run build```
    6. Navigate to the project root directory, and run ```pip install .```
    5. Start Scanbot by running the command ```scanbot```

    <br>
    
    <strong>Test Scanbot with the Nanonis V5 Simulator</strong> before integrating it with your STM by following [these instructions](./web-app-test).

    <strong>General user guide available [here](./web-app)</strong>.
  </details>

2. <details>
    <summary>Terminal</summary>
    Running Scanbot from a terminal:
    <br><br>
    1. Clone the [nanonisTCP interface](https://github.com/New-Horizons-SPM/nanonisTCP), navigate to the root directory and run ```pip install .```
    2. Clone the [Scanbot repository](https://github.com/New-Horizons-SPM/scanbot), navigate to the root directory, and run ```pip install .```
    3. Run ```python scanbot_interface.py -c```

    <br>
    For a full list of Scanbot commands, see [commands](./commands). Alternatively run the ```help``` command or, for help with a specific command, run ```help <command_name>```.
  </details>

3. <details>
    <summary>Zulip</summary>
    Running via zulip is the most flexible implementation of Scanbot. You can send commands and receive data from anywhere and in real time via chat streams.
    <br><br>
    1. Clone the [nanonisTCP interface](https://github.com/New-Horizons-SPM/nanonisTCP), navigate to the root directory and run ```pip install .```
    2. Clone the [Scanbot repository](https://github.com/New-Horizons-SPM/scanbot), navigate to the root directory, and run ```pip install .```
    3. Install zulip and zulip_bots
        
        ```pip install zulip```<br>
        ```pip install zulip_bots```
        
    4. [Create a zulip bot](https://zulip.com/help/add-a-bot-or-integration) and download the zuliprc file

    5. Add the following lines to scanbot_config.ini:
        
        ```zuliprc=<path_to_zuliprc>```<br>
        ```upload_method=zulip```

    6. Run ```python scanbot_interface.py -z```
    7. Run [commands](./commands) by sending messages to the Zulip bot

    <br>
    For a full list of Scanbot commands, see [commands](./commands). Alternatively run the ```help``` command or, for help with a specific command, run ```help <command_name>```.
  </details>

## Usage

Refer to the relevant user guide to see how Scanbot can help with data acquisition and probe conditioning in STM experiments.

## Contributing
If you would like to contribute to the Scanbot project you can do this through the GitHub [Issue Register](https://github.com/New-Horizons-SPM/scanbot/issues).
If you come across a problem with Scanbot or would like to request new features, you can raise a [new issue](https://github.com/New-Horizons-SPM/scanbot/issues/new).
Alternatively, scan through our [existing issues](https://github.com/New-Horizons-SPM/scanbot/issues); if you find one you're interested in fixing/implementing, feel free to open a pull request.

## Citing

If you use Scanbot in your scientific research, please consider [citing it](https://zenodo.org/badge/latestdoi/487719232).

## FLEET
Special thanks to [FLEET](https://www.fleet.org.au/) for their contribution through the [FLEET Translation Program](https://www.fleet.org.au/translation/#:~:text=A%20new%20FLEET%20program%20provides,translation%20skills%20in%20Centre%20membership.).
![FLEETLogo](fleet-logo.png)