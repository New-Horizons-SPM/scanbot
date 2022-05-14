# -*- coding: utf-8 -*-
"""
Created on Tue May 10 16:18:08 2022

@author: jced0001
"""

import numpy as np
import scipy.signal as sp
from PIL import Image
import os
import math
import time

###############################################################################
# Drift Correction
###############################################################################
def getFrameOffset(im1,im2,dxy=[1,1]):
    """
    Returns the offset of im2 relative to im1. im1 and im2 must be the same
    size and scale

    Parameters
    ----------
    im1 : image to compare against
    im2 : image to get the offset of
    dxy : pixel size in x and y: [dx,dy]

    Returns
    -------
    None.

    """
    im1_diff = np.diff(im1,axis=0)                                              # Differentiate along x
    im2_diff = np.diff(im2,axis=0)                                              # Differentiate along x
        
    xcor = sp.correlate2d(im1_diff,im2_diff, boundary='symm', mode='same')
    y,x  = np.unravel_index(xcor.argmax(), xcor.shape)

    ni = np.array(xcor.shape)
    oy,ox = np.array([y,x]).astype(int) - (ni/2).astype(int)
    
    ox *= dxy[0]
    oy *= -dxy[1]
    
    return np.array([ox,oy])
###############################################################################
# Drift Correction
###############################################################################
def stitchSurvey(storage,storagePath,surveyName,delete):
    if(surveyName == "*"): return "Survey name required use arg -s=<survey name>"
    surveyName = '_' + surveyName + '_'
    
    files  = []
    bucket = storage.bucket()
    for b in bucket.list_blobs():
        filename = b.name
        if(filename.startswith(storagePath) and filename != storagePath):
            if(surveyName in filename):
                files.append(filename)
                
    if(not len(files)): return "No files found for " + storagePath + surveyName
    
    bucket = storage.bucket()
    for f in files:
        saveFilename = f.split('/')[-1]
        blob = bucket.blob(f)
        blob.download_to_filename(saveFilename)
    
    localFiles  = [f.split('/')[-1] for f in files]
    images = [Image.open(x) for x in localFiles]
    widths, heights = zip(*(i.size for i in images))
    
    n = len(images)
    rows = int(n**0.5)
    cols = math.ceil(n**0.5)
    
    total_width = max(widths)*cols
    max_height  = max(heights)*rows
    
    new_im = Image.new('RGB', (total_width, max_height))
    
    im = 0
    x_offset = 0
    y_offset = 0
    for r in range(rows):
        for c in range(cols):
            if(im == len(images)): break
            new_im.paste(images[im], (x_offset,y_offset))
            x_offset += images[im].size[0]
            im += 1
            
        if(im == len(images)): break
        x_offset  = 0
        y_offset += images[im].size[1]
            
    for im in images: im.close()
    
    new_im.save(surveyName + '.png')
    
    for f in localFiles: os.remove(f)
    
    if(delete):
        for f in files:
            bucket.delete_blob(f)
    
    return "Survey stitched!"