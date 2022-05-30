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
from nanonisTCP.Motor import Motor
from nanonisTCP.AutoApproach import AutoApproach
from nanonisTCP.Current import Current

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
        self.safetyParams = [5e-9,1100,180]                                     # [0]: safe current threshold. [1]: safe retract motor frequency. [2]: safe retract motor voltage
        self.designatedTipShapeArea = [-600e-9,-600e-9,300e-9,300e-9]
        self.designatedGrid = [10,0]
        self.defaultPulseParams = [5,0.1,3,0,0]                                 # np,pw,bias,zhold,rel_abs. Defaults here because nanonis has no TCP comand to retrieve them :(
        
###############################################################################
# Actions
###############################################################################
    def safetyPropsGet(self):
        getStr  = "Safe current threshold     (-maxcur): " + str(self.safetyParams[0]) + " A\n"
        getStr += "Safe retract motor freq    (-motorF): " + str(self.safetyParams[1]) + " Hz\n"
        getStr += "Safe retract motor voltage (-motorV): " + str(self.safetyParams[2]) + " V\n"
        return getStr
    
    def safetyPropsSet(self,threshold,motorF,motorV):
        threshold = abs(threshold)
        self.safetyParams = [threshold,motorF,motorV]
        return self.safetyPropsGet()
        
    def moveArea(self,up,upV,upF,direction,steps,dirV,dirF,zon):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
        
        # Safety checks
        if(up < 10):
            self.disconnect(NTCP)
            self.interface.sendReply("-up must be > 10")
            return
        
        if(upV > 200):
            self.disconnect(NTCP)
            self.interface.sendReply("-upV 200 V max")
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
        
    def plot(self,args):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
        
        scan = Scan(NTCP)                                                       # Nanonis scan module
        _,scanData,_ = scan.FrameDataGrab(14, 1)                                # Grab the data within the scan frame. Channel 14 is . 1 is forward data direction
        
        pngFilename = self.makePNG(scanData)                                    # Generate a png from the scan data
        self.interface.sendPNG(pngFilename,notify=False)                        # Send a png over zulip
        
        self.disconnect(NTCP)                                                   # Close the TCP connection
    
    def stop(self,args):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
        
        scan = Scan(NTCP)                                                       # Nanonis scan module
        scan.Action('stop')                                                     # Stop the current scan
        
        self.disconnect(NTCP)                                                   # Close the NTCP connection
        return ("Stopped!")
    
    def watch(self,suffix,creepIP=None,creepPORT=None,message=""):
        NTCP,connection_error = self.connect(creepIP,creepPORT)                 # Connect to nanonis via TCP
        if(connection_error):
            if(creepIP): global_.creepRunning.clear()
            if(not creepIP): global_.running.clear()                            # Free up the running flag
            self.interface.sendReply(connection_error,message=message)          # Return error message if there was a problem connecting
            return
        
        scan = Scan(NTCP)                                                       # Nanonis scan module
        
        basename     = scan.PropsGet()[3]                                       # Get the save basename
        if(suffix):
            tempBasename = basename + '_' + suffix + '_'                        # Create a temp basename for this survey
            scan.PropsSet(series_name=tempBasename)                             # Set the basename in nanonis for this survey
            
        self.interface.reactToMessage("eyes",message=message)
        
        while(True):
            if(self.checkEventFlags(creep=creepIP)): break                      # Check event flags
            timeoutStatus, _, filePath = scan.WaitEndOfScan(200)                # Wait until the scan finishes
            
            if(not filePath): continue
            
            _,scanData,_ = scan.FrameDataGrab(14, 1)                            # Grab the data within the scan frame. Channel 14 is . 1 is forward data direction
            pngFilename = self.makePNG(scanData, filePath)                      # Generate a png from the scan data
            self.interface.sendPNG(pngFilename,message=message)                 # Send a png over zulip
            
        if(suffix):
            scan.PropsSet(series_name=basename)                                 # Put back the original basename
        
        self.disconnect(NTCP)                                                   # Close the TCP connection
        
        if(creepIP): global_.creepRunning.clear()
        if(not creepIP): global_.running.clear()                                # Free up the running flag
        
        self.interface.reactToMessage("+1")
        
    def survey(self,bias,n,i,suffix,xy,dx,sleepTime,ox=0,oy=0,message="",enhance=False):
        count = 0
        frames = []                                                             # [x,y,w,h,angle=0]
        gridOK = True
        for ii in range(int(-n/2),int(n/2) + n%2):
            jj_range = range(int(-n/2),int(n/2) + n%2)
            if((ii+int(n/2))%2): jj_range = reversed(jj_range)                    # Alternate grid direction each row so the grid snakes... better for drift
            for jj in jj_range:
                count += 1
                if(count < i): continue                                         # Skip this frame if it's before the frame index we want to start from
                frames.append([ jj*dx+ox, ii*dx+oy, xy, xy])                    # Build scan frame
                
                if(abs(frames[-1][0]) + xy/2 > 800e-9): gridOK = False          # Safety checks
                if(abs(frames[-1][1]) + xy/2 > 800e-9): gridOK = False          # Safety checks
        
        if(not gridOK):
            self.interface.sendReply("Survey error: Grid size exceeds scan area",message=message)
            global_.running.clear()                                             # Free up the running flag
            return
        
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error):
            global_.running.clear()                                             # Free up the running flag
            self.interface.sendReply(connection_error,message=message)          # Return error message if there was a problem connecting
            return
        
        self.interface.reactToMessage("working_on_it",message=message)
        
        self.survey_args = [bias,n,i,suffix,xy,dx,sleepTime,ox,oy]              # Store these params for enhance to look at
        
        scan = Scan(NTCP)                                                       # Nanonis scan module
        
        if(bias != "-default"): self.rampBias(NTCP, bias)                       # Change the scan bias if the user wants to
        
        basename     = scan.PropsGet()[3]                                       # Get the save basename
        tempBasename = basename + '_' + suffix + '_'                            # Create a temp basename for this survey
        scan.PropsSet(series_name=tempBasename)                                 # Set the basename in nanonis for this survey
        
        count = i-1
        for frame in frames:
            count += 1
            self.currentSurveyIndex = count
            self.interface.sendReply('Running scan ' + str(count) + '/' + str(n**2) + ': ' + str(frame),message=message) # Send a message that the next scan is starting
            
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
            self.interface.sendPNG(pngFilename,notify=notify,message=message)   # Send a png over zulip
            
            if(self.checkEventFlags()): break                                   # Check event flags
        
        scan.PropsSet(series_name=basename)                                     # Put back the original basename
        self.disconnect(NTCP)                                                   # Close the TCP connection
        
        if(not enhance):
            global_.running.clear()                                             # Free up the running flag
        
        self.interface.sendReply('survey \'' + suffix + '\' done',message=message) # Send a notification that the survey has completed
    
    def enhance(self,bias,n,i,suffix,sleepTime,resume=True,message=""):
        if(self.survey_args == []):
            self.interface.sendReply("Need to run a survey first",message=message)
            global_.running.clear()                                             # Free up the running flag
            return
        
        if(i < 0):                                                              # i=-1 means we want to enhance the last complete scan in the survey
            i = self.currentSurveyIndex - 1                                     # subtract 1 because the current index points to the scan in progress, not the last completed frame
            
        if(i < 0): i = 0                                                        # Incase enhance is run before the first frame in a survey completes
        
        ns    = self.survey_args[1]                                             # Grid size of original survey
        count = 0                                                               # Lazy way to get ii and jj
        for ii in range(int(-ns/2),int(ns/2) + ns%2):
            jj_range = range(int(-ns/2),int(ns/2) + ns%2)
            if((ii+int(ns/2))%2): jj_range = reversed(jj_range)                 # Alternate grid direction each row so the grid snakes... better for drift
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
        
        resumeSurveyAtIdx = self.currentSurveyIndex                             # Survey is currently up to this frame. store for when survey is resumed after enhancing
        resumeSurveyArgs  = self.survey_args.copy()                             # Store the params of the current survey for when survey is resumed after enhancing
        resumeSurveyArgs[2] = resumeSurveyAtIdx                                 # Resuming the survey at this index after enhancing
        
        survey_args = [bias,n,1,suffix,xy,dx,sleepTime,ox,oy]
        self.survey(*survey_args,message=message,enhance=True)                  # Kick off a survey within the frame we want to enhance
        
        if(resume and global_.running.is_set()):
            self.interface.sendReply("Resuming survey...",message=message)
            self.survey(*resumeSurveyArgs,message=message)                      # Resume the survey
        
    
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
        
    def tipShape(self,np,pw,bias,zhold,rel_abs):
        self.interface.reactToMessage("at_work")
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
        
        try:
            tipShaper.Start(wait_until_finished=True,timeout=-1)
        except Exception as e:
            self.interface.sendReply(str(e))
        
        self.disconnect(NTCP)
        self.interface.reactToMessage("dagger")
        
    def tipShapePropsGet(self):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting
         
        tipShaper = TipShaper(NTCP)
        
        try:
            args = tipShaper.PropsGet()                                         # Grab all the current tip shaping settings in nanonis
        except Exception as e:
            self.interface.sendReply(str(e))
            self.disconnect(NTCP)
            return
        
        self.disconnect(NTCP)
        
        getStr  = "Switch off delay (sod): " + str(args[0])  + "\n"
        getStr += "Change bias flag  (cb): " + str(args[1])  + "\n"
        getStr += "Change bias value (b1): " + str(args[2])  + "\n"
        getStr += "Tip lift 1 height (z1): " + str(args[3])  + "\n"
        getStr += "Tip lift 1 time   (t1): " + str(args[4])  + "\n"
        getStr += "Tip lift bias     (b2): " + str(args[5])  + "\n"
        getStr += "Tip lift 2 time   (t2): " + str(args[6])  + "\n"
        getStr += "Tip lift 3 height (z3): " + str(args[7])  + "\n"
        getStr += "Tip lift 3 time   (t3): " + str(args[8])  + "\n"
        getStr += "Final wait time (wait): " + str(args[9])  + "\n"
        getStr += "Restore feeback   (fb): " + str(args[10]) + "\n"
        getStr += "Tip shape area  (area): " + str(self.designatedTipShapeArea) + "\n"
        getStr += "Area grid size  (grid): " + str(self.designatedGrid) + "\n"
        
        return getStr
    
    def tipShapeProps(self,sod,cb,b1,z1,t1,b2,t2,z3,t3,wait,fb,designatedArea,designatedGrid):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting
         
        tipShaper  = TipShaper(NTCP)
        
        try:
            default_args = tipShaper.PropsGet()                                 # Store all the current tip shaping settings in nanonis
        except Exception as e:
            self.interface.sendReply(str(e))
            self.disconnect(NTCP)
            return
            
        tipShaperArgs = [sod,cb,b1,z1,t1,b2,t2,z3,t3,wait,fb]                   # Order matters here
        for i,a in enumerate(tipShaperArgs):
            if(a=="-default"):
                tipShaperArgs[i] = default_args[i]
        
        z1 = tipShaperArgs[3]
        if(z1 < -50e-9):
            self.interface.sendReply("Limit for z1=-50e-9 m")
            self.disconnect(NTCP)
            return
        
        z3 = tipShaperArgs[7]
        if(z1 < -50e-9):
            self.interface.sendReply("Limit for z3=-50e-9 m")
            self.disconnect(NTCP)
            return
        
        if(z1 > 0):
            self.interface.sendReply("Sure you want a positive z1?")
            
        tipShaper.PropsSet(*tipShaperArgs)                                      # update the tip shaping params in nanonis
        
        self.designatedTipShapeArea = designatedArea
        self.designatedGrid[0] = designatedGrid
        
        self.disconnect(NTCP)
        self.interface.reactToMessage("+1")
    
    def pulsePropsGet(self):
        getStr  = "Num pulses          (np): " + str(self.defaultPulseParams[0]) + "\n"
        getStr += "Pulse width         (pw): " + str(self.defaultPulseParams[1]) + "\n"
        getStr += "Pulse bias        (bias): " + str(self.defaultPulseParams[2]) + "\n"
        getStr += "ZController hold (zhold): " + str(self.defaultPulseParams[3]) + "\n"
        getStr += "1=Rel. 2=Abs       (abs): " + str(self.defaultPulseParams[4]) + "\n"
        
        return getStr
    
    def pulseProps(self,np,pw,bias,zhold,rel_abs):
        if(abs(bias) > 10): return "Bias must be <= 10 V"
        self.defaultPulseParams = [np,pw,bias,zhold,rel_abs]                    # Store here because there's no TCP command to retrieve settings from nanonis
        self.interface.reactToMessage("+1")
        
    def pulse(self):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
        
        biasModule = Bias(NTCP)
        
        np,pw,bias,zhold,rel_abs = self.defaultPulseParams                      # Grab the stored pulse params
        for n in range(0,np):                                                   # Pulse the tip -np times
            biasModule.Pulse(pw,bias,zhold,rel_abs,wait_until_done=False)
            time.sleep(pw + 0.2)                                                # Wait 200 ms more than the pulse time
        
        self.disconnect(NTCP)
        self.interface.reactToMessage("explosion")
    
    def biasDep(self,nb,bdc,bi,bf,px,suffix,message=""):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting
        
        self.interface.reactToMessage("working_on_it",message=message)
        
        biasList = np.linspace(bi,bf,nb)
        
        scan = Scan(NTCP)
        
        basename     = scan.PropsGet()[3]                                       # Get the save basename
        tempBasename = basename + '_' + suffix + '_'                            # Create a temp basename for this survey
        scan.PropsSet(series_name=tempBasename)                                 # Set the basename in nanonis for this survey
        
        scanPixels,scanLines = scan.BufferGet()[2:]
        lx = int((scanLines/scanPixels)*px)
        
        x,y,w,h,angle = scan.FrameGet()
        
        ## Initial drift correct frame
        dxy = []
        initialDriftCorrect = []
        if(px > 0):
            self.rampBias(NTCP, bdc)
            scan.BufferSet(pixels=px,lines=lx)
            scan.Action('start',scan_direction='up')
            scan.WaitEndOfScan()
            scan.PropsSet(series_name=tempBasename + str(bdc) + "V-DC_")        # Set the basename in nanonis for this survey
            _,initialDriftCorrect,_ = scan.FrameDataGrab(14, 1)
            
            dx  = w/px; dy  = h/lx
            dxy = np.array([dx,dy])
        
        if(self.checkEventFlags()): biasList=[]                                 # Check event flags
        
        for b in biasList:
            if(b == 0): continue                                                # Don't set the bias to zero ever
            
            scan.PropsSet(series_name=tempBasename + str(b) + "V_")             # Set the basename in nanonis for this survey
            ## Bias dep scan
            self.rampBias(NTCP, b)
            scan.BufferSet(pixels=scanPixels,lines=scanLines)
            scan.Action('start',scan_direction='down')
            _, _, filePath = scan.WaitEndOfScan()
            
            _,scanData,_ = scan.FrameDataGrab(14, 1)
            
            
            pngFilename = self.makePNG(scanData, filePath)                      # Generate a png from the scan data
            
            notify = True
            if(not filePath): notify= False                                     # Don't @ users if the image isn't complete
            self.interface.sendPNG(pngFilename,notify=notify,message=message)   # Send a png over zulip
            
            if(self.checkEventFlags()): break                                   # Check event flags
            
            if(not len(initialDriftCorrect)): continue                          # If we haven't taken out initial dc image, dc must be turned off so continue
            
            scan.PropsSet(series_name=tempBasename + str(bdc) + "V-DC_")        # Set the basename in nanonis for this survey
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
            
        scan.PropsSet(series_name=basename)                                     # Put back the original basename
        
        self.disconnect(NTCP)
        
        global_.running.clear()
        
        self.interface.sendReply("Bias dependent imaging complete",message=message)
    
    def setBias(self,bias):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
        
        if(bias and abs(bias) < 10):
            self.rampBias(NTCP, bias)                                           # Only ramp the bias if it's not zero
            self.interface.reactToMessage("+1")
        else:
            self.interface.reactToMessage("cross_marker")
            
        self.disconnect(NTCP)
        
        global_.running.clear()
        
