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
from scipy import ndimage

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
# Classifying STM Images
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
    if(not tipChangeCount and len(tipChanges)): tipChangeCount += 1             # Some very fine tip changes can be missed without this
    
    return tipChangeCount

###############################################################################
# Analyse STM Images
###############################################################################
def analyse(scanData,lxy,curvatureThreshold=4,minIslandArea=30,minGoopArea=2):
    """
    Utility that decomposes a scan into islands and substrate

    Parameters
    ----------
    scanData : raw scan data
    lxy      : scan range [x,y](m)
    curvatureThreshold : islands with sum(abs(mean curvature)) less than this 
                         threshold are considered substrate. otherwise 
                         considered as molecules/sample. This parameter may be
                         sample dependent
    minIslandArea : minimum size of something considered an island (nm2)        # Note: Bare regions of substrate are also considered islands
    minGoopArea   : minimum size of something considered goop (nm2)

    """
    lxy = np.array(lxy)                                                         # Ensure it's a numpy array
    pxy = np.array(scanData.shape[1],scanData.shape[0])                         # Num pixels [x,y]
    dxy = np.array(lxy/pxy)                                                     # Real size of each pixel on the figure (this is not the resolution of the actual data)
    pixelArea = dxy[0]*dxy[1]*1e18                                              # Area of each pixel in units of nm2
    
    im = normalise(scanData.copy(), 255).astype(np.uint8)                       # Normalise the data and convert it to uint8 for the canny filter later
    
    lowpass = ndimage.gaussian_filter(scanData, 2)
    gxy  = np.gradient(lowpass,*dxy)                                            # Not sure if it should be dx,dy or dy,dx here
    grad = np.sqrt(gxy[0]**2 + gxy[1]**2)
    grad = normalise(grad,255).astype(np.uint8)
    mask = grad > 127
    
    edgeEnhanced = im.copy()
    edgeEnhanced[mask] = 255                                                    # Set edges to saturation
    edgeEnhanced[0][:] = 255                                                    # Saturate the top border. Saturating the border ensures no open contours later
    edgeEnhanced[pxy[1]-1][:] = 255                                             # Saturate the bottom border
    edgeEnhanced[:,0] = 255                                                     # Saturate the left border
    edgeEnhanced[:,pxy[0]-1] = 255                                              # Saturate the right border
    
    ret,thresh = cv2.threshold(edgeEnhanced,240,255,0)                          # Set threshold values for finding contours. high threshold since we've saturated the edges
    contours,hierarchy = cv2.findContours(thresh, 1, 2)                         # Pull out all contours
    contours = sorted(contours, key=cv2.contourArea)                            # Sort all the contours by ascending area. This will help when we have concentric contours that we need to deal with
    
    goop     = []                                                               # List of 2D arrays, each containing one piece of 'goop' from the raw image
    goopMask = []                                                               # List of 2D boolean arrays that contain the mask for the goop in the above array
    for idx,c in enumerate(contours):
        area = cv2.contourArea(c)*pixelArea                                     # Area of the contour in nm2
        if(area > minGoopArea and area < minIslandArea):                        # Anything between these two values is considered 'goop'
            mask = np.zeros_like(scanData)
            cv2.drawContours(mask, contours, idx, 255, -1)                      # Draw filled contour in mask
            mask = mask> 0                                                      # Convert to bool
            
            goopMask.append(mask)                                               # Append this mask to the list of goop
            goop.append(np.zeros_like(scanData))                                # Append new image to list of goop
            goop[-1][mask] = (im[mask] - np.min(im[mask]))                      # Anything outside the mask remains zero. anything inside the mask is filled with the original data
    totalGoopMask = np.sum(goopMask,0) > 0                                      # Sum of all that is considered goop
    
    island     = []                                                             # List of 2D image arrays, each will contain a single island
    islandMask = []                                                             # List of 2D mask arrays, each will contain the corresponding mask for an island
    totalIslandMask = np.zeros_like(scanData) > 0                               # Running total mask of all islands.
    for idx,c in enumerate(contours):                                           # Loop through all the contours
        area = cv2.contourArea(c)*pixelArea                                     # Calculate the area in nm2
        if(area > 0.95*pxy[0]*pxy[1]*pixelArea): continue                       # If the area is the the ~whole scan window, it's probably the artificial contour we've drawn around it so skip it
        if(area > minIslandArea):                                               # If is large enough to be considered an island...
            mask = np.zeros_like(scanData)                                      # This will contain the mask for this island
            cv2.drawContours(mask, contours, idx, 255, -1)                      # Draw filled contour in mask
            
            mask = mask > 0                                                     # Convert it to bool
            islandMask.append(mask)                                             # Append this mask to the list of masks
            island.append(np.zeros_like(scanData))                              # Append a new image to our list of islands
            island[-1][mask] = im[mask]                                         # Grab the island from the original image
            island[-1][totalGoopMask]   -= im[totalGoopMask]                    # Get rid of the goop
            island[-1][totalIslandMask] -= im[totalIslandMask]                  # Get rid of any smaller islands we've already found within it. This only works because we've sorted the contours by ascending area already
            island[-1][~mask] = 0                                               # Anything outside our island should just be zero
            island[-1][island[-1]<0] = 0                                        # Anything within our island that was subtracted in the previous step should also be zero
            island[-1][island[-1]>0] -=np.min( island[-1][island[-1]>0])        # Bring the bottom of the island to zero
        
            totalIslandMask = totalIslandMask | (islandMask[-1] > 0)            # Append this island to the total island mask
    
    substrate = np.zeros_like(scanData)                                         # Substrate mask
    molecules = np.zeros_like(scanData)                                         # Molecules/sample mask
    for idx,i in enumerate(island):                                             # Loop through everyhing we've considered an island
        H = meanCurvature(i,dxy*1e10)                                           # Calculate the mean curvature (numbers are weird when dxy is really small so multiply by a large constant)
        H[~islandMask[idx]] = 0                                                 # Force everything outside the island to zero
        hfactor = np.sum(abs(H)/(pixelArea*np.sum(i>0)))                        # Sum the total curvature and divide by area
        if(hfactor < curvatureThreshold):                                       # Anything less than the curvature threshold is considered flat enough to be substrate.
            substrate += i
        else:                                                                   # Otherwise count it as molecules/sample
            molecules += i
    
    return {"substrate" : substrate,
            "molecules" : molecules}

