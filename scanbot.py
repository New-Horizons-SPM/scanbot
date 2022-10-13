# -*- coding: utf-8 -*-
"""
Created on Fri August 8 22:06:52 2022

@author: Julian Ceddia
"""

from nanonisTCP import nanonisTCP
from nanonisTCP.Scan import Scan
from nanonisTCP.Signals import Signals
from nanonisTCP.Piezo import Piezo
from nanonisTCP.Bias import Bias
from nanonisTCP.ZController import ZController
from nanonisTCP.Motor import Motor
from nanonisTCP.AutoApproach import AutoApproach
from nanonisTCP.Current import Current

import time
import ntpath
import numpy as np
import nanonispyfit as napfit
import matplotlib.pyplot as plt

import global_

import utilities

class scanbot():
    channel = 14
###############################################################################
# Constructor
###############################################################################
    def __init__(self,interface):
        self.interface = interface
        self.safetyParams = [5e-9,2100,270]                                     # [0]: safe current threshold. [1]: safe retract motor frequency. [2]: safe retract motor voltage

###############################################################################
# Actions
###############################################################################
    def stop(self):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
        
        scan = Scan(NTCP)                                                       # Nanonis scan module
        scan.Action('stop')                                                     # Stop the current scan
        
        self.disconnect(NTCP)                                                   # Close the NTCP connection
        
    def plot(self,channel=-1):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
        
        scan = Scan(NTCP)                                                       # Nanonis scan module
        if(channel < 0): channel = self.channel                                 # Plot the default channel if -c param not passed in
        
        _,channels,_,_ = scan.BufferGet()
        if(channel not in channels):
            self.interface.reactToMessage("cross_mark")
            self.interface.sendReply("Available channels:\n" + "\n".join(str(c) for c in channels))
            return
        
        _,scanData,_ = scan.FrameDataGrab(channel, 1)                           # Grab the data within the scan frame. Channel 14 is . 1 is forward data direction
        
        try:
            pngFilename = 'im-c' + str(channel) + '.png'                        # All unsaved (incomplete) scans are saved as im.png
            pngFilename = self.makePNG(scanData,pngFilename=pngFilename)        # Generate a png from the scan data
            self.interface.sendPNG(pngFilename,notify=False)                    # Send a png over zulip
        except:
            self.interface.reactToMessage("cross_mark")
        
        self.disconnect(NTCP)                                                   # Close the TCP connection
    
    def survey(self,bias,n,startAt,suffix,xy,dx,px,sleepTime,stitch,macro,ox=0,oy=0,message="",enhance=False):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting   
        
        scan  = Scan(NTCP)
        piezo = Piezo(NTCP)
        range_x,range_y,_ = piezo.RangeGet()
        
        x = np.linspace(-1, 1,n) * (n-1)*dx/2
        y = x
        
        frames = []
        for j in y:
            for i in x:
                frames.append([i+ox, j+oy, xy, xy])
                if(i+ox>range_x/2 or j+oy>range_y/2):
                    self.interface.sendReply("Survey error: Grid size exceeds scan area",message=message)
                    self.disconnect(NTCP)                                       # Close the TCP connection
                    global_.running.clear()                                     # Free up the running flag
                    return
            x = np.array(list(reversed(x)))                                     # Snake the grid - better for drift
            
        if(bias != "-default"): self.rampBias(NTCP, bias)                       # Change the scan bias if the user wants to
        
        basename = self.interface.topoBasename                                  # Get the basename that's been set in config file
        if(not basename): basename = scan.PropsGet()[3]                         # Get the save basename from nanonis if one isn't supplied
        tempBasename = basename + '_' + suffix + '_'                            # Create a temp basename for this survey
        scan.PropsSet(series_name=tempBasename)                                 # Set the basename in nanonis for this survey
        
        if(px != "-default"):
            px = int(np.ceil(px/16)*16)                                         # Pixels must be divisible by 16
            scan.BufferSet(pixels=px,lines=px)
        
        stitchedSurvey = []
        if(stitch == 1):
            _,_,px,lines = scan.BufferGet()
            stitchedSurvey = np.zeros((lines*n,px*n))*np.nan
        
        for idx,frame in enumerate(frames):
            if(idx < startAt-1): continue
            
            self.interface.sendReply('Running scan ' + str(idx + 1) + '/' + str(n**2),message=message) # Send a message that the next scan is starting
            
            slept = 0
            scan.FrameSet(*frame)                                               # Set the coordinates and size of the frame window in nanonis
            scan.Action('start')                                                # Start the scan. default direction is "up"
            while(slept < sleepTime):                                           # This loop makes running 'stop' more responsive
                time.sleep(0.2)                                                 # Wait for drift to settle
                slept += 0.2
                if(self.checkEventFlags()): break                               # Check event flags
            if(self.checkEventFlags()): break                                   # Check event flags
            
            timeoutStatus = 1
            scan.Action('start')                                                # Start the scan. default direction is "up"
            while(timeoutStatus):
                timeoutStatus, _, filePath = scan.WaitEndOfScan(timeout=200)    # Wait until the scan finishes
                if(self.checkEventFlags()): break                               # Check event flags
            if(self.checkEventFlags()): break                                   # Check event flags
                
            if(not filePath): time.sleep(0.2); continue                         # If user stops the scan, filePath will be blank, then go to the next scan
            
            _,scanData,_ = scan.FrameDataGrab(14, 1)                            # Grab the data within the scan frame. Channel 14 is . 1 is forward data direction
            pngFilename,scanDataPlaneFit = self.makePNG(scanData, filePath,returnData=True,dpi=150) # Generate a png from the scan data
            self.interface.sendPNG(pngFilename,notify=True,message=message)     # Send a png over zulip
            
            if(macro != 'OFF'): pass                                            # Implement macro here
            
            if(stitch):
                row = (idx)//n
                col = ((row)%2)*((n-1) - idx%n) + ((row+1)%2)*idx%n
                stitchedSurvey[(n-1-row)*lines:(n-1-row)*lines+lines,px*col:px*col+px] = scanData
            
            if(self.interface.sendToCloud == 1):
                metaData = self.getMetaData(filePath)
                pklFile = utilities.pklDict(scanData,filePath,*metaData,comments="scanbot")
                self.interface.uploadToCloud(pklFile)                           # Send data to cloud database
        
        if(stitch == 1 and not np.isnan(stitchedSurvey).all()):
            stitchFilepath = self.makePNG(stitchedSurvey,pngFilename = suffix + '.png',dpi=150*n, fit=False)
            self.interface.sendPNG(stitchFilepath,notify=False,message=message)     # Send a png over zulip
        
        scan.PropsSet(series_name=basename)                                     # Put back the original basename
        self.disconnect(NTCP)                                                   # Close the TCP connection
        global_.running.clear()                                                 # Free up the running flag
        
        self.interface.sendReply('survey \'' + suffix + '\' done',message=message) # Send a notification that the survey has completed
        
    def moveArea(self,up,upV,upF,direction,steps,dirV,dirF,zon):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
        
        # Safety checks
        if(up < 10):
            self.disconnect(NTCP)
            self.interface.sendReply("-up must be > 10")
            return
        
        if(upV > 300):
            self.disconnect(NTCP)
            self.interface.sendReply("-upV 300 V max")
            return
        
        if(upF > 2.5e3):
            self.disconnect(NTCP)
            self.interface.sendReply("-upF 2.5 kHz max")
            return
        
        if(dirV > 200):
            self.disconnect(NTCP)
            self.interface.sendReply("-dirV 200 V max")
            return
        
        if(dirF > 2.5e3):
            self.disconnect(NTCP)
            self.interface.sendReply("-dirF 2.5 kHz max")
            return
        
        if(upV < 1):
            self.disconnect(NTCP)                                               # Close the TCP connection
            self.interface.sendReply("-upV must be between 1 V and 200 V")
            return
            
        if(upF < 500):
            self.disconnect(NTCP)                                               # Close the TCP connection
            self.interface.sendReply("-upF must be between 500 Hz and 2.5 kHz")
            return
        
        if(dirV < 1):
            self.disconnect(NTCP)                                               # Close the TCP connection
            self.interface.sendReply("-upV must be between 1 V and 200 V")
            return
            
        if(dirF < 500):
            self.disconnect(NTCP)                                               # Close the TCP connection
            self.interface.sendReply("-upF must be between 500 Hz and 2.5 kHz")
            return
        
        if(not direction in ["X+","X-","Y+","Y-"]):
            self.disconnect(NTCP)                                               # Close the TCP connection
            self.interface.sendReply("-dir can only be X+, X-, Y+, Y-")
            return
        
        if(steps < 0):
            self.disconnect(NTCP)
            self.interface.sendReply("-steps must be > 0")
            return
        
        if(up < 0):
            self.disconnect(NTCP)
            self.interface.sendReply("-up must be > 0")
            return
        
        motor         = Motor(NTCP)                                             # Nanonis Motor module
        zController   = ZController(NTCP)                                       # Nanonis ZController module
        autoApproach  = AutoApproach(NTCP)                                      # Nanonis AutoApproach module
        
        self.interface.reactToMessage("working_on_it")
        
        self.stop()
        
        print("withdrawing")
        zController.Withdraw(wait_until_finished=True,timeout=3)                # Withdwar the tip
        print("withdrew")
        time.sleep(0.25)
        
        motor.FreqAmpSet(upF,upV)                                               # Set the motor controller params appropriate for Z piezos
        motor.StartMove("Z+",up,wait_until_finished=True)                       # Retract the tip +Z direction
        print("Moving motor: Z+" + " " + str(up) + "steps")
        time.sleep(0.5)
        
        stepsAtATime = 10                                                       # Moving the motor across 10 steps at a time to be safe
        leftOver     = steps%stepsAtATime                                       # Continue moving motor a few steps if stes is not divisible by 10
        steps        = int(steps/stepsAtATime)                                  # Sets of 10 steps
        
        isSafe = True
        motor.FreqAmpSet(dirF,dirV)                                             # Set the motor controller params appropriate for XY piezos
        for s in range(steps):
            motor.StartMove(direction,stepsAtATime,wait_until_finished=True)    # Move safe number of steps at a time
            print("Moving motor: " + direction + " " + str(stepsAtATime) + "steps")
            isSafe = self.safeCurrentCheck(NTCP)                                # Safe retract if current overload
            if(not isSafe):
                self.disconnect(NTCP)                                           # Close the TCP connection
                self.interface.sendReply("Could not complete move_area...")
                self.interface.sendReply("Safe retract was triggered because the current exceeded "
                                         + str(self.safetyParams[0]*1e9) + " nA"
                                         + " while moving areas")
                return
                
            time.sleep(0.25)
        
        motor.StartMove(direction,leftOver,wait_until_finished=True)
        print("Moving motor: " + direction + " " + str(leftOver) + "steps")
        time.sleep(0.5)
        
        isSafe = self.safeCurrentCheck(NTCP)                                    # Safe retract if current overload
        if(not isSafe):
            self.disconnect(NTCP)                                               # Close the TCP connection
            self.interface.sendReply("Could not complete move_area...")
            self.interface.sendReply("Safe retract was triggered because the current exceeded "
                                     + str(self.safetyParams[0]*1e9) + " nA"
                                     + " while moving areas")
            return
        
        self.interface.reactToMessage("double_down")
        motor.FreqAmpSet(upF,upV)
        autoApproach.Open()
        autoApproach.OnOffSet(on_off=True)
        
        while(autoApproach.OnOffGet()):
            print("Still approaching...")
            time.sleep(1)
        
        time.sleep(1)
        if(zon): zController.OnOffSet(True)
        
        time.sleep(3)
        self.interface.reactToMessage("sparkler")
        
        self.disconnect(NTCP)                                                   # Close the TCP connection
        
