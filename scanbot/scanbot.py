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
from nanonisTCP.TipShaper import TipShaper

import time
from datetime import datetime as dt
from datetime import timedelta
import ntpath
import numpy as np
import nanonispyfit as napfit
import matplotlib.pyplot as plt
import cv2

import math

import global_

import utilities

class scanbot():
    channel      = 14                                                           # Default plot channel. Change this using plot_channel command
    
    safeCurrent  = 5e-9                                                         # Current above this value is considered a tip crash.   Dummy value - this gets overridden by config.
    safeRetractV = 200                                                          # Voltage applied during safe retract.                  Dummy value - this gets overridden by config.
    safeRetractF = 1500                                                         # Frequency applied during safe retract.                Dummy value - this gets overridden by config.
    
    zMaxV  = 200                                                                # Voltage limits Dummy value - this gets overridden by config.
    zMinV  = 0                                                                  # Voltage limits Dummy value - this gets overridden by config.
    xyMaxV = 130                                                                # Voltage limits Dummy value - this gets overridden by config.
    xyMinV = 0                                                                  # Voltage limits Dummy value - this gets overridden by config.
        
    zMaxF  = 5000                                                               # Frequency limits Dummy value - this gets overridden by config.
    zMinF  = 500                                                                # Frequency limits Dummy value - this gets overridden by config.
    xyMaxF = 5000                                                               # Frequency limits Dummy value - this gets overridden by config.
    xyMinF = 500                                                                # Frequency limits Dummy value - this gets overridden by config.
    
    autoInitSet  = False                                                        # Flag to indicate whether tip, sample, and clean metal locations have been initialised
    
    surveyParams  = []                                                          # Last survey params
    survey2Params = []                                                          # Last survey2 params
###############################################################################
# Constructor
###############################################################################
    def __init__(self,interface):
        self.interface = interface
        