###############################################################################
# Utilities
###############################################################################
    def safeCurrentCheck(self,NTCP):
        motor         = Motor(NTCP)
        zController   = ZController(NTCP)
        currentModule = Current(NTCP)
        
        current = abs(currentModule.Get())
        threshold = self.safetyParams[0]
        print("Safe check... Current: " + str(current) + ", threshold: " + str(threshold))
        if(current < threshold):
            return True
        
        self.interface.sendReply("---\nWarning: Safe retract has been triggered.\n"
                                 + "Current: " + str(current*1e9) + " nA\n"
                                 + "Threshold: " + str(threshold*1e9) + " nA\n")
        
        zController.Withdraw(wait_until_finished=False)                         # Retract the tip
        
        try:
            print("Stopping other processes...")
            self.interface.stop(args=[])
        except Exception as e:
            self.interface.sendReply("---\nWarning: error stopping processes during safe retract...")
            self.interface.sendReply(str(e) + "\n---")
        
        safeFreq    = self.safetyParams[1]
        safeVoltage = self.safetyParams[2]
        motor.FreqAmpSet(safeFreq,safeVoltage)
        motor.StartMove(direction="Z+", steps=50,wait_until_finished=True)
        print("Retracted and moved 50 motor steps up")
        
        count = 0
        while(current > threshold):
            if(count%5 == 0):
                self.interface.sendReply("---\n"
                                     + "Warning: Safe retract has been triggered.\n"
                                     + "Current still above threshold after "
                                     + str((count+1)*50) + " Z+ motor steps.\n" 
                                     + "Current: " + str(current*1e9) + " nA\n"
                                     + "Threshold: " + str(threshold*1e9) + " nA\n")
                
            motor.StartMove(direction="Z+", steps=50,wait_until_finished=True)
            current = abs(currentModule.Get())
            count += 1
            print("Retracting another 50 steps... current: " + str(current*1e9) + " nA")
        
        self.interface.sendReply("Warning: Safe retract complete... current: " + str(current*1e9) + " nA\n---\n")
        return False
    
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
        
    def checkEventFlags(self,message = "",creep=False):
        if(creep): return not global_.creepRunning.is_set()
        
        if(not global_.running.is_set()): return 1                              # Running flag
        
        if(global_.pause.is_set()):
            NTCP,connection_error = self.connect()                              # Connect to nanonis via TCP
            if(connection_error): return connection_error                       # Return error message if there was a problem connecting        
            scan = Scan(NTCP)
            scan.Action(scan_action='pause')
            
            while global_.pause.is_set(): time.sleep(2)                         # Pause flag
            
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
        time.sleep(0.2)                                                         # Sleep