###############################################################################
# Config
###############################################################################
    def plotChannel(self,c=-1,a=-1,r=-1):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
        
        scan = Scan(NTCP)
        signals = Signals(NTCP)
        
        signal_names,signal_indexes = signals.InSlotsGet()
        num_channels,channels,pixels,lines = scan.BufferGet()
        
        helpStr  = "**Selected channel:**\n" + signal_names[self.channel] + "\n\n"
        
        helpStr += "**Channels in scan buffer:**\n"
        helpStr += "Buffer idx | Signal idx | Signal name\n"
        for idx,name in enumerate(signal_names):
            if(idx in channels):
                helpStr += str(idx).ljust(11) + '| ' + str(signal_indexes[idx]).ljust(11) + ": " + name + "\n"
        
        helpStr += "\n**Available channels:**\n"
        helpStr += "Buffer idx | Signal idx | Signal name\n"
        for idx,name in enumerate(signal_names):
            helpStr += str(idx).ljust(11) + '| ' + str(signal_indexes[idx]).ljust(11) + "| " + name + "\n"
            
        helpStr = "```\n" + helpStr + "\n```"
        
        if(c == -1 and a == -1 and r == -1): self.disconnect(NTCP); return helpStr
        
        # Validations first
        errmsg = ''
        if(c != -1 and not c in channels):  errmsg += "Invalid signal -c=" + str(c) + " is not in the buffer\n"
        if(a != -1 and not a in range(24)): errmsg += "Invalid signal -a=" + str(a) + "\n"
        if(a != -1 and a in channels):      errmsg += "-a=" + str(a) + " is already in the buffer\n"
        if(r != -1 and not r in channels):  errmsg += "-r=" + str(r) + " is not in the buffer\n"
        if(r == self.channel):              errmsg += "-r=" + str(r) + " cannot be removed while selected\n"
        
        if(errmsg):
            self.disconnect(NTCP)
            errmsg += helpStr
            return errmsg
        
        # Then process
        setBuf = False
        if(c != -1): self.channel = c
        if(a != -1): channels.append(a); setBuf = True
        if(r != -1): channels.remove(r); setBuf = True
        
        if(setBuf): scan.BufferSet(channel_indexes=channels)
        
        self.disconnect(NTCP); 
        
        self.interface.reactToMessage("+1")
    
