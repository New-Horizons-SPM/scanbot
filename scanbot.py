# -*- coding: utf-8 -*-
"""
Created on Fri May  6 15:38:34 2022

@author: jack hellerstedt and julian ceddia
"""

from nanonisTCP import nanonisTCP
from nanonisTCP.Scan import Scan
from nanonisTCP.TipShaper import TipShaper
from nanonisTCP.Bias import Bias
from nanonisTCP.ZController import ZController
from nanonisTCP.FolMe import FolMe

import nanonisUtils as nut

import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import nanonispyfit as nap

import time
import ntpath                                                                   # os.path but for windows paths

import global_

class scanbot():
###############################################################################
# Constructor
###############################################################################
    def __init__(self,interface):
        self.interface = interface
        self.survey_args = []
        self.designatedTipShapeArea = [-600e-9,-600e-9,300e-9,300e-9]
        self.designatedGrid = [10,0]
        self.defaultPulseParams = [5,0.1,3,0,0]                                 # np,pw,bias,zhold,rel_abs. Defaults here because nanonis has no TCP comand to retrieve them :(
        
###############################################################################
# Actions
###############################################################################
    def plot(self,args):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
        
        scan = Scan(NTCP)                                                       # Nanonis scan module
        _,scanData,_ = scan.FrameDataGrab(14, 1)                                # Grab the data within the scan frame. Channel 14 is . 1 is forward data direction
        
        pngFilename = self.makePNG(scanData)                                    # Generate a png from the scan data
        self.interface.sendPNG(pngFilename,notify=False)                        # Send a png over zulip
        
        self.disconnect(NTCP)                                                   # Close the TCP connection
        return ""
    
    def stop(self,args):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
        
        scan = Scan(NTCP)                                                       # Nanonis scan module
        scan.Action('stop')                                                     # Stop the current scan
        
        self.disconnect(NTCP)                                                   # Close the NTCP connection
        return ("Stopped!")
    
    def watch(self,suffix,creepIP=None,creepPORT=None):
        NTCP,connection_error = self.connect(creepIP,creepPORT)                 # Connect to nanonis via TCP
        if(connection_error):
            self.interface.sendReply(connection_error)
            return                                                              # Return error message if there was a problem connecting        
        
        scan = Scan(NTCP)                                                       # Nanonis scan module
        
        basename     = scan.PropsGet()[3]                                       # Get the save basename
        if(suffix):
            tempBasename = basename + '_' + suffix + '_'                        # Create a temp basename for this survey
            scan.PropsSet(series_name=tempBasename)                             # Set the basename in nanonis for this survey
        
        self.interface.sendReply('Scanbot :eyes: \'' + suffix + '\'')           # Send a notification that the survey has completed
        
        while(True):
            if(self.checkEventFlags()): break                                   # Check event flags
            timeoutStatus, _, filePath = scan.WaitEndOfScan(200)                # Wait until the scan finishes
            
            if(not filePath): continue
            
            _,scanData,_ = scan.FrameDataGrab(14, 1)                            # Grab the data within the scan frame. Channel 14 is . 1 is forward data direction
            pngFilename = self.makePNG(scanData, filePath)                      # Generate a png from the scan data
            self.interface.sendPNG(pngFilename)                                 # Send a png over zulip
            
        if(suffix):
            scan.PropsSet(series_name=basename)                                 # Put back the original basename
        
        self.disconnect(NTCP)                                                   # Close the TCP connection
        
        global_.running.clear()                                                 # Free up the running flag
        
        self.interface.sendReply('Stopped watching \'' + suffix + '\'')         # Send a notification that the survey has completed
        
    def survey(self,bias,n,i,suffix,xy,dx,sleepTime,ox=0,oy=0):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
        
        self.survey_args = [bias,n,i,suffix,xy,dx,sleepTime,ox,oy]              # Store these params for enhance to look at
        
        scan = Scan(NTCP)                                                       # Nanonis scan module
        
        if(bias != "-default"): self.rampBias(NTCP, bias)                       # Change the scan bias if the user wants to
        
        basename     = scan.PropsGet()[3]                                       # Get the save basename
        tempBasename = basename + '_' + suffix + '_'                            # Create a temp basename for this survey
        scan.PropsSet(series_name=tempBasename)                                 # Set the basename in nanonis for this survey
        
        count = 0
        frames = []                                                             # [x,y,w,h,angle=0]
        for ii in range(int(-n/2),int(n/2) + n%2):
            jj_range = range(int(-n/2),int(n/2) + n%2)
            if(ii%2): jj_range = reversed(jj_range)                             # Alternate grid direction each row so the grid snakes... better for drift
            for jj in jj_range:
                count += 1
                if(count < i): continue                                         # Skip this frame if it's before the frame index we want to start from
                frames.append([ jj*dx+ox, ii*dx+oy, xy, xy])                    # Build scan frame
        
        count = i-1
        for frame in frames:
            count += 1
            self.currentSurveyIndex = count
            self.interface.sendReply('Running scan ' + str(count) + ': ' + str(frame)) # Send a message that the next scan is starting
            
            scan.FrameSet(*frame)                                               # Set the coordinates and size of the frame window in nanonis
            scan.Action('start')                                                # Start the scan. default direction is "up"
            
            time.sleep(sleepTime)                                               # Wait for drift to settle
            if(self.checkEventFlags()): break
        
            scan.Action('start')                                                # Start the scan again after waiting for drift to settle
            
            timeoutStatus = 1
            while(timeoutStatus):
                timeoutStatus, _, filePath = scan.WaitEndOfScan(timeout=200)    # Wait until the scan finishes
                if(self.checkEventFlags()): break
            
            _,scanData,_ = scan.FrameDataGrab(14, 1)                            # Grab the data within the scan frame. Channel 14 is . 1 is forward data direction
            
            pngFilename = self.makePNG(scanData, filePath)                      # Generate a png from the scan data
            
            notify = True
            if(not filePath): notify= False                                     # Don't @ users if the image isn't complete
            self.interface.sendPNG(pngFilename,notify)                          # Send a png over zulip
            
            if(self.checkEventFlags()): break                                   # Check event flags
        
        scan.PropsSet(series_name=basename)                                     # Put back the original basename
        self.disconnect(NTCP)                                                   # Close the TCP connection
        
        global_.running.clear()                                                 # Free up the running flag
        
        self.interface.sendReply('survey \'' + suffix + '\' done')              # Send a notification that the survey has completed
    
    def enhance(self,bias,n,i,suffix,sleepTime):
        if(self.survey_args == []):
            self.interface.sendReply("Need to run a survey first")
            global_.running.clear()                                             # Free up the running flag
            return
        
        ns    = self.survey_args[1]                                             # Grid size of original survey
        count = 0                                                               # Lazy way to get ii and jj
        for ii in range(int(-ns/2),int(ns/2) + ns%2):
            jj_range = range(int(-ns/2),int(ns/2) + ns%2)
            if(ii%2): jj_range = reversed(jj_range)                             # Alternate grid direction each row so the grid snakes... better for drift
            for jj in jj_range:
                count += 1
                if(count == i): break
            if(count == i): break
        
        dx = self.survey_args[5]                                                # Frame spacing in the original survey grid
        ox = self.survey_args[7]                                                # Origin of the original survey grid
        oy = self.survey_args[8]                                                # Origin of the original survey grid
        
        ox,oy =  jj*dx+ox, ii*dx+oy                                             # New origin for the enhance grid is the centre of the frame to enhance
        
        xy = self.survey_args[4]/n                                              # if xy is set to 0, divide the enhance grid fills the frame exactly
        dx = xy                                                                 # spacing = frame size by default
        
        ox += (dx/2)*((n+1)%2)                                                  # Offset for even grids to keep centre
        oy += (dx/2)*((n+1)%2)                                                  # Offset for even grids to keep centre
        
        if(sleepTime == "-default"): sleepTime = self.survey_args[6]            # Keep the sleepTime the same as the survey
        
        survey_args = [bias,n,1,suffix,xy,dx,sleepTime,ox,oy]
        self.survey(*survey_args)                                               # Kick off a survey within the frame we want to enhance
    
    def moveTip(self,pos):
        x = pos[0]
        y = pos[1]
        if(abs(x) > 800e-9): self.interface.sendReply("Can't move tip outside scan window"); return
        if(abs(y) > 800e-9): self.interface.sendReply("Can't move tip outside scan window"); return
        
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): self.interface.sendReply(connection_error); return # Return error message if there was a problem connecting
        
        folMe = FolMe(NTCP)
        folMe.XYPosSet(x,y,Wait_end_of_move=True)
        
        self.disconnect(NTCP)
        # self.interface.sendReply("Tip-moved to " + str(x) + "," + str(y))
        
    def tipShape(self,np,pw,bias,zhold,rel_abs):
        global_.pause.set()
        time.sleep(0.5)
        
        gridCentre = self.designatedTipShapeArea[0:2]
        gridSize   = self.designatedTipShapeArea[2:4]
        gridN      = self.designatedGrid[0]
        gridI      = self.designatedGrid[1]
        
        dx    = gridSize[0]/gridN
        xpos  = gridCentre[0] - gridSize[0]/2
        xpos += (gridI%gridN + 0.5)*dx
        
        dy    = gridSize[1]/gridN
        ypos  = gridCentre[1] - gridSize[1]/2
        ypos += (int(gridI/gridN) + 0.5)*dy
        
        self.moveTip(pos=[xpos,ypos])
        self.designatedGrid[1] += 1
        
        self.executeTipShape()
        
        time.sleep(0.5)
        
        self.pulse()
        
        time.sleep(0.5)
        
        global_.pause.clear()
        
    def executeTipShape(self):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting
        
        tipShaper = TipShaper(NTCP)
        tipShaper.Start(wait_until_finished=True,timeout=-1)
        
        self.disconnect(NTCP)
        # self.interface.sendReply("Tip-shape complete")
        
    def tipShapeProps(self,sod,cb,b1,z1,t1,b2,t2,z3,t3,wait,fb,designatedArea,designatedGrid):#,np,pw,bias,zhold,rel_abs):
        if(z1 > 50e-9):
            self.interface.sendReply("Limit for z1=50e-9 m")
            return
        
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting
         
        tipShaper  = TipShaper(NTCP)
        
        default_args  = tipShaper.PropsGet()                                    # Store all the current tip shaping settings in nanonis
        tipShaperArgs = [sod,cb,b1,z1,t1,b2,t2,z3,t3,wait,fb]                   # Order matters here
        for i,a in enumerate(tipShaperArgs):
            if(a=="-default"):
                tipShaperArgs[i] = default_args[i]
                
        tipShaper.PropsSet(*tipShaperArgs)                                      # update the tip shaping params in nanonis
        
        self.designatedTipShapeArea = designatedArea
        self.designatedGrid[0] = designatedGrid
        
        self.disconnect(NTCP)
        self.interface.sendReply("Tip-shaper props set")
    
    def pulseProps(self,np,pw,bias,zhold,rel_abs):
        self.defaultPulseParams = [np,pw,bias,zhold,rel_abs]
        
    def pulse(self):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
        
        biasModule = Bias(NTCP)
        
        np,pw,bias,zhold,rel_abs = self.defaultPulseParams                      # Grab the stored pulse params
        for n in range(0,np):                                                   # Pulse the tip -np times
            biasModule.Pulse(pw,bias,zhold,rel_abs,wait_until_done=False)
            time.sleep(pw + 0.2)                                                # Wait 200 ms more than the pulse time
        
        self.disconnect(NTCP)
        
        # self.interface.sendReply("Bias pulse complete")
    
    def biasDep(self,nb,bdc,bi,bf,px,suffix):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting
        
        biasList = np.linspace(bi,bf,nb)
        
        scan = Scan(NTCP)
        
        scanPixels,scanLines = scan.BufferGet()[2:]
        lx = int((scanLines/scanPixels)*px)
        
        x,y,w,h,angle = scan.FrameGet()
        
        ## Initial drift correct frame
        dxy = []
        initialDriftCorrect = "skip"
        if(px > 0):
            self.rampBias(NTCP, bdc)
            scan.BufferSet(pixels=px,lines=lx)
            scan.Action('start',scan_direction='up')
            scan.WaitEndOfScan()
            _,initialDriftCorrect,_ = scan.FrameDataGrab(14, 1)
            
            dx  = w/px; dy  = h/lx
            dxy = np.array([dx,dy])
        
        if(self.checkEventFlags()): biasList=[]                                 # Check event flags
        
        for b in biasList:
            if(b == 0): continue                                                # Don't set the bias to zero ever
            ## Bias dep scan
            self.rampBias(NTCP, b)
            scan.BufferSet(pixels=scanPixels,lines=scanLines)
            scan.Action('start',scan_direction='down')
            _, _, filePath = scan.WaitEndOfScan()
            
            _,scanData,_ = scan.FrameDataGrab(14, 1)
            
            
            pngFilename = self.makePNG(scanData, filePath)                      # Generate a png from the scan data
            
            notify = True
            if(not filePath): notify= False                                     # Don't @ users if the image isn't complete
            self.interface.sendPNG(pngFilename,notify)                          # Send a png over zulip
            
            if(self.checkEventFlags()): break                                   # Check event flags
            
            if(initialDriftCorrect == "skip"): continue                         # If we haven't taken out initial dc image, dc must be turned off so continue
            
            ## Drift correct scan
            self.rampBias(NTCP, bdc)
            scan.BufferSet(pixels=px,lines=lx)
            scan.Action('start',scan_direction='up')
            timeoutStatus, _, filePath = scan.WaitEndOfScan()
            if(timeoutStatus): break
            _,driftCorrectFrame,_ = scan.FrameDataGrab(14, 1)
            
            if(self.checkEventFlags()): break                                   # Check event flags
            
            ox,oy = nut.getFrameOffset(initialDriftCorrect,driftCorrectFrame,dxy)
            x,y   = np.array([x,y]) - np.array([ox,oy])
            
            scan.FrameSet(x,y,w,h)
            
        self.disconnect(NTCP)
        
        global_.running.clear()
        
        self.interface.sendReply("Bias dependent imaging complete")
    
    def setBias(self,bias):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
        
        ## Need to put a check in here to see if bias is outside bias range
        ## Nanonis sim allows biases outside range?
        if(bias):
            self.rampBias(NTCP, bias)                                           # Only ramp the bias if it's not zero
            self.interface.sendReply("Bias set to " + str(bias) + "V")
        else:
            self.interface.sendReply("Can't set bias to zero")
            
        self.disconnect(NTCP)
        
        global_.running.clear()
        
        
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
        
    def makePNG(self,scanData,filePath=''):
        fig, ax = plt.subplots(1,1)
        
        mask = np.isnan(scanData)                                               # Mask the Nan's
        scanData[mask == True] = np.nanmean(scanData)                           # Replace the Nan's with the mean so it doesn't affect the plane fit
        scanData = nap.plane_fit_2d(scanData)                                   # Flattern the image
        vmin, vmax = nap.filter_sigma(scanData)                                 # cmap saturation
        
        ax.imshow(scanData, cmap='Blues_r', vmin=vmin, vmax=vmax) # Plot
        ax.axis('off')
        
        pngFilename = 'im.png'
        if filePath: pngFilename = ntpath.split(filePath)[1] + '.png'
        
        fig.savefig(pngFilename, dpi=60, bbox_inches='tight', pad_inches=0)
        plt.close('all')
        
        return pngFilename
        
    def checkEventFlags(self,message = ""):
        if(not global_.running.is_set()): return 1                              # Running flag
        
        if(global_.pause.is_set()):
            NTCP,connection_error = self.connect()                              # Connect to nanonis via TCP
            if(connection_error): return connection_error                       # Return error message if there was a problem connecting        
            scan = Scan(NTCP)
            scan.Action(scan_action='pause')
            
            while global_.pause.is_set(): time.sleep(2)                         # Pause flag
            
            scan.Action(scan_action='stop')
            
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