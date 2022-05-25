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
import imageio

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
    
    ox += x%2                                                                   # Add in this offset because differentiating results in odd number of px 
    
    ox *= dxy[0]
    oy *= -dxy[1]
    
    return np.array([ox,oy])
###############################################################################
# Image Processing
###############################################################################
def getFiles(storage,storagePath,surveyName):
    surveyName = '_' + surveyName + '_'
    
    files  = []
    bucket = storage.bucket()
    for b in bucket.list_blobs():
        filename = b.name
        if(filename.startswith(storagePath) and filename != storagePath):
            if(surveyName in filename):
                files.append(filename)
    
    return files

def downloadFiles(storage,files):
    bucket = storage.bucket()
    for f in files:
        saveFilename = f.split('/')[-1]
        blob = bucket.blob(f)
        blob.download_to_filename(saveFilename)
    
    localFiles  = [f.split('/')[-1] for f in files]
    return localFiles
    
def stitchSurvey(storage,storagePath,surveyName,delete):
    if(surveyName == "*"): return "Survey name required use arg -s=<survey name>"
    
    files = getFiles(storage,storagePath,surveyName)
                
    if(not len(files)): return "No files found for " + storagePath + surveyName
    
    localFiles = downloadFiles(storage,files)
    
    images = [Image.open(x) for x in localFiles]
    widths, heights = zip(*(i.size for i in images))
    
    n = len(images)
    cols = math.ceil(n**0.5)
    rows = math.ceil(n/cols)
    
    total_width  = max(widths)*cols
    total_height = max(heights)*rows
    
    new_im = Image.new('RGB', (total_width, total_height))
    
    im = 0
    direction = 1
    x_offset = 0
    y_offset = max(heights)
    for r in range(rows):
        for c in range(cols):
            if(im == len(images)): break
            new_im.paste(images[im], (x_offset,total_height - y_offset))
            x_offset += images[im].size[0]*direction
            im += 1
            
        if(im == len(images)): break
        direction *= -1
        x_offset += images[im].size[0]*direction
        y_offset += images[im].size[1]
            
    for im in images: im.close()
    
    new_im.save(surveyName + '.png')
    
    bucket = storage.bucket()
    blob = bucket.blob(storagePath + "stitch/" + surveyName.strip('_') + '.png')
    blob.upload_from_filename(surveyName + '.png')

    url = blob.generate_signed_url(expiration=9999999999)
    
    os.remove(surveyName + '.png')
    
    for f in localFiles: os.remove(f)
    
    if(delete):
        for f in files:
            bucket.delete_blob(f)
    
    return url

def makeGif(storage,storagePath,surveyName,delete):
    files = getFiles(storage,storagePath,surveyName)
                
    if(not len(files)): return "No files found for " + storagePath + surveyName
    
    localFiles = downloadFiles(storage,files)
    biasList = []
    
    reply = ""
    try:
        biasList = [float(fname.split(surveyName)[-1].split('V_')[0].strip('_')) for fname in localFiles]
        localFiles = [f for _,f in sorted(zip(biasList,localFiles))]
    except:
        reply = "Could not sort by bias"
        
    images = [Image.open(x) for x in localFiles]
    
    images[0].save('output.gif', formate='GIF',
               append_images=images[1:],
               save_all=True,
               duration=300, loop=0
               )
    
    bucket = storage.bucket()
    blob = bucket.blob(storagePath + "gifs/" + surveyName.strip('_') + '.gif')
    blob.upload_from_filename('output.gif')

    url = blob.generate_signed_url(expiration=9999999999)
    
    os.remove('output.gif')
    
    for f in localFiles: os.remove(f)
    
    return reply,url