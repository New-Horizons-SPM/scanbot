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
    im1 = ndimage.gaussian_filter(im1, 0.5)
    im2 = ndimage.gaussian_filter(im2, 0.5)
    im1_diff = np.diff(im1,axis=1)                                              # Differentiate along x
    im2_diff = np.diff(im2,axis=1)                                              # Differentiate along x
        
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
# Tip tracking
###############################################################################
def getAveragedFrame(cap,n=1,initialFrame=[]):
    """
    Read frames from cv2.VideoCapture

    Parameters
    ----------
    cap : cv2.VideoCapture object
    n   : number of frames to average

    Returns
    -------
    ret : Still capturing
    avgFrame : Averaged frames

    """
    ret, avgFrame = cap.read()
    if(not ret): return ret, avgFrame
    avgFrame = np.array(avgFrame).astype(np.float32)
    for i in range(n-1):
        ret, frame = cap.read()                                                 # Capture frame-by-frame
        if(not ret): return ret, frame
        avgFrame += np.array(frame).astype(np.float32)
    
    avgFrame = avgFrame/n
    
    if(len(initialFrame)):
        diff = abs(initialFrame.astype(float) - frame.astype(float))
        tip = np.max(diff,axis=2)
        tip /= np.max(tip)
        mask = tip > 0.25
        initialFrame[mask,:] = 0.0
        diff = abs(initialFrame - frame)
        avgFrame = np.max(diff,axis=2)
    
    return ret,avgFrame

def trackTip(ROI,tipPos):
    threshold = 160
    ret,thresh = cv2.threshold(ROI.astype(np.uint8),threshold,255,0)            # Set threshold values for finding contours. high threshold since we've saturated the edges
    contours,hierarchy = cv2.findContours(thresh, 1, 2)                         # Pull out all contours
    
    area = 10
    tipContour = -1
    minRow = tipPos[1] - area
    maxRow = tipPos[1] + area
    if(minRow < 0): minRow = 0
    if(maxRow > len(ROI) - 1): maxRow = len(ROI) - 1
    
    minCol = tipPos[0] - area
    maxCol = tipPos[0] + area
    if(minCol < 0): minCol = 0
    if(maxCol > len(ROI[0]) - 1): maxCol = len(ROI[0]) - 1
    
    for idx,c in enumerate(contours):
        mask = np.zeros_like(ROI).astype(np.uint8)
        cv2.drawContours(mask, contours, idx, 255, -1)                          # Draw filled in contour on mask
        if(np.sum(mask[minRow:maxRow,minCol:maxCol] > 0)):
            tipContour = idx
            break
        
    mask = mask/np.max(mask)
    mask = mask.astype(np.uint8)
    
    if(tipContour == -1):
        print("LOST TIP")
        mask = np.zeros_like(ROI).astype(np.uint8)
        cv2.drawContours(mask, contours, -1, 255, -1)                           # Draw filled in contour on mask
        return mask,tipPos
    
    tipRow = max(loc for loc, val in enumerate(np.argmax(mask > 0,axis=1) > 0) if val)
    mask[minRow:maxRow,minCol:maxCol] *= 2
    mask[mask < 2] = 0
    tipColLeft = np.argmax(np.argmax(mask > 0,axis=0) > 0)
    tipColRight = len(mask[0]) - np.argmax(np.argmax(np.fliplr(mask) > 0,axis=0) > 0) - 1
    tipCol = int((tipColLeft + tipColRight)/2)
    
    tipPos = np.array([tipCol,tipRow])
    
    return tipPos
    
def drawRec(frame,rec,xy=[0,0],win=0):
    """
    Draw a rectangle at a location in the frame

    Parameters
    ----------
    frame : cv2 frame to draw a rectangle on
    rec   : coordinates of the rectangle [x,y,w,h] where x,y is the coordinate 
            of the top left corner of the rectangle with respect to the origin
            xy
    xy    : origin [x,y]
    win   : Number of pixels by which to increase the size of the rectangle.

    Returns
    -------
    frame_rec : 

    """
    r = rec.copy()
    r[0] -= win;
    r[1] -= win
    r[2] += 2*win
    r[3] += 2*win
    
    x,y = xy
    r[0] += x
    r[1] += y
    
    startPoint = (r[0],r[1])
    endPoint   = (r[0] + r[2],r[1] + r[3])
    frame_rec = cv2.rectangle(frame, startPoint, endPoint, color=(255,0,0), thickness=2)
    
    return frame_rec

def trimStart(cap,frames):
    frameCount = 0
    while(cap.isOpened()):                                                      # Read until video is completed
        ret,frame = cap.read()                                                  # Capture frame-by-frame
        if(not ret): break
        frameCount += 1
        if(frameCount >= frames): break

