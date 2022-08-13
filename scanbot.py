# -*- coding: utf-8 -*-
"""
Created on Fri August 8 22:06:52 2022

@author: Julian Ceddia
"""

from nanonisTCP import nanonisTCP
from nanonisTCP.Scan import Scan
from nanonisTCP.Signals import Signals

import time
import ntpath
import numpy as np
import nanonispyfit as nap
import matplotlib.pyplot as plt

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
            pngFilename = 'im-c' + str(channel) + '.png'                            # All unsaved (incomplete) scans are saved as im.png
            pngFilename = self.makePNG(scanData,pngFilename=pngFilename)            # Generate a png from the scan data
            self.interface.sendPNG(pngFilename,notify=False)                        # Send a png over zulip
        except:
            self.interface.reactToMessage("cross_mark")
        
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
        if(c != -1 and not c in channels):  self.disconnect(NTCP); return "Invalid signal -c=" + str(c) + " is not in the buffer\n" + helpStr
        if(a != -1 and not a in range(24)): self.disconnect(NTCP); return "Invalid signal -a=" + str(a) + "\n" + helpStr
        if(a != -1 and a in channels):      self.disconnect(NTCP); return "-a=" + str(a) + " is already in the buffer\n" + helpStr
        if(r != -1 and not r in channels):  self.disconnect(NTCP); return "-r=" + str(r) + " is not in the buffer\n" + helpStr
        if(r == self.channel):              self.disconnect(NTCP); return "-r=" + str(r) + " cannot be removed while selected\n" + helpStr
        
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