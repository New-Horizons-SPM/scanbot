# Hooks
[Hooks](https://www.rswebsols.com/tutorials/programming/software-development-hook-hooking) allow you to add or replace key components of Scanbot's functionality where system-specific customisation is required.
The ability to do this without rewriting source code means you can pull Scanbot updates without losing your custom functionality. For example, Scanbot monitors a camera feed when tracking the motion of the STM
head during automated operation; a task that may require a light to be switched on or off at times. Obviously, the code needed to achieve this will vary from system to system. This is where the user-written hook
```hk_light.py``` would be called by Scanbot to perform such a task. This page details all the hooks currently available to Scanbot. Feel free to raise an issue on the GitHub page if you require a hook at a certain
point in Scanbot's source code. All hooks must be saved in the directory ~/scanbot/scanbot/

## hk_light
This hook is called by any function that requires control over the STM light when monitoring the camera feed.

* Inputs: None
* Outputs: None
* Error handling: Raise an ```Exception``` if unable to turn the light on or off

Structure:
hk_light.py must contain two functions: ```turn_on``` and ```turn_off```. An example is shown below:
```Python
def turn_on():
    # Code to turn light on
    # If unsuccessful:
        # Raise Exception
    # If successful:
    print("Light on!")
        
def turn_off():
    # Code to turn light off
    # If unsuccessful:
        # Raise Exception
    # If successful:
    print("Light off!")
```
<br>


## hk_survey
This hook can be called at the completion of every scan in a ```survey``` or ```survey2``` when the ```-hk_survey``` option is set.

* Inputs:
    1. Raw scan data
    2. .sxm filename
    3. A Python dictionary containing metadata about the scan
* Outputs: None
* Error handling: None

Structure:
hk_survey.py must contain the function ```run```. An example is shown below:
```Python
def run(scan_data,filename,metadata):
    # Code to process the image (e.g. plane fit, filtering, etc.)
    # Code to save the image or send the image to a server
    # Code to do anything you want
```

## hk_classifier
This hook can called at the completion of every scan in a ```survey``` or ```survey2``` when the ```-autotip``` and ```-hk_classifier``` options are set.
Its purpose is to use an alternative image classifier when assessing the quality of completed STM images and to decide when Scanbot should reshape the tip.

* Inputs:
    1. Raw scan data
    2. .sxm filename
    3. Record of all previous classifications - a list of dictionaries
* Outputs:
    1. A python dictionary containing classification labels. The only mandatory label is "tipShape". This is what tells Scanbot whether to execute a tip shape or not.
* Error handling: None

Structure: hk_classifier.py must contain the function ```run```. An example is shown below:
```Python
def run(scan_data,filename,classification_hist):
    # Code to process the image (e.g. plane fit, filtering, etc.)
    
    # API call to external classifier (e.g. AI agent)
    
    classification = {"tipChanges": <output from classifier>,   # Example trait to keep track of
                      "unstable": <output from classifier>,     # Example trait to keep track of
                      "multipleTips": <output from classifier>, # Example trait to keep track of
    
    # Check the classification history to see if we've had a bad run of images
    
    if(num_bad_images > threshold):
        classification["tipShape"] = True                       # Tell Scanbot to reshape the tip
    else:
        classification["tipShape"] = False                      # Tell Scanbot not to reshape the tip
        
    return classification
```

## hk_tipShape
This hook can be called from the auto_tip_shape command, prior to performing a tip shaping action, when the ```-hk_tipShape``` option is set.
Its purpose is to adjust the tip shaping parameters based on either the image of the tip's imprint or the size and symmetry scores assigned to the imprint by Scanbot.

* Inputs:
    1. Image of the region prior to making the imprint
    2. Image of the tip's imprint
    3. 1D array containing all the tip shaping properties. See [nanonisTCP.TipShaper](https://github.com/New-Horizons-SPM/nanonisTCP).
    4. Size score (nm2) assigned by Scanbot.
    5. Circularity score (0=very bad, 1=perfect circle) assigned by Scanbot
* Outputs:
    1. (Optional) 1D array containing the desired tip shaping parameters.
* Error handling: None

Structure: hk_tipShape.py must contain the funtion ```run```. An example is show below:
```Python
def run(cleanImage, tipImprint, tipShapeProps, size, sym):
    # Code to filter tipImprint
    
    # API call to RL Agent to determine appropriate tip shaping parameters
    
    # Adjust relevant tip shaping parameters
    tipShapeProps[3] = agent.z1     # Amount to plunge the tip into the surface (m)
    tipShapeProps[5] = agent.bias   # Bias applied while the tip is in the suface (V)
    tipShapeProps[7] = agent.z2     # Amount to pull tip out of the surface (m)
    
    return tipShapeProps            # Return the updated tip shaping properties
```