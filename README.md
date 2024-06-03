04/06/2024
Note: There are currently some issues that might arise due to incompatibilites of the NanonisTCP interface and different versions of Nanonis V5 software. I will be working through these over the next couple of weeks. Please open an issue if you experience such problems, thanks!

# V4 Update!
Scanbot has been implemented as a web application using [React](https://react.dev/).
    
On Windows, the easiest way to use it is by downloading the <a href="https://scanbot-46390.web.app" target="_blank">executable</a>.

Alternatively, Scanbot can be installed via ```pip install scanbot``` and launched with ```scanbot```
    
Full documentation available [here](https://new-horizons-spm.github.io/scanbot/web-app/).

# Scanbot       [![DOI](https://zenodo.org/badge/487719232.svg)](https://zenodo.org/badge/latestdoi/487719232)

Scanbot is a collection of several automated STM and nc-AFM data acquisition commands compatible with Nanonis V5 SPM control software.
Full documentation available [here](https://new-horizons-spm.github.io/scanbot/).

### Functional Overview
* STM
    - Bias dependent imaging with drift correction
    - Automated sample surveying (NxN grid)
* STS
    - STS Grids with drift correction
* nc-AFM
    - z-dependent nc-AFM
    - nc-AFM registration
* Automation
    - Tip shaping
    - Full control over the course motors
* Hooks
    - Scanbot has a number of built-in [hooks](https://new-horizons-spm.github.io/scanbot/hooks/) to let you customise key functionality.

## Contributing

If you wish to contribute to Scanbot in any way, please refer to [these guidlines](https://new-horizons-spm.github.io/scanbot/#contributing).

## Citing

If you use Scanbot in your scientific research, please consider [citing it](https://zenodo.org/badge/latestdoi/487719232).

## FLEET
Special thanks to [FLEET](https://www.fleet.org.au/) for their contribution through the [FLEET Translation Program](https://www.fleet.org.au/translation/#:~:text=A%20new%20FLEET%20program%20provides,translation%20skills%20in%20Centre%20membership.).