###############################################################################
# Data Acquisition
###############################################################################
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
            
    def survey(self,bias,n,startAt,suffix,xy,dx,px,sleepTime,stitch,survey_hk,classifier_hk,autotip,ox=0,oy=0,message="",enhance=False,reverse=False,iamauto=False):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error):
            global_.running.clear()                                             # Free up the running flag
            return connection_error                                             # Return error message if there was a problem connecting        
        
        if((autotip == 1) and (self.autoInitSet == False)):
            self.interface.sendReply("Error: run the auto_init command to initialise tip, sample, and clean metal locations before setting -autotip=1")
            self.disconnect(NTCP)
            global_.running.clear()                                             # Free up the running flag
            return
        
        self.surveyParams = [bias,n,startAt,suffix,xy,dx,px,sleepTime,stitch,survey_hk,classifier_hk,autotip]
        
        scan  = Scan(NTCP)
        piezo = Piezo(NTCP)
        range_x,range_y,_ = piezo.RangeGet()
        
        if(xy == "-default"): xy = scan.FrameGet()[2]
        if(dx == "-default"): dx = xy
        
        x = np.linspace(-1, 1,n) * (n-1)*dx/2
        y = x
        
        if(reverse and (n%2)): x = np.array(list(reversed(x)))
        if(reverse):           y = np.array(list(reversed(y)))
        
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
        
        callAutoTipShape = False
        classificationHistory = []
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
                classification = utilities.classify(scanData,filePath,classificationHistory) # Obtain image classification
                if(classifier_hk):
                    try:
                        from hk_classifier import run
                        classification = run(scanData,filePath,classificationHistory) # Overwrite classification with the one from the hook
                    except Exception as e:
                        self.interface.sendReply("Warning: Call to survey hook hk_classifier.py failed:")
                        self.interface.sendReply(str(e))
                        self.interface.sendReply("Default Scanbot classifier will be used instead.")
                    
                classificationHistory.append(classification)
                
                if(classification["tipShape"] == 1):
                    print("auto tip shaping initate!")
                    global_.running.clear()
                    callAutoTipShape = True
            
            pngFilename,scanDataPlaneFit = self.makePNG(scanData, filePath,returnData=True,dpi=150) # Generate a png from the scan data
            self.interface.sendPNG(pngFilename,notify=True,message=message)     # Send a png over zulip
            
            if(survey_hk):                                                      # call a custom python script
                try:
                    from hk_survey import run
                    metaData = self.getMetaData(filePath)
                    run(scanData,filePath,metaData)
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
            
            if(self.checkEventFlags()): break                                   # Check event flags
        
        if(stitch == 1 and not np.isnan(stitchedSurvey).all()):
            stitchFilepath = self.makePNG(stitchedSurvey,pngFilename = suffix + '.png',dpi=150*n, fit=False)
            self.interface.sendPNG(stitchFilepath,notify=False,message=message) # Send a png over zulip
        
        scan.PropsSet(series_name=basename)                                     # Put back the original basename
        self.disconnect(NTCP)                                                   # Close the TCP connection
    
        self.interface.sendReply('survey \'' + suffix + '\' done',message=message) # Send a notification that the survey has completed
        
        if(not iamauto):
            global_.running.clear()                                             # Free up the running flag
        
        if(iamauto): return callAutoTipShape
        
        if(callAutoTipShape):
            user_args = ['-run=survey', '-return=1', '-tipshape=1']
            self.interface.moveTipToClean(user_args=user_args)
        
    def survey2(self,bias,n,startAt,suffix,xy,dx,px,sleepTime,stitch,survey_hk,classifier_hk,autotip, # Survey params
                     nx,ny,xStep,yStep,zStep,xyV,zV,xyF,zF,message=""):          # Move area params
        
        self.survey2Params = [bias,n,startAt,suffix,xy,dx,px,sleepTime,stitch,survey_hk,classifier_hk,autotip, # Survey2 params
                              nx,ny,xStep,yStep,zStep,xyV,zV,xyF,zF]
    
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
                callAutoTipShape = self.survey(bias,n,startAt,s,xy,dx,px,sleepTime,stitch,survey_hk,classifier_hk,autotip,reverse=reverse,iamauto=False,message=message)
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
        
        if(callAutoTipShape):
            user_args = ['-run=survey2', '-return=1', '-tipshape=1']
            self.interface.moveTipToClean(user_args=user_args)
    
    def biasDep(self,nb,dcbias,tdc,dcSpeedRatio,pxdc,lxdc,bi,bf,px,lx,tlf,speedRatio,suffix,message=""):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error):
            global_.running.clear()                                             # Free up the running flag
            return connection_error                                             # Return error message if there was a problem connecting  
        
        self.interface.reactToMessage("working_on_it",message=message)
        
        scanModule  = Scan(NTCP)
        
        basename = self.interface.topoBasename                                  # Get the basename that's been set in config file
        if(not basename): basename = scanModule.PropsGet()[3]                   # Get the save basename from nanonis if one isn't supplied
        tempBasename = basename + '_' + suffix + '_'                            # Create a temp basename for this survey
        scanModule.PropsSet(series_name=tempBasename)                           # Set the basename in nanonis for this survey
        
        scanFrame = scanModule.FrameGet()                                       # [x,y,w,h,theta]
        
        if(tlf == '-default'): _,_,tlf,_,_,_ = scanModule.SpeedGet()            # Get the default time per line if it's not provided
        
        print(px,lx,pxdc,lxdc)
        if(px == '-default'): px = scanModule.BufferGet()[2]                    # Get the default number of pixels from nanonis
        px = int(np.ceil(px/16)*16)                                             # Ensure the number of pixels is divisible by 16 (nanonis requirement)
        if(lx == 0): lx = px                                                    # Default lx=px if lx not provided
        
        pxdc = int(np.ceil(pxdc/16)*16)                                         # Ensure the number of pixels for the drift correct frame is divisible by 16 (nanonis requirement)
        if(lxdc == 0): lxdc = int((pxdc*lx)/px)                                 # Keep the same ratio as px:lx if lxdc not provided
        
        print(px,lx,pxdc,lxdc)
        if(px < 16 or lx < 0 or pxdc < 16 or lxdc < 0): 
            self.interface.sendReply("Error: Check -px, -lx, -pxdc, and -lxdc",message=message)
            global_.running.clear()                                             # Free up the running flag
            self.disconnect(NTCP)
            return
        
        dx    = scanFrame[2]/pxdc
        dy    = scanFrame[3]/lxdc
        dxy   = np.array([dx,dy])
        ox,oy = np.array([0,0])
        
        GIF       = []
        biasList  = np.linspace(bi,bf,nb)
        initialDC = np.zeros((pxdc,pxdc))
        for idx,bias in enumerate(biasList):
            self.interface.sendReply("Scan " + str(idx+1) + "/" + str(nb))
            if(abs(dcbias) > 0):                                                # If drift correction is turned on, take a drift correction image
                time.sleep(0.25)
                scanModule.BufferSet(pixels=pxdc,lines=lxdc)
                scanModule.SpeedSet(fwd_line_time=tdc,speed_ratio=dcSpeedRatio)
                
                print("Ramping bias to " + str(dcbias) + " and taking drift correction image.")
                self.rampBias(NTCP, dcbias)
                time.sleep(0.25)
                
                basename_dc = tempBasename + str(int(dcbias*100)/100) + "V-DC_"
                scanModule.PropsSet(series_name=basename_dc)                    # Set the basename for drift correction images
                scanModule.Action('start',scan_direction='up')
                _, _, filePath = scanModule.WaitEndOfScan()
                if(not filePath): break                                         # If the scan was stopped manually before, stop here
                _,driftCorrection,_ = scanModule.FrameDataGrab(14, 1)
                
                if(np.sum(initialDC) == 0): initialDC = driftCorrection         # On the first run through, we will compare the initial drift correction frame with itself, so ox,oy = 0,0
                ox,oy = utilities.getFrameOffset(initialDC,driftCorrection,dxy,theta=-scanFrame[4]) # Frame offset for drift correction. passing negative scan angle because nanonis is backwards
                print("Frame offset correction offset: " + str([ox,oy]))
                
                scanFrame[0] -= ox
                scanFrame[1] -= oy
                scanModule.FrameSet(*scanFrame)                                 # Move the scan frame
                
            print("Ramping to next image bias: " + str(int(100*bias)/100) + " V")
            self.rampBias(NTCP, bias)                                           # Ramp to the next image bias
            
            scanModule.BufferSet(pixels=px,lines=lx)
            scanModule.SpeedSet(fwd_line_time=tlf,speed_ratio=speedRatio)
            
            basename_image = tempBasename + str(int(100*bias)/100) + "V_"
            scanModule.PropsSet(series_name=basename_image)                     # Set the basename in nanonis for this survey
            
            scanModule.Action('start',scan_direction='down')
            _, _, filePath = scanModule.WaitEndOfScan()
            if(not filePath): break
            
            _,scanData,_ = scanModule.FrameDataGrab(14, 1)                      # 14 = z., 18 is Freq. shift
            pngFilename = self.makePNG(scanData, filePath)                      # Generate a png from the scan data
            GIF.append(scanData)
            
            self.interface.sendPNG(pngFilename,notify=False,message=message)    # Send a png over zulip
            
        time.sleep(0.25)
        scanModule.PropsSet(series_name=basename)                               # Put back the original basename
        
        # self.interface.sendPNG(utilities.makeGif(GIF),notify=False,message=message)
        
        self.interface.sendReply("biasDep " + suffix + " complete.")
        
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
        dx  = scanFrame[2]/dcpx; dy  = scanFrame[3]/dclx
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
        
        GIF = []
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
            GIF.append(scanData)
            
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
# Tip Actions
###############################################################################
    def moveArea(self,up,upV,upF,direction,steps,dirV,dirF,zon,approach=True,message=""):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
        
        # Safety checks
        if(up < 10):
            self.disconnect(NTCP)
            self.interface.sendReply("-up must be > 10",message=message)
            return False
        
        if(upV > self.zMaxV):
            upV = self.zMaxV
            # self.disconnect(NTCP)
            # self.interface.sendReply("-upV 300 V max",message=message)
            # return False
        
        if(upF > self.zMaxF):
            upF = self.zMaxF
            # self.disconnect(NTCP)
            # self.interface.sendReply("-upF 2.5 kHz max",message=message)
            # return False
        
        if(dirV > self.xyMaxV):
            dirV = self.xyMaxV
            # self.disconnect(NTCP)
            # self.interface.sendReply("-dirV 200 V max",message=message)
            # return False
        
        if(dirF > self.xyMaxF):
            dirF = self.xyMaxF
            # self.disconnect(NTCP)
            # self.interface.sendReply("-dirF 2.5 kHz max",message=message)
            # return False
        
        if(upV < self.zMinV):
            upV = self.zMinV
            # self.disconnect(NTCP)                                               # Close the TCP connection
            # self.interface.sendReply("-upV must be between 1 V and 200 V",message=message)
            # return False
            
        if(upF < self.zMinF):
            upF = self.zMinF
            # self.disconnect(NTCP)                                               # Close the TCP connection
            # self.interface.sendReply("-upF must be between 500 Hz and 2.5 kHz",message=message)
            # return False
        
        if(dirV < self.xyMinV):
            dirV = self.xyMinV
            # self.disconnect(NTCP)                                               # Close the TCP connection
            # self.interface.sendReply("-upV must be between 1 V and 200 V",message=message)
            # return False
            
        if(dirF < self.xyMinF):
            dirF = self.xyMinF
            # self.disconnect(NTCP)                                               # Close the TCP connection
            # self.interface.sendReply("-upF must be between 500 Hz and 2.5 kHz",message=message)
            # return False
        
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
                                         + str(self.safeCurrent*1e9) + " nA"
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
                                     + str(self.safeCurrent*1e9) + " nA"
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
    
    def moveTip(self,lightOnOff,cameraPort,trackOnly,xStep,zStep,xV,zV,xF,zF,demo,roi=[],target=[],tipPos=[],win=15,iamauto=False):
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
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error):
            global_.running.clear()                                             # Free up the running flag
            return connection_error                                             # Return error message if there was a problem connecting
        
        if(lightOnOff):                                                         # If we want to turn the light on
            try:
                from hk_light import turn_on
                turn_on()                                                       # Call the hook to do so. Hook should return null if successful, otherwise it should throw an Exception
            except Exception as e:
                self.interface.sendReply("Error calling hook hk_light.py to turn on light")
                self.disconnect(NTCP)
                global_.running.clear()                                         # Free up the running flag
                return str(e)
        
        cap = utilities.getVideo(cameraPort,demo)
        ret,frame = utilities.getAveragedFrame(cap,n=1)                         # Read the first frame of the video to test camera feed
        if(not ret):
            self.interface.sendReply("Error finding camera feed. Check camera port.")
            self.disconnect(NTCP)
            global_.running.clear()                                             # Free up the running flag
            cap.release()
            cv2.destroyAllWindows()
            return
        
        if(not len(roi)):                                                       # Don't do this if we're passing in an ROI already
            self.autoInitSet = False                                            # If an roi hasn't been passed in, it means this was called directly by user and the auto_init will need to be redone
            ret,frame = utilities.getAveragedFrame(cap,n=1)                     # Read the first frame of the video
            
            self.interface.sendReply("Select tracking ROI. Press 'q' to cancel")
            roi = utilities.getROI(cap)
            if(not len(roi)):
                self.interface.sendReply("Cancelling move tip")
                self.disconnect(NTCP)
                global_.running.clear()                                         # Free up the running flag
                cap.release()
                cv2.destroyAllWindows()
                return
                
            self.interface.sendReply("Select a marker for the tip location. Press 'q' to cancel")
            tipPos = utilities.markPoint(cap)
        
        if(len(tipPos) and not len(target) and not trackOnly):
            ret,frame = utilities.getAveragedFrame(cap,n=1)                     # Read the first frame of the video
            
            self.interface.sendReply("Select target location for the tip. Press 'q' to cancel and enter track-only mode")
            target = utilities.markPoint(cap)
            
        if(len(target)):
            target = target - tipPos
            if(target[1] > 0 and not iamauto):
                self.interface.sendReply("Error: cannot move tip lower than current position. Track-Only mode activated")
                target = []
        
        if(not len(target)): trackOnly = True
        
        ROI = utilities.extract(frame,roi)
        WIN = utilities.extract(frame,roi,win)
        
        tipToROI = tipPos - roi[0:2]
        
        print("withdrawing")
        zController = ZController(NTCP)
        zController.Withdraw(wait_until_finished=True,timeout=3)                # Withdwar the tip
        print("withdrew")
        time.sleep(0.25)
        
        success = True
        targetHit = False
        xy  = np.array([0,0])
        oxy = np.array([0,0])
        currentPos = np.array([0,0])
        while(cap.isOpened()):
            if(not success):
                self.interface.sendReply("Error moving area... tip crashed... stopping")
                global_.running.clear()
                break
            
            ret, frame = utilities.getAveragedFrame(cap,n=11)
            if(not ret): break
        
            oxy = utilities.trackROI(im1=ROI, im2=WIN)
            
            currentPos = xy + oxy
            
            ROI,WIN,roi,xy = utilities.update(roi,ROI,win,frame,oxy,xy)
            
            rec = utilities.drawRec(frame.astype(np.uint8), roi, xy=oxy)
            rec = utilities.drawRec(rec, roi, win=win)
            
            if(len(tipPos)): rec = cv2.circle(rec, currentPos + tipPos, radius=3, color=(0, 0, 255), thickness=-1)
            if(len(target)): rec = cv2.circle(rec, target + tipPos, radius=3, color=(0, 255, 0), thickness=-1)
            
            cv2.imshow('Frame',rec)
            
            if cv2.waitKey(25) & 0xFF == ord('q'): break                        # Press Q on keyboard to  exit
            if(self.checkEventFlags()): break                                   # Check event flags
            
            if(trackOnly): continue
            
            if(currentPos[1] > target[1]):                                      # First priority is to always keep the tip above this line
                if(demo): continue
                success = self.moveArea(up=zStep, upV=zV, upF=zF, direction="X+", steps=0, dirV=xV, dirF=xF, zon=False, approach=False)
                continue
            if(currentPos[0] < target[0]):
                if(demo): continue
                success = self.moveArea(up=10, upV=zV, upF=zF, direction="X+", steps=xStep, dirV=xV, dirF=xF, zon=False, approach=False)
                continue
            if(currentPos[0] > target[0]):
                if(demo): continue
                success = self.moveArea(up=10, upV=zV, upF=zF, direction="X-", steps=xStep, dirV=xV, dirF=xF, zon=False, approach=False)
                continue
            
            targetHit = True
            self.interface.sendReply("Target Hit!")
            break                                                               # Target reached!
        
        cap.release()
        cv2.destroyAllWindows()
        
        if(iamauto):
            tipToROI = tipPos - roi[0:2]
            self.roi[0:2] = tipPos - tipToROI
            self.tipPos = currentPos + tipPos
        
        if(lightOnOff):                                                         # If we want to turn the light off
            try:
                from hk_light import turn_off
                turn_off()                                                      # Call the hook to do so. Hook should return null if successful, otherwise it should throw an Exception
            except Exception as e:
                self.interface.sendReply("Error calling hook hk_light.py to turn light off")
                self.disconnect(NTCP)
                global_.running.clear()                                         # Free up the running flag
                return str(e)
            
        self.disconnect(NTCP)                                                   # Close the TCP connection
        
        if(targetHit and iamauto): return "Target Hit"                          # Keep the running flag going because we might be approaching after this.
        
        global_.running.clear()                                                 # Free up the running flag
        
        return
        
    def tipShape(self):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting
        
        tipShaper = TipShaper(NTCP)
        
        try:
            tipShaper.Start(wait_until_finished=True,timeout=-1)
        except Exception as e:
            self.interface.sendReply(str(e))
        
        self.disconnect(NTCP)
        self.interface.reactToMessage("dagger")
        
    def tipShapeProps(self,sod,cb,b1,z1,t1,b2,t2,z3,t3,wait,fb):
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
        if(z3 < -50e-9):
            self.interface.sendReply("Limit for z3=-50e-9 m")
            self.disconnect(NTCP)
            return
        
        if(z1 > 0):
            self.interface.sendReply("Sure you want a positive z1?")
            
        if(z3 < 0):
            self.interface.sendReply("Sure you want a negative z3?")
            
        tipShaper.PropsSet(*tipShaperArgs)                                      # update the tip shaping params in nanonis
        
        self.disconnect(NTCP)
        self.interface.reactToMessage("+1")
        
