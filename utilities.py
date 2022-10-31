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
import nanonispyfit as napfit
import cv2

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
    ox,oy = rotate([0,0],[ox,oy],theta)
    
    return np.array([ox,oy])

def rotate(origin, point, angle):
    """
    Taken from:
    https://stackoverflow.com/questions/34372480/rotate-point-about-another-point-in-degrees-python
    Rotate a point counterclockwise by a given angle around a given origin.

    The angle should be given in radians.
    """
    ox, oy = origin
    px, py = point

    qx = ox + math.cos(angle) * (px - ox) - math.sin(angle) * (py - oy)
    qy = oy + math.sin(angle) * (px - ox) + math.cos(angle) * (py - oy)
    return qx, qy
###############################################################################
# Make gif
###############################################################################
def makeGif(GIF):
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
###############################################################################
# Make gif
###############################################################################
def classify(data,tipChanges=True,sharpness=False,closeDouble=False,longDouble=False):
    """
    This checks a raw scan for the following:

    Parameters
    ----------
    scanData    : Raw scan data
    tipChanges  : Look for tip changes.
    sharpness   : Quantify sharpness.
    closeDouble : Look for double tip (close range)
    longDouble  : Look for double tip (long range)

    Returns
    -------
    dict:
    "tipChanges"   : number of detected tip changes
    "sharpness"    : a sharpness score from zero to 10  (not implemented yet)
    "closeDouble"  : 0 = not doubled. 1 = doubled       (not implemented yet)
    "longDouble"   : 0 = not doubled. 1 = doubled       (not implemented yet)
    "nan"          : data passed in contains NANs

    """
    nan = np.isnan(data).any()                                                  # Flag to say there are nans in data which might affect  analysis
    scanData = np.nan_to_num(data)
    tipChangeCount = findTipChanges(scanData.copy())

    return {"tipChanges" : tipChangeCount,
            "nan"        : nan}

def findTipChanges(scanData):
    scanData = np.diff(scanData,axis=0)**2                                      # Take the derivative in y to enhance tip changes that occur as horizontal lines. **2 to further enhance
    scanData /= np.max(abs(scanData))                                           # Normalise
    vmin, vmax = napfit.filter_sigma(scanData)                                  # Find 3 sigma
    scanData -= vmin                                                            # Subtract the minimum
    scanData /= abs(vmax - vmin)                                                # And divide by the range (3 sigma)
    scanData[scanData > 1] = 1                                                  # Saturate everything over 1
    scanData *= 255                                                             # Change the range so it's uint8 representable
    grey = scanData.astype(np.uint8)                                            # Change the data type to uint8 for the Canny filter
    
    edges = cv2.Canny(grey, threshold1=50, threshold2=150, apertureSize = 3)    # Edge detection
    lines = cv2.HoughLinesP(image=edges, rho=1, theta=np.pi/180, threshold=1,   # Pull lines from edges
                            lines=np.array([]),minLineLength=1,maxLineGap=0)
    
    if(type(lines) == type(None)): lines = []                                   # Make it an empty list if there are no lines detected
    
    lineDict = {}                                                               # Dictionary to sort all lines according to their y-coodinate
    for line in lines:                                                          
        if(abs(line[0][1] == line[0][3])):                                      # Only process this line if it is horizontal (i.e. y1=y2)
            if(line[0][1] in lineDict):                                         # If there's already a horizontal line at this y-coordinate
                lineDict[line[0][1]].append(line)                               # Add it to the dictionary
            else:                                                               # If this is the first horizontal line at this y-coordinate...
                lineDict[line[0][1]] = [line]                                   # Create a new dictionary entry with the y-coordinate as the key and add the line

    tipChanges = []                                                             # This will be the list of y-coordinates where tip changes have occurred
    minLineLength=len(grey[0])/8                                                # Only count lines if they are at least 1/8 of the image in length
    for y,lines in lineDict.items():                                            # For each y-coordinate we've found lines at
        totalLength = 0
        for line in lines:
            totalLength += line[0][2] - line[0][0]                              # Accumulate total line length at this y coordinate.
        if(totalLength > minLineLength):                                        # If the total length is greater than our threshold
            tipChanges.append(y)                                                # Count this line as a tip change and append its y coord

    tipChanges = np.sort(tipChanges)                                            # Sort coords by ascending order
    diff = np.diff(tipChanges)                                                  # Group lines that are less than two pixels apart in y and
    tipChangeCount = sum(diff > 2)                                              # Count the number of tip changes to be the number of groups
    
    return tipChangeCount
    