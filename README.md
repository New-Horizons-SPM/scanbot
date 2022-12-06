# Scanbot
Scanbot is a collection of several automated STM and nc-AFM data acquisition commands compatible with Nanonis V5 SPM control software.

## Installation
First install the [nanonisTCP interface](https://github.com/New-Horizons-SPM/nanonisTCP)

Clone this repository, navigate to the root directory, and run ```pip install .```

## Setup and Run
Scanbot can be interfaced through a terminal or via zulip
### Terminal
Run 'python scanbot_interface.py -c'

### Zulip
1. Make sure zulip and zulip_bots are installed
    ```
    pip install zulip
    pip install zulip_bots
    ```

2. [Create a zulip bot](https://zulip.com/help/add-a-bot-or-integration)\
Download the zuliprc file

3. Create a config file scanbot/scanbot/scanbot_config.ini with the fields:
    ```
    zuliprc=<path_to_zuliprc>
    upload_method=zulip
    ```

### Config File
The scanbot_config.ini configuration file can store things like default IP adress, default TCP Ports, etc.
See scanbot_interface.py/loadConfig for details. The last line of the config file must be blank.
An example config file is:
```
upload_method=path
path=./scanbot_images/
port_list=6501,6502,6503,6504
ip=127.0.0.1

```
## Usage
For a full list of commands, run the ```help``` command. For help with a specific command, run ```help <command_name>```

### Functions
* STM
  - Bias dependent imaging with drift correction
  - Automated sample surveying (NxN grid)
* nc-AFM
  - z-dependent imaging
  - nc-AFM registration
* Piezo control
  - Move area macroscopically