def meanCurvature(Z,dxy=[1,1]):
    """
    Formaulas from the internet to calculate mean curvature
    https://stackoverflow.com/questions/11317579/surface-curvature-matlab-equivalent-in-python

    Parameters
    ----------
    Z   : 2D image as a numpy array
    dxy : pixel size

    Returns
    -------
    H : mean curvature

    """
    Zy,  Zx  = np.gradient(Z.astype(np.float32),*dxy)
    Zxy, Zxx = np.gradient(Zx,*dxy)
    Zyy, _   = np.gradient(Zy,*dxy)

    H = (Zx**2 + 1)*Zyy - 2*Zx*Zy*Zxy + (Zy**2 + 1)*Zxx
    H = -H/(2*(Zx**2 + Zy**2 + 1)**(1.5))

    return H

def normalise(im,maxval,mask=[],sig=3):
    if(len(mask) == 0): mask = np.ones_like(im)
    mask = mask > 0
    im[~mask] = 0
    vmin, vmax = napfit.filter_sigma(im[mask],sig=sig)                          # cmap saturation
    im[mask] -= vmin
    im[mask] /= abs(vmax - vmin)
    im[im > 1] = 1
    im[mask] *= maxval
    im[~mask] = 0
    return im

def tipQuality(scanData,dxy,pos,xy=[0,0]):
    """
    This function assesses the quality of an STM tip by analysing its crater.

    Parameters
    ----------
    scanData : raw scan data of the area where a tip shape has occurred
    lxy      : scan range [x,y](m)
    pos      : Location the tip shape occurred [x,y] (m)
    xy       : Defines whether the tip shape location is relative or absolute.
               If provided, xy is the absolute location of the centre of the 
               scan frame and <pos> is considered an absolute location. If 
               left as [0,0], <pos> is considered relative to the centre of 
               the scan frame

    Returns
    -------
    score: A score from 0 to 1 that quantifies tip quality. 0 is bad. 1 is good
    error: 0 means all good.
           1 means couldn't find a contour at the tip location
    """
    
    lowpass = ndimage.gaussian_filter(scanData, 2)
    gxy  = np.gradient(lowpass,*dxy)                                            # Not sure if it should be dx,dy or dy,dx here
    grad = np.sqrt(gxy[0]**2 + gxy[1]**2)
    grad = normalise(grad,255).astype(np.uint8)
    mask = grad > 127
    
    ret,thresh = cv2.threshold(edgeEnhanced,240,255,0)                          # Set threshold values for finding contours. high threshold since we've saturated the edges
    contours,hierarchy = cv2.findContours(thresh, 1, 2)                         # Pull out all contours
    
    
    
    
    
    contours = pickle.load(open('contours.pk','rb'))
    dxy = np.array([1.953125e-10, 1.953125e-10])
    pixelArea = dxy[0]*dxy[1]
    
    goop = []
    minIslandArea = 40
    minGoopArea = 2                                                                 # Min goop area is 2 nm2
    for idx,c in enumerate(contours):
        area = cv2.contourArea(c)*pixelArea
        if(area*1e18 > minGoopArea and area*1e18 < minIslandArea):                  # Only highlight islands larger than 25 nm2
            mask = np.zeros_like(rawim)
            cv2.drawContours(mask, contours, idx, 255, -1)                          # Draw filled contour in mask
            mask = mask> 0
            P = cv2.arcLength(curve=c, closed=True)*dxy[0]
            C = 4*np.pi*area/(P**2)
            if(C > 0.8):
                cv2.drawContours(rawim, contours, idx, 255)