###############################################################################
# Utilities
###############################################################################
    def rampBias(self,NTCP,bias,dbdt=1,db=50e-3,zhold=True):                    # Ramp the tip bias from current value to final value at a rate of db/dt
        if(bias == 0): return
        biasModule = Bias(NTCP)                                                 # Nanonis Bias module
        zController = ZController(NTCP)                                         # Nanonis ZController module
        
        sleepTime   = db/dbdt                                                   # Sleep interval for changing bias by step size
        currentBias = biasModule.Get()                                          # Grab the current tip bias from nanonis
        
        if(zhold): zController.OnOffSet(False)                                  # Turn off the z-controller if we need to
        
        if(bias < currentBias): db = -db                                        # flip the sign of db if we're going down in bias
        for b in np.arange(currentBias,bias,db):                                # Change the bias according to step size
            if(b and abs(b) <= 10): biasModule.Set(b)                           # Set the tip bias in nanonis. skip b == 0
            time.sleep(sleepTime)                                               # sleep a bit
        
        biasModule.Set(bias)                                                    # Set the final bias in case the step size doesn't get us there nicely
        
        if(zhold): zController.OnOffSet(True)                                   # Turn the controller back on if we need to
        
    def makePNG(self,scanData,filePath='',pngFilename='im.png',returnData=False,fit=True,dpi=150):
        fig, ax = plt.subplots(1,1)
        
        mask = np.isnan(scanData)                                               # Mask the Nan's
        scanData[mask == True] = np.nanmean(scanData)                           # Replace the Nan's with the mean so it doesn't affect the plane fit
        scanData -= np.nanmean(scanData)
        if(fit): scanData = napfit.plane_fit_2d(scanData)                       # Flatten the image
        vmin, vmax = napfit.filter_sigma(scanData)                              # cmap saturation
        
        ax.imshow(scanData, cmap='Blues_r', vmin=vmin, vmax=vmax)               # Plot
        ax.axis('off')
        
        if filePath: pngFilename = ntpath.split(filePath)[1] + '.png'
        
        fig.savefig(pngFilename, dpi=dpi, bbox_inches='tight', pad_inches=0)
        plt.close('all')
        
        if(returnData): return pngFilename,scanData
        return pngFilename
    
    def getMetaData(self,filePath):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return "getMetaData: " + connection_error
        
        scan = Scan(NTCP)
        x,y,w,h,angle    = scan.FrameGet()
        _,_,pixels,lines = scan.BufferGet()
        
        self.disconnect(NTCP); 
        
        return [x,y,w,h,angle,pixels,lines]
        
    def checkEventFlags(self,message = ""):
        if(not global_.running.is_set()):
            self.interface.reactToMessage("stop_button")
            return 1                                                            # Running flag
        
        if(global_.pause.is_set()):
            NTCP,connection_error = self.connect()                              # Connect to nanonis via TCP
            if(connection_error):
                self.interface.sendReply(connection_error)                      # Return error message if there was a problem connecting
                return 1
            scan = Scan(NTCP)
            scan.Action(scan_action='pause')
            
            self.interface.reactToMessage("pause")
            
            while global_.pause.is_set():
                time.sleep(2)                                                   # Sleep for a bit
                if(not global_.running.is_set()):
                    self.interface.reactToMessage("stop_button")
                    self.disconnect(NTCP)
                    return 1
                
            self.interface.reactToMessage("play")
            scan.Action(scan_action='resume')
            self.disconnect(NTCP)
            
    def safeCurrentCheck(self,NTCP):
        motor         = Motor(NTCP)                                             # Nanonis Motor module
        zController   = ZController(NTCP)                                       # Nanonis Z-Controller module
        currentModule = Current(NTCP)                                           # Nanonis Current module
        
        current = abs(currentModule.Get())                                      # Get the tip current
        threshold = self.safetyParams[0]                                        # Threshold current from safety params
        
        print("Safe check... Current: " + str(current)
            + ", threshold: " + str(threshold))
        
        if(current < threshold):
            return True                                                         # All good if the current is below the threshold
        
        self.interface.sendReply("---\nWarning: Safe retract has been triggered.\n"
                                 + "Current: " + str(current*1e9) + " nA\n"
                                 + "Threshold: " + str(threshold*1e9) + " nA\n")
        
        zController.Withdraw(wait_until_finished=False)                         # Retract the tip
        
        try:                                                                    # Stop anything running. try/except is probably overkill but just in case
            print("Stopping other processes...")
            self.interface.stop(args=[])
        except Exception as e:
            self.interface.sendReply("---\nWarning: error stopping processes during safe retract...")
            self.interface.sendReply(str(e) + "\n---")
        
        safeFreq    = self.safetyParams[1]                                      # Motor frequency for safe retract from safety parameters
        safeVoltage = self.safetyParams[2]                                      # Motor voltage for safe retract from safety parameters
        motor.FreqAmpSet(safeFreq,safeVoltage)                                  # Set the motor frequency/voltage in the nanonis motor control module
        motor.StartMove(direction="Z+", steps=50,wait_until_finished=True)      # Move up 50 steps immediately
        print("Retracted and moved 50 motor steps up")
        
        count = 0                                                               # Keep track of how many steps we've gone up
        while(current > threshold):                                             # Kepp moving 50 steps in Z+ until the current is < threshold
            if(count%5 == 0):                                                   # Send a warning over the interface every 250 motor steps
                self.interface.sendReply("---\n"
                                     + "Warning: Safe retract has been triggered.\n"
                                     + "Current still above threshold after "
                                     + str((count+1)*50) + " Z+ motor steps.\n" 
                                     + "Current: " + str(current*1e9) + " nA\n"
                                     + "Threshold: " + str(threshold*1e9) + " nA\n")
                
            motor.StartMove(direction="Z+", steps=50,wait_until_finished=True)  # Move another 50 steps up
            current = abs(currentModule.Get())                                  # Get the tip current after moving
            count += 1
            print("Retracting another 50 steps... current: " + str(current*1e9) + " nA")
        
        self.interface.sendReply("Warning: Safe retract complete... current: " + str(current*1e9) + " nA\n---\n")
        return False
    
###############################################################################
# Nanonis TCP Connection
###############################################################################
    def connect(self,creepIP=None,creepPORT=None):
        IP   = creepIP
        PORT = creepPORT
        try:                                                                    # Try to connect to nanonis via TCP
            if(not IP):   IP   = self.interface.IP
            if(not PORT): PORT = self.interface.portList.pop()
            NTCP = nanonisTCP(IP, PORT)
            return [NTCP,0]
        except Exception as e:
            if(len(self.interface.portList)): return [0,str(e)]                 # If there are ports available then return the exception message
            return [0,"No ports available"]                                     # If no ports are available send this message
    
    def disconnect(self,NTCP):
        NTCP.close_connection()                                                 # Close the TCP connection
        self.interface.portList.append(NTCP.PORT)                               # Free up the port - put it back in the list of available ports
        time.sleep(0.2)                                                         # Give nanonis a bit of time to close the connection before attempting to reconnect using the same port (from experience)