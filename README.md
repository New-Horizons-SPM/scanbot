# V3 Update!
Thanks to [holoviz Panel](https://panel.holoviz.org/), Scanbot now has a GUI. Clone the V3 branch, follow the normal installation, then run scanbot using ```python scanbot_interface.py -gui```.

# Scanbot       [![DOI](https://zenodo.org/badge/487719232.svg)](https://zenodo.org/badge/latestdoi/487719232)

Scanbot is a collection of several automated STM and nc-AFM data acquisition commands compatible with Nanonis V5 SPM control software.
Full documentation available [here](https://new-horizons-spm.github.io/scanbot/).


## Installation
1.  Install the [nanonisTCP interface](https://github.com/New-Horizons-SPM/nanonisTCP)

2. Clone this repository, navigate to the root directory, and run ```pip install .```

## Setup and Run
Scanbot can be interfaced through a terminal or via zulip

### Terminal
Run ```python scanbot_interface.py -c```

### Zulip
1. Install zulip and zulip_bots
    
    ```pip install zulip```<br>
    ```pip install zulip_bots```
    
2. [Create a zulip bot](https://zulip.com/help/add-a-bot-or-integration) and download the zuliprc file

3. Add the following lines to scanbot_config.ini:
    
    ```zuliprc=<path_to_zuliprc>```<br>
    ```upload_method=zulip```

4. Run ```python scanbot_interface.py -z```
5. Run commands by sending messages to the Zulip bot

## Usage
For a full list of Scanbot commands, see [commands](https://new-horizons-spm.github.io/scanbot/commands/).
Alternatively run the ```help``` command or, for help with a specific command, run ```help <command_name>```.
For example work-flow automation, see [Intended Usage](https://new-horizons-spm.github.io/scanbot/automation/#intended-usage)

### Configuration
The scanbot_config.ini configuration file can store things like the default IP adress, default TCP Ports, etc. Save it in the project's root directory.
See [configuration](https://new-horizons-spm.github.io/scanbot/configuration/) for more details.
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
    - Scanbot has a number of built-in [hooks](https://new-horizons-spm.github.io/scanbot/hooks/) to let you customise key functionality.

## Citing

If you use Scanbot in your scientific research, please consider [citing it](https://zenodo.org/badge/latestdoi/487719232).

## FLEET
Special thanks to [FLEET](https://www.fleet.org.au/) for their contribution through the [FLEET Translation Program](https://www.fleet.org.au/translation/#:~:text=A%20new%20FLEET%20program%20provides,translation%20skills%20in%20Centre%20membership.).
