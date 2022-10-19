# -*- coding: utf-8 -*-
"""
Created on Thu Aug 18 10:35:50 2022

@author: Julian
"""

import ntpath
import pickle
import math
import numpy as np
import scipy.signal as sp

def pklDict(scanData,filePath,x,y,w,h,angle,pixels,lines,comments=""):
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
    
    pickle.dump(pklDict, open(filename + ".pkl", 'wb'))                         # Pickle containing config settings and unlabelled data
    return filename + ".pkl"

###############################################################################
# Drift Correction - gets the real-space offset between two frames
###############################################################################
def getFrameOffset(im1,im2,dxy=[1,1],theta=0):
    """
    Returns the offset of im2 relative to im1. im1 and im2 must be the same
    size and scale. Keep dxy=[1,1] to return offset in units of pixels.
    When using with nanonis to detect drift, take the current scan frame 
    position and subtract ox,oy from it. i.e.: center_x -= ox; center_y -= oy

    Parameters
    ----------
    im1 : image to compare against
    im2 : image to get the offset of
    dxy : pixel size in x and y: [dx,dy]
    theta : angle in degrees

    Returns
    -------
    [ox,oy] : offset in x and y

    """
    im1_diff = np.diff(im1,axis=0)                                              # Differentiate along x
    im2_diff = np.diff(im2,axis=0)                                              # Differentiate along x
        
    xcor = sp.correlate2d(im1_diff,im2_diff, boundary='symm', mode='same')
    y,x  = np.unravel_index(xcor.argmax(), xcor.shape)

    ni = np.array(xcor.shape)
    oy,ox = np.array([y,x]).astype(int) - (ni/2).astype(int)
    
    ox += x%2                                                                   # Add in this offset because differentiating results in odd number of px 
    
    ox *= dxy[0]
    oy *= -dxy[1]
    
    theta *= math.pi/180                                                        # Convert to radians
    R = np.array([[math.cos(theta)**2,math.sin(theta)**2],                      # Rotation matrix to account for angle of scan frame
                  [math.sin(theta)**2,math.cos(theta)**2]])
    
    ox,oy = np.matmul(R,np.array([ox,oy]).T)                                    # Account for angle of scan frame
    
    return np.array([ox,oy])

###############################################################################
# Make gif
###############################################################################
def makeGif(data):
    """
    To Do: pass in list of images and turn them into a gif

    Parameters
    ----------
    data : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    pass