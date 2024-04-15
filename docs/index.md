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
We welcome contributions from the community to Scanbot. Here's how you can contribute:

### Issues
Encounter a problem? Please report it by [opening a new issue](https://github.com/New-Horizons-SPM/scanbot/issues/new). If you're able to fix the issue yourself, feel free to submit a pull request.

### Feature Requests
Have an idea for a new feature? Submit it through our [issue tracker](https://github.com/New-Horizons-SPM/scanbot/issues/new). Please provide detailed information about your feature to help us understand your vision.

### Develop New Scanbot Commands
Interested in expanding Scanbot's capabilities? Follow these steps:

1. Open a new issue detailing your proposed command.
2. If approved, you can either develop your command using the [hk_commands hook](./hooks/#hk_commands) or by updating Scanbot's source directly.
3. Submit a pull request for review.

### Pull Requests
If you're going to submit a pull request for any of the above please ensure the following:

1. Changes are compatible with the latest version of the V4 branch
2. Titles and summaries are clear, concise, and explain the rationale behind the changes, what issues they address, and any other relevant context.
3. You have an open issue that can be linked to the pull request.
4. All new code is well-documented and any new features or bug fixes include appropriate tests.
5. Tag ceds92 for review as they are the main reviewer for this project. Include any other contributors who might be impacted by or interested in the changes.

### Documentaion
If your changes to Scanbot require updates to the documentation, please handle this on the mkdocs branch.
You can update the documentation there and submit a separate pull request linked to the same issue:

1. Check out the mkdocs branch from the main repository.
2. Update or add documentation to reflect the changes made to the software. Ensure that all new features, configurations, or usage instructions are clearly documented.
3. Use clear, concise language and format the documentation for easy reading. Include examples if applicable.
4. Submit a pull request for the documentation updates, ensuring it references the same issue as your code changes.
5. Tag ceds92 in the pull request for the documentation as well, to ensure consistency and accuracy in both code and informational updates.

### Support

If you have questions or need assistance that the documentation doesn’t address, please don’t hesitate to open an issue in our [issue tracker](https://github.com/New-Horizons-SPM/scanbot/issues/new).
We are committed to providing support and will do our best to assist you promptly!

## Citing

If you use Scanbot in your scientific research, please consider [citing it](https://zenodo.org/badge/latestdoi/487719232).

## FLEET
Special thanks to [FLEET](https://www.fleet.org.au/) for their contribution through the [FLEET Translation Program](https://www.fleet.org.au/translation/#:~:text=A%20new%20FLEET%20program%20provides,translation%20skills%20in%20Centre%20membership.).
![FLEETLogo](fleet-logo.png)