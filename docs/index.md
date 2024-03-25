<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-6MK4DRHXWM"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'G-6MK4DRHXWM');
</script>
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

There are several ways to install Scanbot:

1. <strong>Quick Start:</strong><br><br>
    For a quick start <strong>on Windows</strong>, download and run the .exe file from <a href="https://scanbot-46390.web.app" target="_blank">here</a>.
    This method automatically sets up and launches the Scanbot web app.
<br><br>
2. <strong>Installing via pip:</strong><br><br>
If you prefer using pip, you can install Scanbot directly with:
<br>
```pip install scanbot```
<br><br>
3. <strong>Building from Source:</strong><br><br>
    To install Scanbot from its source, particularly if you want the latest version or wish to contribute to its development, follow these steps:

    1. Clone the [Scanbot repository](https://github.com/New-Horizons-SPM/scanbot)
    2. Install node.js from [here](https://nodejs.org/en) or if you're using anaconda, run ```conda install conda-forge::nodejs```
    3. Navigate to ```scanbot/scanbot/App``` and run ```npm install```
    4. From the same directory, run ```npm run build```
    5. Navigate to the project root directory, and run ```pip install .```
    6. Start Scanbot by running the command ```scanbot```


## Running:

Scanbot can be run as a web application, in a terminal, or via the open-source messaging platform, [Zulip](https://zulip.com/):

1. <strong>Web Application:</strong><br><br>
    The web app can be launched by running the command: ```scanbot```
    <br><br>
    You can <strong>test Scanbot with the Nanonis V5 Simulator</strong> before integrating it with your STM by following [these instructions](./web-app-test).
    <br><br>
    The general <strong>user guide</strong> is available [here](./web-app)</strong>.
<br><br>
2. <strong>Terminal:</strong><br><br>
    Scanbot can run in a terminal after running: ```scanbot -c```
    <br><br>
    For a full list of Scanbot commands, see [here](./commands). Alternatively run the ```help``` command or, for help with a specific command, run ```help <command_name>```.
<br><br>
3. <strong>Zulip:</strong><br><br>
    Running via Zulip is the most flexible implementation of Scanbot. You can send commands and receive data from anywhere and in real time via chat streams.
    You must follow a few additional steps first:
    
    1. Install zulip and zulip_bots
        
        ```pip install zulip```<br>
        ```pip install zulip_bots```
        
    2. [Create a zulip bot](https://zulip.com/help/add-a-bot-or-integration) and download the zuliprc file

    3. Add the following lines to scanbot_config.ini:
        
        ```zuliprc=<path_to_zuliprc>```<br>
        ```upload_method=zulip```
    
    4. Launch Scanbot by running: ```scanbot -z```
    <br><br>
    
    For a full list of Scanbot commands, see [here](./commands). Alternatively run the ```help``` command or, for help with a specific command, run ```help <command_name>```.
<br>

## Contributing
If you would like to contribute to the Scanbot project you can do this through the GitHub [Issue Register](https://github.com/New-Horizons-SPM/scanbot/issues).
If you come across a problem with Scanbot or would like to request new features, you can raise a [new issue](https://github.com/New-Horizons-SPM/scanbot/issues/new).
Alternatively, scan through our [existing issues](https://github.com/New-Horizons-SPM/scanbot/issues); if you find one you're interested in fixing/implementing, feel free to open a pull request.

## Citing

If you use Scanbot in your scientific research, please consider [citing it](https://zenodo.org/badge/latestdoi/487719232).

## FLEET
Special thanks to [FLEET](https://www.fleet.org.au/) for their contribution through the [FLEET Translation Program](https://www.fleet.org.au/translation/#:~:text=A%20new%20FLEET%20program%20provides,translation%20skills%20in%20Centre%20membership.).
![FLEETLogo](fleet-logo.png)