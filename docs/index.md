# Scanbot       [![DOI](https://zenodo.org/badge/487719232.svg)](https://zenodo.org/badge/latestdoi/487719232)

Scanbot is a collection of several automated STM and nc-AFM data acquisition commands compatible with Nanonis V5 SPM control software.

## Featured
* [React Implementation of Scanbot](./featured/#web-app)<br>
* [Scanbot meets ChatGPT](./featured/#scanbot-meets-chatgpt)

## Installation
1.  Install the [nanonisTCP interface](https://github.com/New-Horizons-SPM/nanonisTCP)

2. Clone [this repository](https://github.com/New-Horizons-SPM/scanbot), navigate to the root directory, and run ```pip install .```

## Setup and Run
Scanbot can be run in the following ways:

1. <details>
    <summary>Web App (V4+ NEW!)</summary>
    Scanbot hast (mostly) been implemented using [React](https://react.dev/)
    
    On Windows, the easiest way to use it is by [downloading and running the .exe](https://firebasestorage.googleapis.com/v0/b/scanbot-46390.appspot.com/o/scanbot-react%2Fscanbot.zip?alt=media&token=ee1091ef-7b08-4ec4-903d-3892a0fbd7b0).
    Then navigating to [http://127.0.0.1:5000/](http://127.0.0.1:5000/) in a browser (tested in Chrome).
    
    Alternatively, you can install it from scratch:

    1. Install node.js from [here](https://nodejs.org/en) or if you're using anaconda, run conda install conda-forge::nodejs
    2. Navigate to ```~/scanbot/scanbot``` and ```run npm install```
    3. Start the server: navigate to ```~/scanbot/server/``` and run ```python server.py```
    4. Start the web app: navigate to ```~/scanbot/scanbot/``` and run ```npm start```

    <br>

    <strong>Documentation available [here](./web-app)</strong>
  </details>

2. <details>
    <summary>Broswer (V3+)</summary>
    Thanks to [holoviz Panel](https://panel.holoviz.org/), Scanbot runs in a browser from V3 onwards.
    <br><br>
        1. Find the ```scanbot_interface.py``` script (up to V3: ```~/scanbot/scanbot/```, or in V4: ```~/scanbot/server/```)
        <br>
        2. Run ```python scanbot_interface.py -gui```
    <br><br>
    <strong>Documentation available [here](./gui)</strong>
  </details>

3. <details>
    <summary>Terminal (V1+)</summary>
    Running Scanbot from a terminal:
    <br><br>
    Run ```python scanbot_interface.py -c```

    <br>
    For a full list of Scanbot commands, see [commands](./commands). Alternatively run the ```help``` command or, for help with a specific command, run ```help <command_name>```.
  </details>

4. <details>
    <summary>Zulip (V1+)</summary>
    Running via zulip is the most flexible implementation of Scanbot. You can send commands and receive data in real time via chat streams.
    <br><br>
    1. Install zulip and zulip_bots
        
        ```pip install zulip```<br>
        ```pip install zulip_bots```
        
    2. [Create a zulip bot](https://zulip.com/help/add-a-bot-or-integration) and download the zuliprc file

    3. Add the following lines to scanbot_config.ini:
        
        ```zuliprc=<path_to_zuliprc>```<br>
        ```upload_method=zulip```

    4. Run ```python scanbot_interface.py -z```
    5. Run [commands](./commands) by sending messages to the Zulip bot

    <br>
    For a full list of Scanbot commands, see [commands](./commands). Alternatively run the ```help``` command or, for help with a specific command, run ```help <command_name>```.
  </details>

## Usage

For example automation work-flow, see [Intended Usage](./automation/#intended-usage). To write your own custom Scanbot commands, see [hk_commads](./hooks/#hk_commands).

### Configuration
The scanbot_config.ini configuration file can store things like the default IP adress, default TCP Ports, etc. Save it in the project's root directory.
See [configuration](./configuration.md) for more details.
An example config file is:
```
ip=127.0.0.1                    # IP of the machine running Nanonis
port_list=6501,6502,6503,6504   # Available TCP ports
upload_method=path              # Configure Scanbot to save PNGs locally
path=./scanbot_images/          # Directory for saved PNGs

```

### Functional Overview
* STM
    - Bias dependent imaging with drift correction
    - Automated sample surveying (NxN grid)
* nc-AFM
    - z-dependent nc-AFM
    - nc-AFM registration
* Automation
    - Tip shaping
    - Full control over the course motors
* Hooks
    - Scanbot has a number of built-in [hooks](./hooks) to let you customise key functionality.

## Contributing
If you would like to contibute to the Scanbot project you can do this through the GitHub [Issue Register](https://github.com/New-Horizons-SPM/scanbot/issues).
If you come across a problem with Scanbot or would like to request new features, you can raise a [new issue](https://github.com/New-Horizons-SPM/scanbot/issues/new).
Alternatively, scan through our [existing issues](https://github.com/New-Horizons-SPM/scanbot/issues); if you find one you're interested in fixing/implementing, feel free to open a pull request.

## Citing

If you use Scanbot in your scientific research, please consider [citing it](https://zenodo.org/badge/latestdoi/487719232).

## FLEET
Special thanks to [FLEET](https://www.fleet.org.au/) for their contribution through the [FLEET Translation Program](https://www.fleet.org.au/translation/#:~:text=A%20new%20FLEET%20program%20provides,translation%20skills%20in%20Centre%20membership.).
![FLEETLogo](fleet-logo.png)