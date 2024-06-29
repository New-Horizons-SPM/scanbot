# Scanbot       [![DOI](https://zenodo.org/badge/487719232.svg)](https://zenodo.org/badge/latestdoi/487719232)

Scanbot is a collection of several automated STM and nc-AFM data acquisition commands compatible with Nanonis V5 and V5e SPM control software (stable with R12280 and later).

<strong>Full documentation available [here](https://new-horizons-spm.github.io/scanbot/web-app/).</strong>

## Functional Overview
* STM
    - Bias dependent imaging with drift correction
    - Automated sample surveying (NxN grid)
* STS
    - STS Grids with drift correction
* nc-AFM (coming soon in the web app version)
    - z-dependent nc-AFM
    - nc-AFM registration
* Automation
    - Tip shaping
    - Full control over the course motors
* Hooks
    - Scanbot has a number of built-in [hooks](https://new-horizons-spm.github.io/scanbot/hooks/) to let you customise key functionality.

## Quick Start
### Download and Run on Windows
On Windows, you can download and run the <a href="https://scanbot-46390.web.app" target="_blank">Scanbot executable</a>.

### Install with pip
Alternatively, Scanbot can be installed with pip:

```pip install scanbot```

#### Launch as a Web Application
To launch Scanbot as a web application, run:

```scanbot```

It should automatically open and run in a new browser tab. If it doesn't, head to http://127.0.0.1:5000.

#### Launch in Console Mode
You can launch Scanbot in a console mode with the -c option:

```scanbot -c```

In console mode, run ```help``` to see a full list of commands. To get help with a specific command, run ```help <command name>```

For more details, refer to the [documentation](https://new-horizons-spm.github.io/scanbot/)

## Contributing

If you wish to contribute to Scanbot in any way, please refer to [these guidleines](https://new-horizons-spm.github.io/scanbot/#contributing).

## Citing

If you use Scanbot in your scientific research, please consider [citing it](https://zenodo.org/badge/latestdoi/487719232).

## FLEET
Special thanks to [FLEET](https://www.fleet.org.au/) for their contribution through the [FLEET Translation Program](https://www.fleet.org.au/translation/#:~:text=A%20new%20FLEET%20program%20provides,translation%20skills%20in%20Centre%20membership.).
