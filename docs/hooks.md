<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-6MK4DRHXWM"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'G-6MK4DRHXWM');
</script>
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
    4. Array containing target size (nm2 - smaller = better) and circularity (0 = asymmetric, 1 = perfect circle) scores of the imprint.
    5. Array containing actual size and circularity scores assigned by Scanbot
    6. history: a variable to pass anything out at the end of the function, which will be passed back in on the next iteration. This is a way to keep track of what's happened in previous attempts.
* Outputs:
    1. 1D array containing the modified tip shaping parameters.
    2. History variable that contains anything you would like to keep track of. This will be passed back into the hook on the next iteration.
* Error handling: None

Structure: hk_tipShape.py must contain the funtion ```run```. An example is show below:
```Python
def run(cleanImage, tipImprint, tipShapeProps, target, actual, history):
    # Code to filter tipImprint
    
    # API call to RL Agent passing in tipImprint and history to determine next tip-shaping parameters.
    
    # Adjust relevant tip shaping parameters
    tipShapeProps[3] = agent.z1     # Amount to plunge the tip into the surface (m)
    tipShapeProps[5] = agent.bias   # Bias applied while the tip is in the suface (V)
    tipShapeProps[7] = agent.z2     # Amount to pull tip out of the surface (m)
    
    record = {"z1": agent.z1,       # Make a record of this tip-shaping attempt
              "bias": agent.bias,
              "z2": agent.z2,
              "imprint": agent.imprint)
    
    history.append(record)          # Append it to the running history so it can be taken into account on the next iteration
    
    return tipShapeProps, history   # Return the updated tip shaping properties
```

## hk_commands
This hook is used to implement custom written commands into Scanbot. To enable it, set ```hk_commands=1``` in ```scanbot_config.ini```.
Commands in hk_commands.py that have the same name as any existing Scanbot command will take priority.

Structure: hk_commands.py must contain the class ```hk_commands``` and contain the class variable ```commands```. ```commands``` is a python dictionary
that maps the command name (key), as called by the user, to the function that handles it.

Scanbot commands can be run either in the main thread or in a separate thread. The below Python code shows the implementation of two similar commands,
the first, ```change_bias```, is a scenario where threading may be unnecessary, while in the second, ```change_bias2```, it could be useful.
To test this script:

1. Set ```hk_commands=1``` in ```scanbot_config.ini```
2. Copy and paste the below code to ~/scanbot/scanbot/hk_commands.py
3. Restart Scanbot ```python scanbot_interface.py -c```
4. Try running ```help change_bias``` or simply ```change_bias -V=1```

