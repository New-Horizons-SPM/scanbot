<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-6MK4DRHXWM"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'G-6MK4DRHXWM');
</script>
# Scanbot Web App

![WebApp](./appim/top-level.png)

Scanbot is available as a web application built with [React](https://react.dev/).
This application is still being developed, with the following features already fully implemented:

* Sample Surveying
* Bias Dependent Imaging
* Tip Shaping
* End-To-End Survey Automation

This page describes the function and parameters for all features accessible in the web application.
Note that in the application you can also hover over any of the parameters to obtain a detailed description about it.

# Installation


There are several ways to install Scanbot:

1. For a quick start on Windows, download and run the .exe file from <a href="https://scanbot-46390.web.app" target="_blank">here</a>.
This method automatically sets up and launches the Scanbot web app.

2. Installing via pip
If you prefer using pip, you can install Scanbot directly with the following command:
<br>
```pip install scanbot```
<br><br>
You can then launch Scanbot by running the command:
<br>
```scanbot```

3. Building from Source:

    1. Clone the [Scanbot repository](https://github.com/New-Horizons-SPM/scanbot)
    2. Install node.js from [here](https://nodejs.org/en) or if you're using anaconda, run ```conda install conda-forge::nodejs```
    3. Navigate to ```scanbot/scanbot/App``` and run ```npm install```
    4. From the same directory, run ```npm run build```
    5. Navigate to the project root directory, and run ```pip install .```
    6. Start Scanbot by running the command ```scanbot```

<br>

<strong>You can test Scanbot with the Nanonis V5 Simulator</strong> before integrating it with your STM by following [these instructions](../web-app-test).</strong>

# Configuration
From the landing page, you can access Scanbot's configuration.
Upon accepting the configuration, your scanbot_config.ini file will be saved automatically and your settings will be remembered.
These settings can be updated any time.

| Parameter                                                | Default Value                          | Description |
| -------------------------------------------------------- | -------------------------------------- | ----------- |
| IP Adress                                                | 127.0.0.1                              | IP address of the computer hosting Nanonis. If running Scanbot on the same machine, use the default local host IP                                                                                                                                                                                                                                      |
| TCP Ports                                                | 6501,6502,6503,6504                    | Comma-delimited ports for TCP connection. See Nanonis > System > Options > TCP Programming Interface                                                                                                                                                                                                                                                   |
| Nanonis Version Number                                   | 99999999                               | Check your Nanonis version number in Nanonis > help > info. Default value represents the latest version                                                                                                                                                                                                                                                |
| Crash Current (A)                                        | 5e9                                    | Threshold current that is considered a tip crash when moving the Piezos. The tip will automatically retract until the current is below this current if a crash is detected.                                                                                                                                                                            |
| Crash Retract Frequency (Hz)                             | 1500                                   | Frequency applied to retract the coarse Z piezo in the event of a crash                                                                                                                                                                                                                                                                                |
| Crash Retract Voltage (V)                                | 200                                    | Voltage applied to retract the coarse piezo in the event of a crash                                                                                                                                                                                                                                                                                    |
| Topo basename                                            |                                        | Base name for saved sxm files acquired by scanbot. Leave empty to keep settings in Nanonis                                                                                                                                                                                                                                                             |


# Data Acquisition
From the landing page, you can access the data acquisition tools, including tools to help automate the STM.
![DataAcquisition](./appim/data-acquisition.png)

## Survey
![DataAcquisition](./appim/survey.png)

When the Survey function is selected, the parameters in the table below can be configured.
Note that answering ```Yes``` to ```Auto tip shaping?```, is only possible after following a short
[initialisation procedure](#automation). After completing this initialisation procedure, Scanbot can integrate the automated tip shaping with sample surveying. The process is as follows:
1. Images acquired during the survey are analysed and deemed 'good' or 'bad' based on how much the tip interacts with the sample.
2. If <strong>five 'bad' images are detected in a row</strong>, the survey will be stopped. Scanbot will then use the camera feed to track and move the tip to the clean reference metal.
3. Upon appraching on the clean reference metal, Scanbot will launch the automated tip shaping routine.
4. After acquiring a tip suitable for imaging, Scanbot will move the STM tip back to the sample of interest.
5. A new survey will automatically begin.

<strong>It's a good idea to go through [these steps](../web-app-test) using the Nanonis Simulator to get comfortable with how Scanbot automates surveys before trying this on your STM.</strong>

| Parameter                                            | Description                                                                                                                                                                                                                                                                                                                             |
|------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Survey fine grid size (NxN)                          | Surveys are grids of images. This parameter defines the grid size. For example, if N=3, the survey grid will be 9 images in a 3x3 grid                                                                                                                                                                                                  |
| Survey coarse grid size X/Y                          | The coarse grid is a macroscopic grid of points on the sample where surveys will be carried out.<br>At the completion of each survey, the coarse piezos will move the tip to the next location in the course grid.<br>The course grid size is XxY.<br>For example, if X=5 and Y=2, a total of 10 fine-grid surveys will be carried out. |
| Scan size (m)                                        | Length and width of each image in the survey in meters                                                                                                                                                                                                                                                                                  |
| Scan spacing (m)                                     | Spacing between images in a survey in meters                                                                                                                                                                                                                                                                                            |
| Number of pixels                                     | Number of pixels in each image in the survey                                                                                                                                                                                                                                                                                            |
| Scan bias (V)                                        | Bias the images in the survey will be acquired at                                                                                                                                                                                                                                                                                       |
| Filename suffix                                      | String that will be appended to the end of the .sxm filenames for all images acquired in the survey                                                                                                                                                                                                                                     |
| Drift compensation (s)                               | Number of seconds after which to restart each scan. This is to accommodate for drift induced by the scan frame moving.                                                                                                                                                                                                                  |
| Number of motor steps (Z+)                           | Number of motor steps the tip will retract before moving to the next survey location in the coarse grid                                                                                                                                                                                                                                 |
| Piezo voltage during Z+ motor steps (V)              | Voltage applied to the Z piezos when retracting the tip before moving to the next coarse grid location                                                                                                                                                                                                                                  |
| Piezo frequency during Z+ motor steps (Hz)           | Frequency applied to the Z piezos when retracting the tip before moving to the next coarse grid location                                                                                                                                                                                                                                |
| Number of motor steps (X/Y)                          | Number of piezo motor steps (after retracting in Z+) between coarse grid locations                                                                                                                                                                                                                                                      |
| Piezo voltage during X/Y motor steps (V)             | Voltage applied to the X/Y piezos when moving to the next coarse grid location                                                                                                                                                                                                                                                          |
| Piezo Frequency during X/Y motor steps (Hz)          | Frequency applied to the X/Y piezos when moving to the next coarse grid location                                                                                                                                                                                                                                                        |
| Call hk_survey.py after each image?                  | Answer 'Yes' if you've written a custom hk_hook.py hook that you want executed after each scan completes                                                                                                                                                                                                                                |
| Call hk_classifier.py instead of default classifier? | Answer 'Yes' if you've written a custom hk_classifier.py hook to analyse completed scans and determine if the tip needs reshaping                                                                                                                                                                                                       |
| Auto tip shaping?                                    | Answer 'Yes' if you want Scanbot to automatically move the tip to the clean reference metal and reshape the tip when it detects a bad tip                                                                                                                                                                                               |

## Bias Dependent Imaging

The bias dependent imaging function lets you take a series of drift-corrected images at different bias values. The plot area will show the latest image side-by-side with a GIF of all the previously acquired images in the set.
![biasdepwindow](./appim/bias-dep.png)

When the Bias Dependent function is selected, the following parameters can be configured:

| Parameter                                            | Description                                                                                                                                                                 |
|------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Number of images                                     | Number of images to acquire between the initial and final bias                                                                                                              |
| Initial bias (V)                                     | Bias of the first image in the set                                                                                                                                          |
| Final bias (V)                                       | Bias of the final image in the set                                                                                                                                          |
| Pixels in data image                                 | Number of pixels in the bias dependent scans. This must be a multiple of 16 in nanonis                                                                                      |
| Lines in data image                                  | Number of lines in the bias dependent scans                                                                                                                                 |
| Time per line during data acquisition (s)            | Sets the forward speed of the tip during bias dependent scans                                                                                                               |
| Backwards time per line multiplier                   | Sets the backward speed of the tip during bias dependent scans. (2 = twice as fast as the forward speed)                                                                    |
| Pixels in drift correction image                     | Number of pixels during the frames taken for drift correction purposes.<br>A drift correction frame is acquired between each of the bias dependent scans at a constant bias |
| Lines in drift correction image                      | Number of lines during the frames taken for drift correction purposes.<br>Set this to 0 to keep the same ratio as pixels/lines in the bias dependent images                 |
| Bias during drift correction (V)                     | Bias that the drift correction frames are acquired at.<br>Set this to 0 to turn off drift correction                                                                        |
| Time per line during drift correction (s)            | Sets the forward speed of the tip when acquiring drift correction images                                                                                                    |
| Backwards time per line multiplier                   | Sets the backward speed of the tip during drift correction scans. (0.5 = half the speed as the forward speed)                                                               |
| Suffix                                               | Text to append to the .sxm filenames for all images in this set                                                                                                             |

## STS Grid

The STS Grid function lets you acquire a drift-corrected STS map.
The plot area will show the latest drift-correction image alongside a gif of previous drift-correction images to keep track of overall drift during the experiment.
The process of the experiment is as follows:

1. The existing Pattern Grid is loaded in from Nanonis.
2. A check is carried out to ensure the STM tip and the grid centre are both within the current scan frame. If not, the scan will not start.
3. An image is taken in the upward scan direction as a reference to measure future drift. The image bias and setpoint can be configured in the settings.
4. The bias and setpoint are adjusted to configured values, then tip moves to the first location in the grid.
5. The STS setpoint current and bias is then applied before acquiring a spectrum.
6. Steps 4 and 5 are repeated until a configurable number of spectra are taken. <strong>Note that the setpoint at which the tip moves between grid points can be different to that of the acquired spectra.<strong>
7. A drift correction image is acquired and compared with the original frame. If any drift is detected, the scan frame and grid centre are updated to compensate. <strong>Note that the bias and setpoint current of the drift correction images can be configured differently to that of the acquired spectra.</strong>
8. Steps 4 to 7 are repeated until the grid completes.

The output grid data (apart from being autosaved as individual .dat files by Nanonis) will be saved in the specified directory in the form of a [pickled](https://www.geeksforgeeks.org/understanding-python-pickling-example/) Python dictionary with the following structure:
```Python
grid_data['sweep_signal'] # contains the sweep signal, in this case it is the nanonis "bias calc (V)" signal
grid_data[<channel_name>] # contains a 3D matrix of the grid data, where axis 0 and 1 are the spatial axes, while axis 2 is the measured signal axis.
```
<strong>Note that <channel_name> can be any of the recorded channels highlighted in the Nanonis Bias Spectroscopy module.</strong>
The output grid file is never locked and will be updated in real-time after each spectrum within the grid is acquired.

![stsgridwindow](./appim/sts-grid.png)

The following Python code shows how to visualise the output grid data:
```Python
# %%
import pickle
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import savgol_filter as savgol
import matplotlib.animation as animation
from scipy.ndimage import gaussian_filter as gaussian
from scipy.stats import norm

########## Parameters ##########
path = "C:/Users/<path to your folder/"                                         # Path where the grid data file is saved
filename = "scanbot-sts-grid.pk"                                                # Filename of the grid data to plot
channel  = 'Current (A)'                                                        # Channel to plot
deriv    = True                                                                 # Take the derivative of the signal? (e.g. dIdV from current)
bias     = -0.1                                                                 # Bias slice to plot from the grid data
makeGif  = True                                                                 # Turn data into gif. can take a long time.
gif_n    = 10                                                                   # Take every gif_nth slice in the grid so the gif isn't so large
########## Parameters ##########

pk = pickle.load(open(path + filename,'rb'))                                    # Loads in the .pk grid file

data  = pk['data']
sweep = data['sweep_signal']                                                    # Sweep signal is the bias for bias spectroscopy
grid  = np.array(data[channel])                                                 # Extract the signal for the selected channel. Use np.flipud because the first point in the grid is at the bottom.
if(deriv):
    # increasing the window_lenth increases the smoothing before taking the derivative
    grid = savgol(grid, window_length=3, polyorder=1, deriv=1, axis=2)          # Take the derivative to get dI/dV

index = np.argmin(abs(sweep - bias))                                            # Index of the bias we want to plot
gridSlice = grid[:,:,index].copy()                                              # Take a slice out of the grid at the selected bias

mask = gridSlice == 0
gridSlice[mask] = np.nan                                                        # Make the zeros nan so they don't spoil the contrast when plotting

# Plotting a slice of the grid
fig = plt.figure()
ax  = fig.add_subplot(111)
ax.imshow(gridSlice)

if(makeGif):                                                                    # Create and save a gif of the output grid
    fig = plt.figure(1,figsize=(10,5))
    ax = fig.add_subplot(111)
    
    ims = []                                                                    # Array of images to be turned into gif
    for i in range(0,np.size(grid,2)):                                          # Loop through all of the slices in the grid
        if(i%gif_n): continue                                                   # Only use every gif_nth frame in the gif to save time and space
        image = grid[:,:,i]
        
        image = gaussian(image,1)                                               # Spatial filtering... Comment this line out if you don't want any spatial filtering
        
        #Define colour scale saturation
        mu, sigma = norm.fit(image)
        vmin = mu - 2*sigma
        vmax = mu + 2*sigma
             
        #Plot
        im = plt.imshow(image,cmap='magma',animated=True,origin='lower',vmin=vmin,vmax=vmax)
        plt.axis('off')
        ttl = plt.text(0.5, 1.01, "Bias = %f V" % sweep[i], horizontalalignment='center', verticalalignment='bottom', transform=ax.transAxes)
        
        ims.append([im,ttl])
        
    ani = animation.ArtistAnimation(fig,ims,interval=200,blit=True,repeat_delay=1000)
    ani.save(path + filename + '.gif',writer='imagemagick')                     # save the gif
    
```

# Automation

From the Automation screen, you can initiate the following actions:

* Automated tip shaping
* Tip, sample, and reference metal initialisation
* Move tip to sample/metal

## Automated Tip Shaping

Scanbot can [automatically acquire a tip](../automation/#tip-preparation) suitable for imaging via its tip-shaping protocol. The process is as follows:

1. An NxN grid is set up within the scannable region
2. A small scan is acquired at the first location in the grid
3. If the scanned region is flat/clean, it is deemed suitable for creating an imprint. If not, the scan frame is moved to the next location in the grid and the process repeats
4. The tip apex creates an imprint in the middle of the scan window via a gentle tip-shaping action
5. The imprint of the tip apex is imaged
6. The imprint is analysed and given a size score (in units of nm2) and a circularity score (from 0 to 1)
7. If the target size and circularity values are not met, the scan frame moves to the next location and the process is repeated
8. If the target size and circularity values are met, the process completes

When intitiated from the Automation screen, the plot area will show the latest tip imprint alongside a GIF of all previous tip imprints from the given run.
This lets you observe how the geometry at the apex of the probe evolves with each iteration.

![autotipshape](appim/autotipshaping.png)

The following parameters can be configured for this action:

| Parameter                                                 | Description                                                                                                                                                                               |
|-----------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Tip shaping grid size (NxN)                               | The total number of tip-shaping attempts will be NxN                                                                                                                                      |
| Scan size (m)                                             | Size of the scan window when imaging the tip imprint                                                                                                                                      |
| Desired symmetry (0=asymmetric, 1=perfect circle)         | Circularity score that needs to be met before tip-shaping is successful.<br>The imprint circularity is calculated by analysing its contour.<br>0.85 or more will generally be good enough |
| Maximum size (nm2)                                        | Maximum area in units of nm2 of the imprint.<br>This will vary for different metal surfaces.<br>2.5 is a good starting point                                                              |
| Tip depth when assessing imprint (m)                      | Amount to crash the tip when creating an imprint to be analysed.<br>This will vary for different metal surfaces.<br>-1.1e-9 is a good starting point                                      |
| Tip depth when reshaping the tip (m)                      | Maximum amount to crash the tip when reshaping it.<br>-10e-9 to -15e-9 is a good starting point if the rng is turned on                                                                   |
| Randomise tip depth from 0 to above value when reshaping? | Randomising the tip crash depth from zero to a maximum value seems to work better than try the same value over and over.<br>Generally select 'Yes' for this option                        |
| Drift compensation time (s)                               | Restarts each scan after this many seconds to compensate for drift when moving scan frames.<br>1 s is generally ok here                                                                   |
| Demo mode?                                                | Load pngs from a pickled file instead of scan window (useful for testing purposes)                                                                                                        |
| Call the hook hk_tipshape?                                | Call your own hk_tipshape.py hook to configure custom tip-shaping parameters based on images of the tip's imprint                                                                         |

## Initialising the Tip, Sample, and Reference Metal Locations

Before the automatic tip preparation can be incorporated into surveys, the tip, sample, and clean reference metal locations must be initialised.
This allows Scanbot to later track and maneuver the tip via the camera feed when required.
From the Automation screen, simply click the 'initialise' button, allow the browser to use the camera, and follow the prompts.
Once these locations are initialised, you will be able to answer 'Yes' to the ```Automated Tip Shaping?``` field in the Survey screen.
In the screenshot below, the red marker indicates the initial position for the tip's apex;
the green markers show the locations of the sample and clean reference metal.

![initialisation](appim/initialisation.png)

## Move Tip

After initialising the tip, sample, and reference metal locations, you will be able to tell Scanbot to track and move the STM tip from its current position to either the sample or reference metal locations.
<strong>Scanbot will always move the tip in the positive Z direction until the tip apex is above the target location. Only then will the X piezo be used to move the tip to its target.</strong>
The 'Go to Metal' and 'Go to Sample' buttons are intended to be used for testing purposes to see how well Scanbot can track the STM tip with your camera setup and specific lighting conditions.

<strong>Note:</strong>
The primary concern when it comes to automating movement of the STM head is accidental tip crashes.
The following rules have been applied to any command where the coarse piezos are utilised:
<br>

- Scanbot can never move the tip in the ```Z-``` direction (down) when using the coarse piezo. Instead, auto approach is used.
- When moving in ```X``` or ```Y``` directions, <strong>the tunnelling current must be monitored after every 10 steps</strong>.
- A tunnelling current greater than the threshold set in the [configuration](#configuration) is considered a crash.
- In the event of a crash, the tip will be retracted using the ```Z+``` piezo and operation will cease.

**Please make sure to set appropriate piezo voltages and frequencies when using any of the commands that control the coarse piezos.**
<br><br><br>
