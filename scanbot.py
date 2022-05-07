# -*- coding: utf-8 -*-
"""
Created on Fri May  6 15:38:34 2022

@author: jced0001
"""

from nanonisTCP import nanonisTCP
from nanonisTCP.Scan import Scan

import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import nanonispyfit as nap

import time
import ntpath                                                                   # os.path but for windows paths

import global_

class Scanbot():
###############################################################################
# Constructor
###############################################################################
    def __init__(self,interface):
        self.interface = interface
        
###############################################################################
# Actions
###############################################################################
    def plot(self,args):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
        
        scan = Scan(NTCP)                                                       # Nanonis scan module
        _,scanData,scanDirection = scan.FrameDataGrab(14, 1)                    # Grab the data within the scan frame. Channel 14 is . 1 is forward data direction
        
        pngFilename = self.makePNG(scanData, scanDirection)                     # Generate a png from the scan data
        self.interface.sendPNG(pngFilename)                                     # Send a png over zulip
        
        self.disconnect(NTCP)                                                   # Close the TCP connection
        return ""
    
    def stop(self,args):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
                                                                                # Defaults args...
        arg_dict = {'-safe'  : '0'}                                             # -safe means safe mode... withdraw tip etc. (not implemented yet)
        
        for arg in args:                                                        # Override the defaults if user inputs them
            key,value = arg.split('=')
            if(not key in arg_dict):
                self.disconnect(NTCP)                                           # Close the connection and 
                return "invalid argument: " + arg                               # return error message
            arg_dict[key] = value     
        
        scan = Scan(NTCP)                                                       # Nanonis scan module
        scan.Action('stop')                                                     # Stop the current scan
        
        self.disconnect(NTCP)                                                   # Close the NTCP connection
        return ("Stopped!")
    
    def survey(self,args):
        NTCP,connection_error = self.connect()                                  # Connect to nanonis via TCP
        if(connection_error): return connection_error                           # Return error message if there was a problem connecting        
                                                                                # Defaults args...
        arg_dict = {'-n'  : '5',                                                # size of the nxn grid of scans
                    '-s'  : 'scanbot',                                          # suffix at the end of autosaved sxm files
                    '-xy' : '100e-9',                                           # length and width of the scan frame (square)
                    '-dx' : '150e-9',                                           # spacing between scans
                    '-oxy': '0,0',                                              # Origin (centre of grid)
                    '-st' : '0.5 '}                                             # Sleep time before restarting scan to correct for drift
        
        for arg in args:                                                        # Override the defaults if user inputs them
            key,value = arg.split('=')
            if(not key in arg_dict):
                self.disconnect(NTCP)                                           # Close the connection and 
                return "invalid argument: " + arg                               # return error message
            arg_dict[key] = value                    
        
        self.survey_args = arg_dict.copy()                                      # Store these params for enhance to look at
        
        scan = Scan(NTCP)                                                       # Nanonis scan module
        
        basename     = scan.PropsGet()[3]                                       # Get the save basename
        tempBasename = basename + '_' + arg_dict['-s'] + '_'                    # Create a temp basename for this survey
        scan.PropsSet(series_name=tempBasename)                                 # Set the basename in nanonis for this survey
        
        n  = int(arg_dict['-n'])                                                # size of nxn grid of scans
        dx = float(arg_dict['-dx'])                                             # Scan spacing
        xy = float(arg_dict['-xy'])                                             # Scan size (square)
        ox = float(arg_dict['-oxy'].split(',')[0])                              # Origin of grid
        oy = float(arg_dict['-oxy'].split(',')[1])                              # Origin of grid
        
        frames = []                                                             # [x,y,w,h,angle=0]
        for ii in range(int(-n/2),int(n/2) + n%2):
            for jj in range(int(-n/2),int(n/2) + n%2):
                if(not ii%2): frames.append([ jj*dx+ox, ii*dx+oy, xy, xy])      # for even ii, go in the forwards direction of jj
                if(ii%2):     frames.append([-jj*dx+ox, ii*dx+oy, xy, xy])      # for odd ii, go in the reverse direction of jj.
                                                                                # Alternate jj direction so the grid snakes which is better for drift
        sleepTime = float(arg_dict['-st'])                                      # Time to sleep before restarting scan to reduce drift
        for frame in frames:
            self.interface.sendReply('running scan' + str(frame))               # Send a message that the next scan is starting
            
            scan.FrameSet(*frame)                                               # Set the coordinates and size of the frame window in nanonis
            scan.Action('start')                                                # Start the scan. default direction is "up"
            if(self.checkEventFlags()): break                                   # Check event flags
            
            time.sleep(sleepTime)                                               # Wait 10s for drift to settle
            if(self.checkEventFlags()): break
        
            scan.Action('start')                                                # Start the scan again after waiting for drift to settle
            timeoutStatus, _, filePath = scan.WaitEndOfScan()                   # Wait until the scan finishes
            
            _,scanData,scanDirection = scan.FrameDataGrab(14, 1)                # Grab the data within the scan frame. Channel 14 is . 1 is forward data direction
            
            if timeoutStatus: filePath = ''                                     # If the timeout status indicates scan did not finish, there's no file to save
            
            pngFilename = self.makePNG(scanData, scanDirection, filePath)       # Generate a png from the scan data
            self.interface.sendPNG(pngFilename)                                 # Send a png over zulip
        
        scan.PropsSet(series_name=basename)                                     # Put back the original basename
        self.disconnect(NTCP)                                                   # Close the TCP connection
        
        global_.running.clear()                                                 # Free up the running flag
        
        self.interface.sendReply('survey \'' + arg_dict['-s'] + '\' done')      # Send a notification that the survey has completed
    
    def enhance(self,args):
                                                                                # Defaults args...
        arg_dict = {'-i'  : '1',                                                # Index of the frame in the last survey to enhance
                    '-n'  : '2',                                                # size of the nxn grid of scans
                    '-s'  : 'enhance',                                          # suffix at the end of autosaved sxm files
                    '-xy' : '0',                                                # length and width of the scan frame (square)
                    '-dx' : '0'}                                                # spacing between scans
        
        for arg in args:                                                        # Override the defaults if user inputs them
            key,value = arg.split('=')
            if(not key in arg_dict):
                return "invalid argument: " + arg                               # return error message
            arg_dict[key] = value                    
        
        i = int(arg_dict['-i'])
        n = int(self.survey_args['-n'])
        
        count = 0
        for ii in range(int(-n/2),int(n/2) + n%2):
            for jj in range(int(-n/2),int(n/2) + n%2):
                count += 1
                if(count == i): break
            if(count == i): break
        
        ox = float(self.survey_args['-oxy'].split(',')[0])                      # Origin of grid
        oy = float(self.survey_args['-oxy'].split(',')[1])                      # Origin of grid
        dx = float(self.survey_args['-dx'])
        if(not ii%2): ox,oy =  jj*dx+ox, ii*dx+oy
        if(    ii%2): ox,oy = -jj*dx+ox, ii*dx+oy
        oxy = str(ox) + ',' + str(oy)
        
        n  = int(arg_dict['-n'])
        xy = float(arg_dict['-xy'])
        dx = float(arg_dict['-dx'])
        
        if(xy == 0): xy = float(self.survey_args['-xy'])/n
        if(dx == 0): dx = xy
        
        survey_args = []
        survey_args.append('-n='   + str(n))
        survey_args.append('-s='   + 'enhance')
        survey_args.append('-xy='  + str(xy))
        survey_args.append('-dx='  + str(dx))
        survey_args.append('-oxy=' + oxy)
        
        self.survey(survey_args)
        