**hk_commands.py**
```Python
from nanonisTCP.Bias import Bias                                                # Import the NanonisTCP Bias Module. Used to control the tip bias
import global_                                                                  # Import the global variables
import time                                                                     # Import time for sleeping

class hk_commands(object):
    def __init__(self,interface):                                               # Set up the constructor like this
        self.interface = interface                                              # Reference to scanbot_interface
        self.initCommandDict()                                                  # Initialise the dictionary containing a list of custom commands
    
    def initCommandDict(self):
        self.commands = {                                                       # A dictionary that maps commands with function names.
                         'change_bias'  : self.changeBias,                      # An example command without threading. Here, the user will call change_bias
                         'change_bias2' : self.changeBias2,                     # An example command with threading. Here, the user will call change_bias2
                         }
    
    def changeBias(self,user_args,_help=False):
        """
        This function changes the bias in Nanonis. It performs this task
        without the use of multi-threading which means it cannot Scanbot will
        be busy until the task is complete. This is fine for commands that will
        not interfere with other threaded tasks (e.g. taking control of the 
        motors while a survey is running). Tasks that are not threaded can run
        while a threaded task is already running. Tasks that are not threaded
        cannot be stopped until complete (i.e. running 'stop' command will not
        work).

        Parameters
        ----------
        user_args : arguments passed in by the user when calling the command
        _help     : flag set when user calls "help change_bias"

        """
        arg_dict = {'-V'    : ['0',        lambda x: float(x), "(float) Set the tip bias."],
                    '-arg2' : ['some str', lambda x: str(x),   "(str) An example user argument that defaults to 'some str' is a string."]}
        
        if(_help): return arg_dict                                              # This will get called when the user runs the command 'help exUnthreaded'
        
        error,user_arg_dict = self.interface.userArgs(arg_dict,user_args)       # This will validate args V and arg2 as float() and str(), respectively
        if(error):
            return error + "\nRun ```help change_bias``` if you're unsure."     # Inform the user of any errors in their input
        
        V,arg2 = self.interface.unpackArgs(user_arg_dict)                       # Unpack the arguments
        
        if(V == 0):                                                             # Validation
            errorMessage = "Cannot set bias to zero!"
            return errorMessage                                                 # Return with error
        
        NTCP,connection_error = self.interface.scanbot.connect()                # Connect to nanonis via TCP
        if(connection_error):
            return connection_error                                             # Return error message if there was a problem connecting        
        
        biasModule = Bias(NTCP)                                                 # The NanonisTCP Bias module
        biasModule.Set(V)                                                       # Set the bias in Nanonis
        
        self.interface.sendReply("Bias set to " + str(V) + "! arg2 = " + arg2)  # This is how you send a reply.
        
        self.interface.scanbot.disconnect(NTCP)                                 # Remember to free up the TCP port
        
        return                                                                  # Return None for success
    
    def changeBias2(self,user_args,_help=False):
        """
        This function will change the bias in Nanonis by threading the function
        "threadedFunction" after validating user input. Only one threaded
        function can run at a time. If the user tries to run a second threaded
        function, they will be presented with an error. This is handled by the
        global flags in global_. Threaded tasks run in the background and can
        be stopped by the user running the "stop" command.

        Parameters
        ----------
        user_args : arguments passed in by the user when calling the command
        _help     : flag set when user calls "help change_bias2"

        """
        arg_dict = {'-V'    : ['0',  lambda x: float(x), "(float) Set the tip bias."],
                    '-wait' : ['10', lambda x: int(x),   "(int) Seconds to wait after changing bias."]}
        
        if(_help): return arg_dict                                              # This will get called when the user runs the command 'help exUnthreaded'
        
        error,user_arg_dict = self.interface.userArgs(arg_dict,user_args)       # This will validate args V and wait as float() and int(), respectively
        if(error):
            return error + "\nRun ```help change_bias2``` if you're unsure."    # Inform the user of any errors in their input
        
        args = self.interface.unpackArgs(user_arg_dict)                         # Unpack the arguments
        
        func = lambda : self.threadedFunction(*args)                            # Handle to the function to be threaded
        return self.interface.threadTask(func)                                  # Return and thread the function
    
    def threadedFunction(self,V,wait):
        """
        This function changes the bias in Nanonis and then waits a specified
        amount of time.
        
        This function is run on a new thread. It will run in the backgound 
        while Scanbot can still reveive commands. It should periodically check
        event flags by calling 'self.interface.scanbot.checkEventFlags()'. If
        True is returned, the 'stop' function has been called by the user.
        Whenever returning, the global running flag should be cleared by 
        calling global_.running.clear().

        Parameters
        ----------
        V    : Change the bias to this value
        wait : Wait this many seconds after changing the bias

        """
        if(V == 0):                                                             # Validation
            errorMessage = "Cannot set bias to zero!"
            global_.running.clear()                                             # Free up the running flag. This must be done whenever exiting a threaded function
            return errorMessage                                                 # Return with error
        
        NTCP,connection_error = self.interface.scanbot.connect()                # Connect to nanonis via TCP
        if(connection_error):
            global_.running.clear()                                             # Free up the running flag. This must be done whenever exiting a threaded function
            return connection_error                                             # Return error message if there was a problem connecting        
        
        biasModule = Bias(NTCP)                                                 # The NanonisTCP Bias module
        biasModule.Set(V)                                                       # Set the bias in Nanonis
        
        self.interface.sendReply("Bias set to " + str(V))                       # This is how you send a reply.
        
        self.interface.sendReply("Waiting " + str(wait) + " seconds...")        # This is how you send a reply.
        
        seconds = 0
        while(seconds < wait):
            time.sleep(1)
            seconds += 1                                                        # Keep track of how many seconds have gone by
            if(self.interface.scanbot.checkEventFlags() == True):               # Periodically check event flags when appropriate to see if the user has called "stop"
                self.interface.sendReply("Stopping early!")                     # This is how you send a reply.
                break
        
        self.interface.sendReply("Done!")                                       # This is how you send a reply.
        
        self.interface.scanbot.disconnect(NTCP)                                 # Remember to free up the TCP port
        global_.running.clear()                                                 # Free up the running flag. This must be done whenever exiting a threaded function
        
        return
```