def getVideo(cameraPort,demo=0):
    if(demo):
        cap = cv2.VideoCapture('../Dev/move_tip_2.mp4')                         # Load in the mp4
        # trimStart(cap,frames=2000)                                              # Trim off the start of the video
        return cap
    
    cap = cv2.VideoCapture(cameraPort,cv2.CAP_DSHOW)                            # Camera feed. Camera port: usually 0 for desktop and 1 for laptops with a camera. cv2.CAP_DSHOW is magic
    return cap

clicked = False
def getInitialFrame(cap,n=10,demo=0):
    global clicked
    clicked = False
    initialFrame = []
    
    if(demo):
        cp = cv2.VideoCapture('../Dev/initialise.mp4')                          # Load in the mp4
    else:
        cp = cap
    
    print("Getting initial frame...")
    windowName = "Move the tip out of view, then click to confirm. 'q' to cancel."
    cv2.namedWindow(windowName)
    cv2.setMouseCallback(windowName, checkClick)
    while(not clicked):
        _,frame = getAveragedFrame(cp,n=1)
        cv2.imshow(windowName,frame.astype(np.uint8))
        if cv2.waitKey(25) & 0xFF == ord('q'): break                            # Press Q on keyboard to  exit
    
    if(clicked):
        _,initialFrame = getAveragedFrame(cp,n=n)
        
    cv2.destroyAllWindows()
    return initialFrame

def displayUntilClick(cap):
    global clicked
    clicked = False
    
    print("Move the tip in view, then click to confirm. 'q' to cancel.")
    windowName = "Move the tip in view, then click to confirm. 'q' to cancel."
    cv2.namedWindow(windowName)
    cv2.setMouseCallback(windowName, checkClick)
    while(not clicked):
        _,frame = getAveragedFrame(cap,n=1)
        cv2.imshow(windowName,frame.astype(np.uint8))
        if cv2.waitKey(25) & 0xFF == ord('q'): break                            # Press Q on keyboard to  exit
        
    cv2.destroyAllWindows()
    
    return clicked == True
    
def checkClick(event, x, y, flags, param):
    global clicked
    if event == cv2.EVENT_LBUTTONUP: clicked = True
    return

def drawRectangle(event, x, y, flags, param):
    global getROI_initial, getROI_final
    if event == cv2.EVENT_LBUTTONDOWN:
       getROI_initial = np.array([x,y])
    elif event == cv2.EVENT_LBUTTONUP:
       getROI_final = np.array([x,y])

markPoint_pos = []
def markPoint(cap,windowName="Mark a point"):
    global markPoint_pos
    
    cv2.namedWindow(windowName)
    cv2.setMouseCallback(windowName, drawCircle)
    
    _,frame = getAveragedFrame(cap,n=1)
    while True:
        if(len(markPoint_pos)): break
        cv2.imshow(windowName,frame.astype(np.uint8))
        if cv2.waitKey(25) & 0xFF == ord('q'): break                            # Press Q on keyboard to  exit
    
    cv2.destroyAllWindows() 
    
    pos = np.array([0,0])
    if(len(markPoint_pos)): pos = markPoint_pos.copy()
    
    markPoint_pos = []
    return pos
       
def drawCircle(event, x, y, flags, param):
    global markPoint_pos
    if event == cv2.EVENT_LBUTTONUP:
       markPoint_pos = np.array([x,y])