###############################################################################
# Auto STM
###############################################################################
    def autoInit(self,lightOnOff,cameraPort,demo,win=15,message=""):
        if(lightOnOff):                                                         # If we want to turn the light on
            try:
                from hk_light import turn_on
                turn_on()                                                       # Call the hook to do so. Hook should return null if successful, otherwise it should throw an Exception
            except Exception as e:
                self.interface.sendReply("Error calling hook hk_light.py to turn on the light")
                global_.running.clear()                                         # Free up the running flag
                return str(e)
        
        cap = utilities.getVideo(cameraPort,demo)
        
        ret,frame = utilities.getAveragedFrame(cap,n=1)                         # Read the first frame of the video
        if(not ret):
            self.interface.sendReply("Error finding camera feed. Check camera port.")
            global_.running.clear()                                             # Free up the running flag
            cap.release()
            cv2.destroyAllWindows()
            return
        
        self.interface.sendReply("Select tracking ROI. Press 'q' to cancel")
        roi = utilities.getROI(cap)
        if(not len(roi)):
            self.interface.sendReply("Cancelling...")
            global_.running.clear()                                             # Free up the running flag
            cap.release()
            cv2.destroyAllWindows()
            return
            
        self.interface.sendReply("Place a marker at the tip location. Press 'q' to cancel")
        tipPos = utilities.markPoint(cap,windowName="Mark tip location")
        if(not len(tipPos)):
            self.interface.sendReply("Cancelling...")
            global_.running.clear()                                             # Free up the running flag
            cap.release()
            cv2.destroyAllWindows()
            return
        
        self.interface.sendReply("Place a marker at a safe height above the clean metal. Press 'q' to cancel")
        cleanMetalPos = utilities.markPoint(cap,windowName="Mark clean metal location")
        if(not len(cleanMetalPos)):
            self.interface.sendReply("Cancelling...")
            global_.running.clear()                                             # Free up the running flag
            cap.release()
            cv2.destroyAllWindows()
            return
        
        self.interface.sendReply("Place a marker at a safe height above the sample. Press 'q' to cancel")
        samplePos = utilities.markPoint(cap,windowName="Mark sample location")
        if(not len(samplePos)):
            self.interface.sendReply("Cancelling...")
            global_.running.clear()                                             # Free up the running flag
            cap.release()
            cv2.destroyAllWindows()
            return
        
        ret, frame = utilities.getAveragedFrame(cap,n=11)
        if(not ret):
            self.interface.sendReply("Problem with camera feed")
            global_.running.clear()                                             # Free up the running flag
            cap.release()
            cv2.destroyAllWindows()
            return
        
        rec = utilities.drawRec(frame.astype(np.uint8), roi)
        rec = utilities.drawRec(rec, roi, win=win)
            
        rec = cv2.circle(rec, tipPos, radius=3, color=(0, 0, 255), thickness=-1)
        rec = cv2.circle(rec, samplePos, radius=3, color=(0, 255, 0), thickness=-1)
        rec = cv2.circle(rec, cleanMetalPos, radius=3, color=(0, 255, 0), thickness=-1)
            
        cv2.imshow('Frame',rec)
        
        self.interface.sendReply("Initialisation complete! If this doens't look correct, run it again.")
        self.interface.sendReply("Press 'q' to exit (timeout = 30s)")
        
        timeout = 0
        while(timeout < 30):
            if cv2.waitKey(25) & 0xFF == ord('q'): break                        # Press Q on keyboard to  exit
            time.sleep(1)
            timeout += 1
            
        cap.release()
        cv2.destroyAllWindows()
        
        self.autoInitSet    = True
        self.roi            = roi
        self.tipPos         = tipPos
        self.samplePos      = samplePos
        self.cleanMetalPos  = cleanMetalPos
        
        self.interface.sendReply("Done")
        
        if(lightOnOff):                                                         # If we want to turn the light on
            try:
                from hk_light import turn_off
                turn_off()                                                      # Call the hook to do so. Hook should return null if successful, otherwise it should throw an Exception
            except Exception as e:
                self.interface.sendReply("Error calling hook hk_light.py to turn off the light.")
                global_.running.clear()                                         # Free up the running flag
                return str(e)
            
        global_.running.clear()                                                 # Free up the running flag
        return
    
    def moveTipToTarget(self,lightOnOff, cameraPort, xStep, zStep, xV, zV, xF, zF, approach, demo, tipshape, retrn, run, target):
        if(not self.autoInitSet):
            self.interface.sendReply("Error, run the auto_init command to initialise tip, sample, and clean metal locations")
            global_.running.clear()                                             # Free up the running flag
            return
        
        trackOnly = 0
        if(target == "sample"):  targetPos = self.samplePos.copy()
        elif(target == "clean"): targetPos = self.cleanMetalPos.copy()
        
        targetHit = self.moveTip(lightOnOff, cameraPort, trackOnly, xStep, zStep, xV, zV, xF, zF, demo,roi=self.roi.copy(),target=targetPos,tipPos=self.tipPos.copy(),iamauto=True)
        
        if(not targetHit == "Target Hit"): return
        
        if(not approach == 1): return
        
        self.moveArea(up=10, upV=zV, upF=zF, direction="X+", steps=0, dirV=xV, dirF=xF, zon=True) # Approach
        
        message = ""
        if(target == "clean" and tipshape == 1):
            message = self.autoTipShape(n=-1, wh=10e-9, symTarget=0.9, sizeTarget=2.5, zQA=-85e-11, ztip=-2.5e-9, sleepTime=1, iamauto=True)
            if(not message): message = ""
        
        if(not "Tip shaping successful" in message):
            global_.running.clear()                                             # Free up the running flag
            return
            
        if(not retrn == 1): return
        
        targetPos = self.samplePos.copy()
        targetHit = self.moveTip(lightOnOff, cameraPort, trackOnly, xStep, zStep, xV, zV, xF, zF, demo,roi=self.roi.copy(),target=targetPos,tipPos=self.tipPos.copy(),iamauto=True)
        
        if(not targetHit == "Target Hit"): return
        
        self.moveArea(up=10, upV=zV, upF=zF, direction="X+", steps=0, dirV=xV, dirF=xF, zon=True) # Approach
        
        global_.running.clear()                                                 # Free up the running flag
        
        if(not run in ["survey","survey2"]):
            self.interface.sendReply("Error running " + run + ". -run must be one of 'survey' or 'survey2'")
            return
        
        if(run == "survey"):
            self.interface.survey(user_args=[],_help=False,surveyParams=self.surveyParams)
            return
                
        if(run == "survey2"):
            self.survey2(user_args=[],_help=False,surveyParams=self.survey2Params)
            return
        
    def autoTipShape(self,n,wh,symTarget,sizeTarget,zQA,ztip,sleepTime,tipShape_hk,message="",iamauto=False):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error):
            global_.running.clear()                                             # Free up the running flag
            return connection_error                                             # Return error message if there was a problem connecting        
        
        scanModule  = Scan(NTCP)
        folme       = FolMe(NTCP)
        tipShaper   = TipShaper(NTCP)
        
        try:
            tipShapeProps = tipShaper.PropsGet()                                # Use the default tip shaping properties to begin with
        except Exception as e:                                                  # If this fails, the tip shaper module isn't open. Nanonis does not support opening the tip shaper module using TCP interface
            global_.running.clear()                                             # Free up the running flag
            self.disconnect(NTCP)                                               # Close the TCP connection
            self.interface.sendReply(str(e))                                    # Inform the user
            return
        
        if(zQA > 0 or ztip > 0):
            global_.running.clear()                                             # Free up the running flag
            self.disconnect(NTCP)                                               # Close the TCP connection
            self.interface.sendReply("Tip lifts -zQA and -ztip must be < 0")
            return
        
        tipShapeProps[10]   = 1                                                 # Make sure feedback on after tip shape
        tipShapeProps[3]   = ztip                                               # Amount to dip the tip into the surface
        tipShapeProps[7]    = -3*ztip                                           # Amount to withdraw the tip from the surface
        
        tipCheckerProps     = tipShaper.PropsGet()                              # These will be the tip shaper properties used to perform a light tip-shaping action which is scanned over to assess tip quality
        tipCheckerProps[1]  = 1                                                 # Turn on the change bias checkbox
        tipCheckerProps[2]  = 0.1                                               # Bias to change to before tip shaping
        tipCheckerProps[3]  = zQA                                               # Set initial tip lift
        tipCheckerProps[4]  = 0.1                                               # Duration of tip lift
        tipCheckerProps[5]  = 0                                                 # Bias applied while tip is in surface
        tipCheckerProps[6]  = 0.1                                               # Amount of time tip is in surface
        tipCheckerProps[7]  = -3*zQA                                            # Tip lift 2
        tipCheckerProps[8]  = 0.1                                               # Duration of tip lift 2
        tipCheckerProps[9]  = 0.1                                               # Time to wait before putting bias back
        tipCheckerProps[10] = 1                                                 # Turn feedback on after tip shape
        
        suffix = "sb-auto-tip"
        basename = self.interface.topoBasename                                  # Get the basename that's been set in config file
        if(not basename): basename = scanModule.PropsGet()[3]                   # Get the save basename from nanonis if one isn't supplied
        tempBasename = basename + '_' + suffix + '_'                            # Create a temp basename for this run
        scanModule.PropsSet(series_name=tempBasename)                           # Set the basename in nanonis
        
        attempt = 0                                                             # Keep track of number of attempts to tip shape
        tipQA   = False                                                         # Temp flag
        xy = np.array([0,0])
        while(attempt < n or n==-1):
            scanModule.FrameSet(*xy, w=wh, h=wh)
            
            scanModule.Action(scan_action="start",scan_direction="up")          # Start an upward scan
            for numSeconds in range(sleepTime):                                 # Sleep at one second intervals so we can still stop the routine without lag if we need to
                time.sleep(1)
                if(self.checkEventFlags()): break                               # Check event flags
            if(self.checkEventFlags()): break                                   # Check event flags
                
            scanModule.Action(scan_action="start",scan_direction="up")          # Restart an upward scan, hopefully image is less drifty now
            
            isClean  = True
            timedOut = True
            while(timedOut and isClean):                                        # Periodically check if the current scan is of a clean region
                timedOut, _, filePath = scanModule.WaitEndOfScan(timeout=3000)  # Wait until the scan finishes or 3 sec, whichever occurs first
                _,cleanImage,_ = scanModule.FrameDataGrab(14, 1)                # Image of the 'clean' surface
                isClean = utilities.isClean(cleanImage,lxy=wh,threshold=0.3e-9,sensitivity=1) # Check if the scan so far is of a clean area
            
            cleanImage = np.flipud(cleanImage)                                  # Flip because the scan direction is up
            if(not isClean):
                scanModule.Action(scan_action='stop')
                xy = xy + np.array([2*wh,0])                                    # Move the scan frame
                self.interface.sendReply("Bad area, moving scan frame")
                continue                                                        # Don't count the attempt if the area sucks
                
            if(not filePath): break                                             # If the scan was stopped before finishing, stop program
            
            tipCheckPos = utilities.getCleanCoordinate(cleanImage, lxy=wh)      # Do some processing to find a clean location to assess tip quality
            if(not len(tipCheckPos)):                                           # If no coordinate is returned because the area is bad...
                xy = xy + np.array([2*wh,0])                                    # Move the scan frame
                continue                                                        # Don't count the attempt if the area sucks
            
            tipCheckPos += xy                                                   # Convert frame-relative coordinate to absolute coordinate
            folme.XYPosSet(*tipCheckPos,Wait_end_of_move=True)                  # Move the tip to a clean place
            
            self.tipShapeProps(*tipCheckerProps)                                # Set the tip shaping properties up for the very light action
            time.sleep(1)
            if(self.checkEventFlags()): break                                   # Check event flags
            self.tipShape()                                                     # Execute the light tip shape
            time.sleep(1)
            if(self.checkEventFlags()): break                                   # Check event flags
            
            scanModule.Action(scan_action="start",scan_direction="up")          # Start an upward scan
            _, _, filePath = scanModule.WaitEndOfScan()                         # Wait until the scan finishes
            if(not filePath): break                                             # If the scan was stopped before finishing, stop program
            _,tipImprint,_ = scanModule.FrameDataGrab(14, 1)                    # Image of the tip's crater after very light tip shape action
            cleanImage = np.flipud(cleanImage)                                  # Flip because the scan direction is up
            
            # Probably do something here to periodically check scan area (as
            # above) in case the tip blew up and left the area a mess.
            
            tipCheckPos -= xy                                                   # Convert absolute coodinate to frame-relative coordinate
            symmetry,size = utilities.assessTip(tipImprint,wh,tipCheckPos)      # Assess the quality of the tip based on the imprint it leaves on the surface
            
            # if(size < 0): contour not found, do something about that.
            
            if(symmetry > symTarget):
                if(size < sizeTarget and size > 0):
                    tipQA = True                                                # Tip quality is good if it meets the target scores
                    break                                                       # Stop the routine if a good tip has been achieved
            
            edgeOfFrame = xy - np.array([wh,0])/2
            folme.XYPosSet(*edgeOfFrame,Wait_end_of_move=True)                  # Move the tip to the left edge of the scan frame
            
            if(tipShape_hk):
                try:
                    import hk_tipShape
                    temp_tipShapeProps = hk_tipShape.run(cleanImage,tipImprint,tipShapeProps.copy(),size,symmetry)
                    if(not type(temp_tipShapeProps) == type(None)):
                        if(not len(temp_tipShapeProps) == len(tipShapeProps)):
                            self.interface.sendReply("Warning: tipShapeProps returned from hk_tipShape.py does not contain expected number of parameters. See documentation for nanonisTCP.TipShaper. This will probably cause an error.")
                        tipShapeProps = temp_tipShapeProps
                except Exception as e:
                    self.interface.sendReply("Error calling hk_tipShape...")
                    self.interface.sendReply(str(e))
            
            self.tipShapeProps(*tipShapeProps)                                  # Set the tip shaping properties up to change the tip
            time.sleep(1)
            if(self.checkEventFlags()): break                                   # Check event flags
            self.tipShape()                                                     # Execute the tip shape
            time.sleep(1)
            if(self.checkEventFlags()): break                                   # Check event flags
            
            xy = xy + np.array([2*wh,0])                                        # Move the scan frame
            attempt += 1
            
        scanModule.PropsSet(series_name=basename)                               # Put back the original basename
        
        self.tipShapeProps(*tipShapeProps)                                      # Put back the original tip shaping properties
        
        message = "Tip shaping failed"
        if(tipQA): message = "Tip shaping successful"
        self.interface.sendReply(message + " after " + str(attempt+1) + " attempts")
        
        self.disconnect(NTCP)                                                   # Close the TCP connection
        
        if(iamauto): return message                                             # Don't clear the running flag if called by iamauto
        
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
# Misc
###############################################################################
    def stop(self):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
        
        scan = Scan(NTCP)                                                       # Nanonis scan module
        scan.Action('stop')                                                     # Stop the current scan
        
        self.disconnect(NTCP)                                                   # Close the NTCP connection
        
###############################################################################
# Utilities
###############################################################################
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
        
        return getStr
    
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
        threshold = self.safeCurrent                                            # Threshold current from safety params
        
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
        
        motor.FreqAmpSet(self.safeRetractF,self.safeRetractV)                   # Set the motor frequency/voltage in the nanonis motor control module
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