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

import time
import ntpath
import numpy as np
import nanonispyfit as nap
import matplotlib.pyplot as plt

import global_

import pickle

class scanbot():
    channel = 14
###############################################################################
# Constructor
###############################################################################
    def __init__(self,interface):
        self.interface = interface

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
    
    def survey(self,bias,n,startAt,suffix,xy,dx,px,sleepTime,ox=0,oy=0,message="",enhance=False):
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
            pngFilename = self.makePNG(scanData, filePath)                      # Generate a png from the scan data
            self.interface.sendPNG(pngFilename,notify=True,message=message)     # Send a png over zulip
            
            if(self.interface.sendToCloud):
                self.interface.uploadToCloud(self.pklData(scanData, filePath))  # Send data to cloud database
        
        scan.PropsSet(series_name=basename)                                     # Put back the original basename
        self.disconnect(NTCP)                                                   # Close the TCP connection
        global_.running.clear()                                                 # Free up the running flag
        
        self.interface.sendReply('survey \'' + suffix + '\' done',message=message) # Send a notification that the survey has completed
    
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
        
    def makePNG(self,scanData,filePath='',pngFilename='im.png'):
        fig, ax = plt.subplots(1,1)
        
        mask = np.isnan(scanData)                                               # Mask the Nan's
        scanData[mask == True] = np.nanmean(scanData)                           # Replace the Nan's with the mean so it doesn't affect the plane fit
        scanData = nap.plane_fit_2d(scanData)                                   # Flattern the image
        vmin, vmax = nap.filter_sigma(scanData)                                 # cmap saturation
        
        ax.imshow(scanData, cmap='Blues_r', vmin=vmin, vmax=vmax)               # Plot
        ax.axis('off')
        
        if filePath: pngFilename = ntpath.split(filePath)[1] + '.png'
        
        fig.savefig(pngFilename, dpi=60, bbox_inches='tight', pad_inches=0)
        plt.close('all')
        
        return pngFilename
    
    def pklData(self,scanData,filePath,comments=""):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return "scanbot/pkldata: " + connection_error
        
        scan = Scan(NTCP)
        x,y,w,h,angle    = scan.FrameGet()
        _,_,pixels,lines = scan.BufferGet()
        
        filename = ntpath.split(filePath)[1]
        pklDict = { "sxm"       : filename,
                    "data"      : scanData,
                    "comments"  : comments,
                    "pixels"    : pixels,
                    "lines"     : lines,
                    "x"         : x,
                    "y"         : y,
                    "w"         : w,
                    "h"         : h,
                    "angle"     : angle}
        
        pickle.dump(pklDict, open(filename + ".pkl", 'wb'))                     # Pickle containing config settings and unlabelled data
        
        self.disconnect(NTCP); 
        
        return filename + ".pkl"
        
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