###############################################################################
# Utilities
###############################################################################
    def makePNG(self,scanData,scanDirection,filePath=''):
        fig, ax = plt.subplots(1,1)
        
        if scanDirection == 'up':
            scanData = np.flipud(scanData)                                      # Flip the scan if it's taken from the bottom up
            
        mask = np.isnan(scanData)                                               # Mask the Nan's
        scanData[mask == True] = np.nanmean(scanData)                           # Replace the Nan's with the mean so it doesn't affect the plane fit
        scanData = nap.plane_fit_2d(scanData)                                   # Flattern the image
        vmin, vmax = nap.filter_sigma(scanData)                                 # cmap saturation
        
        ax.imshow(scanData, origin='lower', cmap='Blues_r', vmin=vmin, vmax=vmax) # Plot
        ax.axis('off')
        
        pngFilename = 'im.png'
        if filePath: pngFilename = ntpath.split(filePath)[1] + '.png'
        
        fig.savefig(pngFilename, dpi=60, bbox_inches='tight', pad_inches=0)
        plt.close('all')
        
        return pngFilename
        
    def checkEventFlags(self):
        if(not global_.running.is_set()): return 1                              # Running flag
        while global_.pause.is_set(): time.sleep(2)                             # Pause flag
    
###############################################################################
# Nanonis TCP Connection
###############################################################################
    def connect(self):
        try:                                                                    # Try to connect to nanonis via TCP
            IP   = self.interface.IP
            PORT = self.interface.portList.pop()
            NTCP = nanonisTCP(IP, PORT)
            return [NTCP,0]
        except Exception as e:
            if(len(self.interface.portList)): return [0,str(e)]                 # If there are ports available then return the exception message
            return [0,"No ports available"]                                     # If no ports are available send this message
    
    def disconnect(self,NTCP):
        NTCP.close_connection()                                                 # Close the TCP connection
        self.interface.portList.append(NTCP.PORT)                               # Free up the port - put it back in the list of available ports