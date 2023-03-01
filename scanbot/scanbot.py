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
from nanonisTCP.FolMe import FolMe
from nanonisTCP.Marks import Marks

import time
from datetime import datetime as dt
from datetime import timedelta
import ntpath
import numpy as np
import nanonispyfit as napfit
import matplotlib.pyplot as plt

import math

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
            
    def survey(self,bias,n,startAt,suffix,xy,dx,px,sleepTime,stitch,hook,autotip,ox=0,oy=0,message="",enhance=False,reverse=False,clearRunning=True):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error):
            global_.running.clear()                                             # Free up the running flag
            return connection_error                                             # Return error message if there was a problem connecting        
        
        scan  = Scan(NTCP)
        piezo = Piezo(NTCP)
        range_x,range_y,_ = piezo.RangeGet()
        
        x = np.linspace(-1, 1,n) * (n-1)*dx/2
        y = x
        
        if(reverse and (n%2)): x = np.array(list(reversed(x)))
        if(reverse):           y = np.array(list(reversed(y)))
            
        if(xy == "-default"): xy = scan.FrameGet()[2]
        if(dx == "-default"): dx = xy
        
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
            
            if(autotip):                                                        # **Currently Testing**
                classification = utilities.classify(scanData)                   # Obtain image classification
                if(not classification['nan']):
                    if(classification['tipChanges'] > 0):                       # Arbitrary condition required to perform tip shape
                        self.interface.sendReply(str(classification),message=message)
            
            pngFilename,scanDataPlaneFit = self.makePNG(scanData, filePath,returnData=True,dpi=150) # Generate a png from the scan data
            self.interface.sendPNG(pngFilename,notify=True,message=message)     # Send a png over zulip
            
            if(hook):                                                           # call a custom python script
                try:
                    import hk_survey
                    hk_survey()
                except Exception as e:
                    self.interface.sendReply("Warning: Call to survey hook hk_survey.py failed:")
                    self.interface.sendReply(str(e))
            
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
            self.interface.sendPNG(stitchFilepath,notify=False,message=message) # Send a png over zulip
        
        scan.PropsSet(series_name=basename)                                     # Put back the original basename
        self.disconnect(NTCP)                                                   # Close the TCP connection
        if(clearRunning): global_.running.clear()                               # Free up the running flag
        
        self.interface.sendReply('survey \'' + suffix + '\' done',message=message) # Send a notification that the survey has completed
        
    def survey2(self,bias,n,startAt,suffix,xy,dx,px,sleepTime,stitch,hook,autotip, # Survey params
                     nx,ny,xStep,yStep,zStep,xyV,zV,xyF,zF,message=""):          # Move area params
        
        if(nx == 1): xStep = 0
        if(ny == 1): yStep = 0
        
        ydirection  = "Y+"
        if(yStep < 0):
            yStep *= -1
            ydirection = "Y-"
        
        xdirection = True
        if(xStep < 0):
            xStep *= -1
            xdirection = False
            
        reverse = False
        xdirections = ["X-","X+"]
        for y in range(ny):
            if(self.checkEventFlags()): break                                   # Check event flags
            for x in range(nx):
                if(self.checkEventFlags()): break                               # Check event flags
                
                s = suffix + "_y" + str(y) + "_x" + str(x)
                self.survey(bias,n,startAt,s,xy,dx,px,sleepTime,stitch,hook,autotip,reverse=reverse,clearRunning=False,message=message)
                reverse = not reverse
                
                if(self.checkEventFlags()): break                               # Check event flags
                time.sleep(2)
                
                if(x == nx-1): continue                                         # Skip the move area after last survey in this row since we'll be moving in y next
                
                if(self.checkEventFlags()): break                               # Check event flags
                
                direction = xdirections[xdirection]
                self.interface.sendReply("Moving " + str(xStep) + " steps in " + direction,message=message)
                
                success = self.moveArea(up=zStep,upV=zV,upF=zF,direction=direction,steps=xStep,dirV=xyV,dirF=xyF,zon=True)
                if(not success):
                    self.interface.sendReply("Error moving area... stopping")
                    global_.running.clear()
                    break
                
                time.sleep(sleepTime)
            
            xdirection = not xdirection                                         # Change x direction to snake the grid
            
            if(y == ny-1): continue                                             # Skip the move area after the last column since we're done.
            
            if(self.checkEventFlags()): break                                   # Check event flags
            
            self.interface.sendReply("Moving " + str(yStep) + " steps in " + ydirection,message=message)
            self.moveArea(up=zStep,upV=zV,upF=zF,direction=ydirection,steps=yStep,dirV=xyV,dirF=xyF,zon=True)
            
            time.sleep(sleepTime)
            
        global_.running.clear()
            
    def moveArea(self,up,upV,upF,direction,steps,dirV,dirF,zon,approach=True,message=""):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
        
        # Safety checks
        if(up < 10):
            self.disconnect(NTCP)
            self.interface.sendReply("-up must be > 10",message=message)
            return False
        
        if(upV > 300):
            self.disconnect(NTCP)
            self.interface.sendReply("-upV 300 V max",message=message)
            return False
        
        if(upF > 2.5e3):
            self.disconnect(NTCP)
            self.interface.sendReply("-upF 2.5 kHz max",message=message)
            return False
        
        if(dirV > 200):
            self.disconnect(NTCP)
            self.interface.sendReply("-dirV 200 V max",message=message)
            return False
        
        if(dirF > 2.5e3):
            self.disconnect(NTCP)
            self.interface.sendReply("-dirF 2.5 kHz max",message=message)
            return False
        
        if(upV < 1):
            self.disconnect(NTCP)                                               # Close the TCP connection
            self.interface.sendReply("-upV must be between 1 V and 200 V",message=message)
            return False
            
        if(upF < 500):
            self.disconnect(NTCP)                                               # Close the TCP connection
            self.interface.sendReply("-upF must be between 500 Hz and 2.5 kHz",message=message)
            return False
        
        if(dirV < 1):
            self.disconnect(NTCP)                                               # Close the TCP connection
            self.interface.sendReply("-upV must be between 1 V and 200 V",message=message)
            return False
            
        if(dirF < 500):
            self.disconnect(NTCP)                                               # Close the TCP connection
            self.interface.sendReply("-upF must be between 500 Hz and 2.5 kHz",message=message)
            return False
        
        if(not direction in ["X+","X-","Y+","Y-"]):
            self.disconnect(NTCP)                                               # Close the TCP connection
            self.interface.sendReply("-dir can only be X+, X-, Y+, Y-",message=message)
            return False
        
        if(steps < 0):
            self.disconnect(NTCP)
            self.interface.sendReply("-steps must be > 0",message=message)
            return False
        
        if(up < 0):
            self.disconnect(NTCP)
            self.interface.sendReply("-up must be > 0",message=message)
            return False
        
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
            isSafe = self.safeCurrentCheck(NTCP,message=message)                # Safe retract if current overload
            if(not isSafe):
                self.disconnect(NTCP)                                           # Close the TCP connection
                self.interface.sendReply("Could not complete move_area...",message=message)
                self.interface.sendReply("Safe retract was triggered because the current exceeded "
                                         + str(self.safetyParams[0]*1e9) + " nA"
                                         + " while moving areas",message=message)
                return False
                
            time.sleep(0.25)
        
        motor.StartMove(direction,leftOver,wait_until_finished=True)
        print("Moving motor: " + direction + " " + str(leftOver) + "steps")
        time.sleep(0.5)
        
        isSafe = self.safeCurrentCheck(NTCP,message=message)                    # Safe retract if current overload
        if(not isSafe):
            self.disconnect(NTCP)                                               # Close the TCP connection
            self.interface.sendReply("Could not complete move_area...",message=message)
            self.interface.sendReply("Safe retract was triggered because the current exceeded "
                                     + str(self.safetyParams[0]*1e9) + " nA"
                                     + " while moving areas",message=message)
            return False
        
        if(approach):
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
        
        return True
    
    def moveTip(self,lightOnOff,cameraPort,trackOnly,demo=0,roi=[],win=20,target=[]):
        """
        In development

        Parameters
        ----------
        lightOnOff : Flag to call hook hk_light. If set, a python script 
                     (~/scanbot/scanbot/hk_light.py) is called to turn the 
                     light on and off before/after moving the tip
        cameraPort : usually if you have a desktop windows machine with one 
                     camera plugged in, set this to 0. laptops with built-in 
                     cameras will probably be 1
        demo       : demo mode (temporary)
        roi        : region of interest to track - might be used later. for now
                     it's manually selected with a mouse
        win        : Window around the ROI to look at.

        """
        import cv2
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error):
            global_.running.clear()                                             # Free up the running flag
            return connection_error                                             # Return error message if there was a problem connecting
        
        if(lightOnOff):                                                         # If we want to turn the light on
            try:
                from hk_light import turn_on
                turn_on()                                                       # Call the hook to do so. Hook should return null if successful, otherwise it should throw an Exception
            except Exception as e:
                self.interface.sendReply("Error calling hook hk_lighton.py")
                self.disconnect(NTCP)
                global_.running.clear()                                         # Free up the running flag
                return str(e)
        
        cap = utilities.getVideo(cameraPort,demo)
        
        if(demo):
            utilities.trimStart(cap,frames=2000)                                # Trim off the start of the video
        
        if(not len(roi)):                                                       # Don't do this if we're passing in an ROI already
            ret,frame = utilities.getAveragedFrame(cap,n=1)                     # Read the first frame of the video
            
            self.interface.sendReply("Select tracking ROI. Press 'q' to cancel")
            roi = utilities.getROI(cap)
            if(not len(roi)):
                self.interface.sendReply("Cancelling move tip")
                self.disconnect(NTCP)
                global_.running.clear()                                         # Free up the running flag
                return
                
            self.interface.sendReply("Select a marker for the tip location. Press 'q' to cancel")
            tipPos = utilities.markPoint(cap)
        
        if(len(tipPos) and not len(target) and not trackOnly):
            ret,frame = utilities.getAveragedFrame(cap,n=1)                     # Read the first frame of the video
            
            self.interface.sendReply("Select target location for the tip. Press 'q' to cancel and enter track-only mode")
            target = utilities.markPoint(cap)
            
            if(len(target)): target = target - tipPos
            
            if(target[1] > 0):
                self.interface.sendReply("Error, cannot move tip lower than current position. Track-Only mode activated")
                target = []
        
        if(not len(target)): trackOnly = True
        
        ROI = utilities.extract(frame,roi)
        WIN = utilities.extract(frame,roi,win)
        
        xy = np.array([0,0])
        success = True
        while(cap.isOpened()):
            if(not success):
                self.interface.sendReply("Error moving area... tip crashed... stopping")
                global_.running.clear()
                break
            
            if(self.checkEventFlags()): break                                   # Check event flags
            ret, frame = utilities.getAveragedFrame(cap,n=11)
            if(not ret): break
        
            oxy = utilities.trackROI(im1=ROI, im2=WIN)
            
            currentPos = xy + oxy
            # print(currentPos,oxy,roi[1])
            
            ROI,WIN,roi,xy = utilities.update(roi,ROI,win,frame,oxy,xy)
            
            rec = utilities.drawRec(frame.astype(np.uint8), roi, xy=oxy)
            rec = utilities.drawRec(rec, roi, win=win)
            
            if(len(tipPos)): rec = cv2.circle(rec, currentPos + tipPos, radius=3, color=(0, 0, 255), thickness=-1)
            if(len(target)): rec = cv2.circle(rec, target + tipPos, radius=3, color=(0, 255, 0), thickness=-1)
            
            cv2.imshow('Frame',rec)
            
            if cv2.waitKey(25) & 0xFF == ord('q'): break                        # Press Q on keyboard to  exit
            
            if(trackOnly): continue
        
            zV = 195
            zF = 1100
            xyV = 130
            xyF = 1100
            if(currentPos[1] > target[1]):                                      # First priority is to always keep the tip above this line
                print("Move tip up")
                success = self.moveArea(up=1000, upV=zV, upF=zF, direction="X+", steps=0, dirV=xyV, dirF=xyF, zon=False, approach=False)
                continue
            if(currentPos[0] < target[0]):
                print("Move tip right")
                success = self.moveArea(up=10, upV=zV, upF=zF, direction="X+", steps=500, dirV=xyV, dirF=xyF, zon=False, approach=False)
                continue
            if(currentPos[0] > target[0]):
                print("Move tip left")
                success = self.moveArea(up=10, upV=zV, upF=zF, direction="X-", steps=500, dirV=xyV, dirF=xyF, zon=False, approach=False)
                continue
            
            print("Target Hit!")
            break                                                               # Target reached!
        
        cap.release()
        cv2.destroyAllWindows()
        
        if(lightOnOff):                                                         # If we want to turn the light off
            try:
                from hk_light import turn_off
                turn_off()                                                      # Call the hook to do so. Hook should return null if successful, otherwise it should throw an Exception
            except Exception as e:
                self.interface.sendReply("Error calling hook hk_lighton.py")
                self.disconnect(NTCP)
                global_.running.clear()                                         # Free up the running flag
                return str(e)
            
        self.disconnect(NTCP)                                                   # Close the TCP connection
        global_.running.clear()                                                 # Free up the running flag
        
    def zdep(self,zi,zf,nz,iset,bset,dciset,bias,dcbias,ft,bt,dct,px,dcpx,lx,dclx,suffix,makeGIF,message=""):
        """
        This function performs a set of constant height scans at different tip 
        heights. 
        Drift correction can be performed between each scan.
        The tip must be within the scan frame to start.
        
        Process:
            1. Setpoint:
                1. The tip's position within the scan frame is recorded and is
                   used as the location to obtain the initial setpoint.
                2. The z-controller is turned on
                3. The z-controller setpoint is set to -iset
                4. The bias is ramped to -bset
                5. 100 z positions are averaged to obtain reference zref
                6. The z-controller is turned off
                7. The bias is ramped to -bias
                8. A tip lift is performed before each scan. i.e. the 
                   z-controller is set to zref + dz, where dz is the tip lift 
                   for whichever scan we are up to in the set.
                   
            2. Drift correction (Turned on when -dcbias is non-zero)
                1. An initial scan is acquired as a reference with V=dcbias and
                   Iset=cdiset before the first scan.
                2. Drift correction scans are acquired between each successive 
                   scan.
                3. The scan frame window and tip setpoint location are updated 
                   according to the offset between the latest drift correction
                   scan and the initial drift correction scan to avoid creep
                4. The piezo z drift compensation is updated according to the 
                   difference in zref between scans
            
            3. End of run:
                1. The z-controller is tuned on
                2. The z-controller setpoint is set to -iset
                3. Stopping the scan at any point will end the process in this 
                   way
                
                   
        """
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error):
            global_.running.clear()                                             # Free up the running flag
            return connection_error                                             # Return error message if there was a problem connecting        
        
        scanModule = Scan(NTCP)
        biasModule = Bias(NTCP)
        zController = ZController(NTCP)
        folme = FolMe(NTCP)
        piezo = Piezo(NTCP)
        
        tipPos    = folme.XYPosGet(Wait_for_newest_data=1)
        scanFrame = scanModule.FrameGet()
        if(not self.tipInFrame(tipPos,scanFrame)):
            self.interface.sendReply("Tip must be in scan frame to get setpoint")
            self.disconnect(NTCP)                                               # Close the TCP connection
            global_.running.clear()                                             # Free up the running flag
            return
        
        currentISet = zController.SetpntGet()
        if(not iset == '-default'):                                             # Only update setpoint if the user provided it
            if(abs(iset) > 1e-9):                                               # Limit to 1 nA to avoid accidental setpoints
                self.interface.sendReply('Maximum setpoint using -iset is 1 nA. If you want iset > 1 nA, put the setting into nanonis and run zdep without the -iset param.')
                self.disconnect(NTCP)
                global_.running.clear()                                         # Free up the running flag
                return
        else:
            iset = currentISet
            
        if(not dciset == '-default'):                                           # Only update setpoint if the user provided it
            if(abs(dciset) > 1e-9):                                             # Limit to 1 nA to avoid accidental setpoints
                self.interface.sendReply('Maximum setpoint using -dciset is 1 nA. If you want iset > 1 nA, put the setting into nanonis and run zdep without the -iset param.')
                self.disconnect(NTCP)
                global_.running.clear()                                         # Free up the running flag
                return
        else:
            dciset = currentISet
        
        basename = self.interface.topoBasename                                  # Get the basename that's been set in config file
        if(not basename): basename = scanModule.PropsGet()[3]                   # Get the save basename from nanonis if one isn't supplied
        tempBasename = basename + '_' + suffix + '_'                            # Create a temp basename for this survey
        scanModule.PropsSet(series_name=tempBasename)                           # Set the basename in nanonis for this survey
        
        _,_,pixels,lines = scanModule.BufferGet()
        if(px   == '-default'):
            px = pixels
            lx = lines
        if(dcpx == '-default'):
            dcpx = pixels
            dclx = lines
            
        if(lx   == 0): lx = px                                                  # Scan frame is square if lx = 0
        if(dclx == 0): dclx = dcpx                                              # Scan frame is square if dclx = 0
        
        _,_,fwdTime,bwdTime,_,_ = scanModule.SpeedGet()
        if(ft == '-default'): ft = fwdTime
        if(bt == '-default'): bt = bwdTime
        speedRatio = ft/bt                                                      # Speed ratio is forward time per line/backward time per line
        
        if(dct == '-default'): dct = fwdTime
        
        v = biasModule.Get()
        if(bset   == '-default'): bset   = v
        if(bias   == '-default'): bias   = v
        if(dcbias == '-default'): dcbias = v
        if(bset > 0):
            self.interface.sendReply("Cannot set -bset to 0 V or tip will crash")
            self.disconnect(NTCP)
            global_.running.clear()                                             # Free up the running flag
        
        status, vx, vy, vz, _, _, _ = piezo.DriftCompGet()
        if not status:
            piezo.DriftCompSet(on=False, vx=0, vy=0, vz=0)
            
        previous_zref = {}
        dx  = scanFrame[2]/px; dy  = scanFrame[3]/dclx
        dxy = np.array([dx,dy])
        ox,oy = np.array([0,0])
        dzList = np.linspace(zi, zf, nz)
        initialDC = np.zeros((dcpx,dcpx))
        print("dzList: " + str(dzList))
        
        scanTime  = lx*(ft + bt)
        delayTime = 4
        if(abs(dcbias) > 0):
           scanTime  += 2*dclx*dct
           delayTime += 1.5
        
        GIF = np.empty((len(dzList)),lx,px)
        eta = len(dzList)*(scanTime + delayTime)
        completionTime = dt.now() + timedelta(seconds=eta)
        self.interface.sendReply("Starting zdep.. ETA: " + str(completionTime))
        for idx,dz in enumerate(dzList):
            self.interface.sendReply("Scan " + str(idx+1) + "/" + str(len(dzList)))
            print("doing dz = " + str(dz*1e9) + " nm")
            if(abs(dcbias) > 0):                                                # If drift correction is turned on, take a drift correction image
                time.sleep(0.25)
                zController.OnOffSet(on=1)                                      # Turn on the controller to get reference
                
                time.sleep(0.25)
                print("DC: Setpoint: " + str(dciset*1e12) + " pA")
                zController.SetpntSet(setpoint=abs(dciset))                     # Update setpoint current in nanonis
                time.sleep(0.25)
                
                print("DC: px,lx: " + str([dcpx,dclx]))
                scanModule.BufferSet(pixels=dcpx,lines=dclx)
                print("DC: tpl: " + str(dct) + " s")
                scanModule.SpeedSet(fwd_line_time=dct,speed_ratio=1)
                
                print("DC: Ramping bias: " + str(dcbias))
                self.rampBias(NTCP, dcbias)
                time.sleep(0.25)
                
                print("DC: Taking scan")
                scanModule.PropsSet(series_name=tempBasename + str(dcbias) + "V-DC_") # Set the basename in nanonis for this survey
                scanModule.Action('start',scan_direction='up')
                _, _, filePath = scanModule.WaitEndOfScan()
                if(not filePath): break                                         # If the scan was stopped before finishing, stop zdep
                _,driftCorrection,_ = scanModule.FrameDataGrab(14, 1)
                
                if(np.sum(initialDC) == 0): initialDC = driftCorrection
                print("Scan Angle: " + str(scanFrame[4]))
                ox,oy = utilities.getFrameOffset(initialDC,driftCorrection,dxy,theta=-scanFrame[4]) # Frame offset for drift correction. passing negative scan angle because nanonis is backwards
                print("DC: ox,oy: " + str([ox,oy]))
                
                scanFrame[0] -= ox
                scanFrame[1] -= oy
                scanModule.FrameSet(*scanFrame)
                
                tipPos -= np.array([ox,oy])
                
            time.sleep(0.25)
            zController.OnOffSet(on=1)                                          # Turn on the controller to get reference
            print("CH: Moving tip: " + str(tipPos))
            folme.XYPosSet(tipPos[0], tipPos[1], Wait_end_of_move=True)
            
            time.sleep(0.5)
            print("CH: Setpoint: " + str(iset*1e12) + " pA")
            zController.SetpntSet(setpoint=abs(iset))                           # Update setpoint current in nanonis
            
            time.sleep(0.5)
            print("CH: Ramping to setpoint bias: " + str(bset) + " V")
            self.rampBias(NTCP, bset)
            
            zref = 0
            time.sleep(0.5)
            for i in range(100):
                zref += zController.ZPosGet()/100                               # Average 100 values of z position. This is the position zi and zf are relative to
                time.sleep(0.01)                                                # 10 ms sample rate
            
            if('time' in previous_zref):
                deltaz = zref - previous_zref['z']
                deltat = (dt.now() - previous_zref['time']).total_seconds()
                dvz = deltaz/deltat
                status, vx, vy, vz, _, _, _ = piezo.DriftCompGet()              # the vz velocity
                print("deltaz/deltat = " + str(deltaz) + "/" + str(deltat))
                print("vz,dvz,vz+dvz = " + str(vz) + "," + str(dvz) + "," + str(dvz + vz))
                if(not -dcbias == 0):                                           # Only do this if dc is turned on
                    print("Updating piezo drift compensation")
                    piezo.DriftCompSet(on=True, vx=vx, vy=vy, vz=vz+dvz)
                
            previous_zref = {'z' : zref,
                             'time' : dt.now()}
            print("setting previous zref to: " + str(previous_zref))
            
            print("CH: zref 100 averages: " + str(zref*1e9) + " nm")
            zController.OnOffSet(on=False)                                      # Turn off the controller
            
            print("CH: Ramping bias: " + str(bias) + " V")
            self.rampBias(NTCP, bias, zhold=False)                              # zhold=False leaves the zhold setting as is during bias ramp (i.e. don't turn controller on after bias ramp complete)
            
            time.sleep(0.25)
            print("CH: moving to z=" + str(1e9*zref + 1e9*dz))
            zController.ZPosSet(zpos=zref + dz)                                 # Go to the next position
            
            print("CH: px,lx: " + str([px,lx]))
            scanModule.BufferSet(pixels=px,lines=lx)
            print("CH: fwd,ratio: " + str([ft,speedRatio]))
            scanModule.SpeedSet(fwd_line_time=ft,speed_ratio=speedRatio)
            scanModule.PropsSet(series_name=tempBasename + str(int(dz*1e12)) + "pm_")     # Set the basename in nanonis for this survey
            scanModule.Action('start',scan_direction='down')
            _, _, filePath = scanModule.WaitEndOfScan()
            if(not filePath): break
            
            _,scanData,_ = scanModule.FrameDataGrab(18, 1)                      # 14 = z., 18 is Freq. shift
            pngFilename = self.makePNG(scanData, filePath)                      # Generate a png from the scan data
            GIF[idx] = scanData
            
            self.interface.sendPNG(pngFilename,notify=False,message=message)    # Send a png over zulip
            
        print("Finishing up.. turning controller on")
        time.sleep(0.25)
        zController.OnOffSet(on=1)                                              # Turn on the controller
        
        time.sleep(0.25)
        zController.SetpntSet(setpoint=abs(iset))                               # Update setpoint current in nanonis
        time.sleep(0.25)
        scanModule.PropsSet(series_name=basename)                               # Put back the original basename
        
        # self.interface.sendPNG(utilities.makeGif(GIF),notify=False,message=message)
        
        self.interface.sendReply("zdep " + suffix + " complete")
        
        self.disconnect(NTCP)                                                   # Close the TCP connection
        global_.running.clear()                                                 # Free up the running flag
    
    def registration(self,zset,iset,bset,bias,ft,bt,px,lx,lz,dz,scanDir,suffix,message=""):
        """
        This function was written to perform nc-AFM registration but may be 
        used for any instance where a tip lift is required during the scan.
        The tip must be within the scan window to start.
        
        Each input parameter is described in scanbot_interface.py/registration
        
        Process:
            1. Setpoint:
                1. Z-Controller is turned on
                2. Setpoint current -iset is set
                3. Bias is ramped to -bset
                4. 100 z positions are averaged at the initial tip location to 
                   obtain zref
                5. The z-controller is turned off
                6. The bias is ramped to -bias
                7. The z piezo is set to zref + zset
            2. Scanning:
                1. The scan is started in a direction set by -dir
                2. The scan frame is polled at an interval = -ft + -bt to check
                   if -lz lines have been acquired.
                3. Once -lz lines have been acquired, the scan is paused and 
                   a tip lift -dz is performed. i.e. the zcontroller is set to
                   position zref + zi + dz
                4. The scan is resumed
            3. End of scan:
                1. The z-controller is tuned on
                2. The z-controller setpoint is set to -iset
                3. Stopping the scan at any point will end the process in this 
                   way

        """
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error):
            global_.running.clear()                                             # Free up the running flag
            return connection_error                                             # Return error message if there was a problem connecting        
        
        scanModule = Scan(NTCP)
        biasModule = Bias(NTCP)
        zController = ZController(NTCP)
        folme = FolMe(NTCP)
        marks = Marks(NTCP)
        
        tipPos    = folme.XYPosGet(Wait_for_newest_data=1)
        scanFrame = scanModule.FrameGet()
        if(not self.tipInFrame(tipPos,scanFrame)):
            self.interface.sendReply("Tip must be in scan frame to get setpoint")
            self.disconnect(NTCP)                                               # Close the TCP connection
            global_.running.clear()                                             # Free up the running flag
            return
        
        currentISet = zController.SetpntGet()
        if(not iset == '-default'):                                             # Only update setpoint if the user provided it
            if(abs(iset) > 1e-9):                                               # Limit to 1 nA to avoid accidental setpoints
                self.interface.sendReply('Maximum setpoint using -iset is 1 nA. If you want iset > 1 nA, put the setting into nanonis and run zdep without the -iset param.')
                self.disconnect(NTCP)
                global_.running.clear()                                         # Free up the running flag
                return
        else:
            iset = currentISet
        
        basename = self.interface.topoBasename                                  # Get the basename that's been set in config file
        if(not basename): basename = scanModule.PropsGet()[3]                   # Get the save basename from nanonis if one isn't supplied
        tempBasename = basename + '_' + suffix + '_'                            # Create a temp basename for this survey
        scanModule.PropsSet(series_name=tempBasename)                           # Set the basename in nanonis for this survey
        
        _,_,pixels,lines = scanModule.BufferGet()
        if(px   == '-default'):
            px = pixels
            lx = lines
        
        if(lx   == 0): lx = px                                                  # Scan frame is square if lx = 0
        
        _,_,fwdTime,bwdTime,_,_ = scanModule.SpeedGet()
        if(ft == '-default'): ft = fwdTime
        if(bt == '-default'): bt = bwdTime
        speedRatio = ft/bt                                                      # Speed ratio is forward time per line/backward time per line
        
        v = biasModule.Get()
        if(bset == '-default'): bset = v
        if(bias == '-default'): bias = v
        if(bset > 0):
            self.interface.sendReply("Cannot set -bset to 0 V or tip will crash")
            self.disconnect(NTCP)
            global_.running.clear()                                             # Free up the running flag
        
        scanDir = scanDir.lower()
        if(not scanDir in ["down","up"]):
            self.interface.sendReply("Scan direction must be either 'up' or 'down'")
            self.disconnect(NTCP)                                               # Close the TCP connection
            global_.running.clear()                                             # Free up the running flag
            return
        
        if(lz >= lx or lz < 1):
            self.interface.sendReply("-lz must be within the scan frame")
            self.disconnect(NTCP)                                               # Close the TCP connection
            global_.running.clear()                                             # Free up the running flag
            return
            
        updown = 1
        if(scanDir == "up"): updown = -1
        x,y,w,h,angle = scanFrame
        angle = -angle*math.pi/180
        start = np.array([x,y])
        start[0] -= w/2
        start[1] += (h/2 - h*(lz/lx))*updown
        start = utilities.rotate(origin=[x,y], point=start, angle=angle)
        
        end = np.array([x,y])
        end[0] += w/2
        end[1] += (h/2 - h*(lz/lx))*updown
        end = utilities.rotate(origin=[x,y], point=end, angle=angle)
        marks.LineDraw(start=start,end=end)
        
        scanModule.BufferSet(pixels=px,lines=lx)
        scanModule.SpeedSet(fwd_line_time=ft,speed_ratio=speedRatio)
        scanModule.PropsSet(series_name=tempBasename)                           # Set the basename in nanonis
        
        zController.OnOffSet(on=1)                                              # Turn on the controller to get reference
        time.sleep(0.25)
        zController.SetpntSet(setpoint=abs(iset))                               # Update setpoint current in nanonis
        time.sleep(0.5)
        self.rampBias(NTCP, bias=bset)
        
        zref = 0
        time.sleep(0.5)
        for i in range(100):
            zref += zController.ZPosGet()/100                                   # Average 100 values of z position. This is the position zi and zf are relative to
            time.sleep(0.01)                                                    # 10 ms sample rate
        
        time.sleep(0.25)
        zController.OnOffSet(on=0)                                              # Turn off the controller
        time.sleep(0.25)
        self.rampBias(NTCP, bias=bias)
        time.sleep(0.5)
        zController.ZPosSet(zpos=zref + zset)                                   # Go to the setpoint
        time.sleep(0.25)
        
        scanModule.Action('start',scan_direction=scanDir)
        while(True):  
            timeout,_,_= scanModule.WaitEndOfScan(timeout=int((ft+bt)*1000))
            if(self.checkEventFlags() or not timeout):                          # Check event flags
                marks.LinesErase()
                time.sleep(0.25)
                zController.OnOffSet(on=1)                                      # Turn on the controller
                time.sleep(0.25)
                zController.SetpntSet(setpoint=abs(iset))                       # Update setpoint current in nanonis
                time.sleep(0.25)
                scanModule.PropsSet(series_name=basename)                       # Put back the original basename
                self.interface.sendReply("registration " + suffix + " stopped")
                self.disconnect(NTCP)                                           # Close the TCP connection
                global_.running.clear()                                         # Free up the running flag
                return
                
            _,scanData,_ = scanModule.FrameDataGrab(0, 1)                       # 14 = z., 18 is Freq. shift
            scanData = np.sum(abs(scanData),axis=1)
            lines = sum(scanData > 0)
            if(lines > lz):
                scanModule.Action('pause',scan_direction=scanDir)
                time.sleep(1)
                zController.ZPosSet(zpos=zref+zset+dz)                          # Apply dz offset
                time.sleep(1)
                scanModule.Action('resume',scan_direction=scanDir)
                break
            
        _, _, filePath = scanModule.WaitEndOfScan()
        if(not filePath): pass
        
        _,scanData,_ = scanModule.FrameDataGrab(18, 1)                          # 14 = z., 18 is Freq. shift
        pngFilename = self.makePNG(scanData, filePath)                          # Generate a png from the scan data
        self.interface.sendPNG(pngFilename,notify=False,message=message)        # Send a png over zulip
            
        time.sleep(0.25)
        zController.OnOffSet(on=1)                                              # Turn on the controller
        
        time.sleep(0.25)
        zController.SetpntSet(setpoint=abs(iset))                               # Update setpoint current in nanonis
        time.sleep(0.25)
        scanModule.PropsSet(series_name=basename)                               # Put back the original basename
        
        marks.LinesErase()
        self.interface.sendReply("registration " + suffix + " complete")
        
        self.disconnect(NTCP)                                                   # Close the TCP connection
        global_.running.clear()                                                 # Free up the running flag
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
    def tipInFrame(self,tipPos,scanFrame):
        x,y,w,h,angle = scanFrame
        angle = angle*math.pi/180
        tipX,tipY = utilities.rotate([x,y],tipPos,angle)
        bottomLeft = np.array([x-w/2,y-h/2])
        topRight = np.array([x+w/2,y+h/2])
        if(tipX < bottomLeft[0] or tipX > topRight[0]): return False
        if(tipY < bottomLeft[1] or tipY > topRight[1]): return False
        return True
    
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
            
    def safeCurrentCheck(self,NTCP,message=""):
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
                                 + "Threshold: " + str(threshold*1e9) + " nA\n",message=message)
        
        zController.Withdraw(wait_until_finished=False)                         # Retract the tip
        
        try:                                                                    # Stop anything running. try/except is probably overkill but just in case
            print("Stopping other processes...")
            self.interface.stop(user_args=[])
        except Exception as e:
            self.interface.sendReply("---\nWarning: error stopping processes during safe retract...",message=message)
            self.interface.sendReply(str(e) + "\n---",message=message)
        
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
                                     + "Threshold: " + str(threshold*1e9) + " nA\n",message=message)
                
            motor.StartMove(direction="Z+", steps=50,wait_until_finished=True)  # Move another 50 steps up
            current = abs(currentModule.Get())                                  # Get the tip current after moving
            count += 1
            print("Retracting another 50 steps... current: " + str(current*1e9) + " nA")
        
        self.interface.sendReply("Warning: Safe retract complete... current: " + str(current*1e9) + " nA\n---\n",message=message)
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