###############################################################################
# Classifying STM Images
###############################################################################
def classify(scanData,filename,classificationHistory):
    """
    This classifies scans based on the number of tip changes that occur in 
    them. If more than 5 tip changes occur, the scan is considered 'bad'. If
    more than 5 bad scans are encountered in a row, then we consider the tip in
    need of shaping.
    
    This classifier can be replaced using the hook: hk_classifier.
    See GitHub page for full documentation

    Parameters
    ----------
    scanData    : Raw scan data
    filename    : .sxm filename
    classificationHistory : Running list of all previous classifications

    Returns
    -------
    classification : dictionary containing labels for image

    """
    nan = np.isnan(scanData).any()                                              # Flag to say there are nans in data which might affect  analysis
    scanData = np.nan_to_num(scanData)
    tipChangeCount = findTipChanges(scanData.copy())
    
    i = 0
    badScans = 0
    tipShape = 0
    while(True):
        i -= 1
        if(abs(i) > len(classificationHistory)): break
    
        scan_i = classificationHistory[i]
        
        if(scan_i["nan"]):
            continue                                                            # Don't count any scans that have been stopped midway
        
        if(scan_i["tipChanges"] > 5):                                           # If there are more than 5 tip changes in this scan, consider the tip unstable
            badScans += 1                                                       # Keep track of the number of bad scans in a row
        
        if(badScans > 4):                                                       # If we get to 5 bad scans in a row, then we'll kick off tip shaping
            tipShape = 1
            break
        
        if(scan_i["tipChanges"] <= 5):                                          # If we run into a good scan, before we hit 5 bad scans, don't tip shape... we need 5 bad scans in a row for that.
            break
        
    classification = {"tipChanges" : tipChangeCount,
                      "nan"        : nan,
                      "tipShape"   : tipShape}
    
    return classification

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
def assessTip(scanData,lxy,xy,returnContour=False):
    """
    Assess the quality of the tip based on the imprint it left on the surface
    after a very light tip shaping action.

    Parameters
    ----------
    scanData : raw scan data
    lxy      : lenght and width of the scan frame (m)
    xy       : position the tip shape occurred relative to the centre of the 
               scan frame

    Returns
    -------
    symScore : score out of 10 for symmetry
    size     : size of the imprint area (nm2)
    contour  : Image of the imprint with a contour drawn on it

    """
    lowpass  = ndimage.gaussian_filter(scanData, 20)                            # Lowpass filter the scandata
    highpass = scanData - lowpass                                               # Subtract the lowpass from original to get highpass
    
    zMax = np.max(highpass)
    zMin = np.min(highpass)
    threshold = (255*((5e-11 - zMin)/(zMax - zMin))).astype(np.uint8)
    
    highpass -= np.min(highpass)
    norm = 255*(highpass/np.max(highpass))
    norm = norm.astype(np.uint8)
    ret,thresh = cv2.threshold(norm,threshold,255,0)                            # Set threshold values for finding contours. high threshold since we've saturated the edges
    contours,hierarchy = cv2.findContours(thresh, 1, 2)                         # Pull out all contours
    contours = sorted(contours, key=cv2.contourArea)                            # Sort all the contours by ascending area. This will help when we have concentric contours that we need to deal with
    
    dxy = lxy/scanData.shape[0]
    # xy += np.array([lxy,lxy])/2
    # xy /= dxy
    # xy  = xy.astype(np.int)
    xy = np.flip(np.unravel_index(np.argmax(np.flipud(highpass)),highpass.shape)) # Take the location of the brightest contour in the image
    
    size = -1
    symScore = 1
    tipImprint = np.zeros_like(scanData) + zMin
    for idx,c in enumerate(contours):
        mask = np.zeros_like(scanData)
        cv2.drawContours(mask, contours, idx, 255, -1)                          # Draw filled contour in mask
        mask = np.flipud(mask)
        if(mask[xy[1],xy[0]] > 0):
            mask = np.flipud(mask) > 0
            tipImprint[mask] = highpass[mask]
            size = cv2.contourArea(c)*dxy*dxy*1e18
            perimeter = cv2.arcLength(c,True)*dxy*1e9
            symScore = (4*np.pi*size)/(perimeter**2)
            cv2.drawContours(scanData, contours, idx, 2*np.max(scanData), 1)    # Draw contour over original scanData
            break
    
    if(not returnContour): return symScore,size
    return symScore, size, scanData
    
def getCleanCoordinate(scanData,lxy):
    """
    Returns a coordinate w.r.t the centre of the scan frame that is free from
    adsorbates.

    Parameters
    ----------
    scanData : 
    lxy      : 

    Returns
    -------
    pos        : location of clean area. [] if area is not clean

    """
    
    return np.array([0.0,0.0])

def isClean(scanData,lxy,threshold=1e-9,sensitivity=1):
    """
    Assess whether imaged surface is clean/flat. Function also works for 
    incomplete images.

    Parameters
    ----------
    scanData    : Raw scan data
    lxy         : Length/width of scan frame in units of nm
    threshold   : Threshold for cleanliness in units of nm
    sensitivity : Scales the threshold area for which a surface is considered 
                  unclean. Larger = less tolerant.
                  
    Returns
    -------
    isClean     : True:  Area is clean to within threshold.
                  False: Area is not clean to within threshold.

    """
    validScan = scanData[np.logical_not(np.isnan(scanData))]
    
    axy = (lxy/scanData.shape[0])**2                                            # Area per pixel
    thresholdArea  = (1e9*lxy/10)*(threshold)**2                                # Threshold for the amount of 'unclean' area
    thresholdArea /= sensitivity
    
    lowpass  = ndimage.gaussian_filter(validScan, 20)                           # Lowpass filter the scandata
    highpass = validScan - lowpass                                              # Subtract the lowpass from original to get highpass
    
    unCleanMask         = abs(highpass) > 1*threshold                           # Mask for surface area that's unClean
    unScannableMask     = abs(highpass) > 2*threshold                           # Mask for surface area that's unScannable
    bailImmediatelyMask = abs(highpass) > 3*threshold                           # Mask for surface area that's extreme
    
    unCleanArea         = np.sum(unCleanMask)*axy
    unScannableArea     = np.sum(unScannableMask)*axy
    bailImmediatelyArea = np.sum(bailImmediatelyMask)*axy
    
    if(unCleanArea         > thresholdArea/1): return False
    if(unScannableArea     > thresholdArea/2): return False
    if(bailImmediatelyArea > thresholdArea/5): return False
    
    return True

def findIslands(scanData,lxy,curvatureThreshold=4,minIslandArea=30,minGoopArea=2):
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
