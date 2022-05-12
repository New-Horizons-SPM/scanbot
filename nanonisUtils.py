# -*- coding: utf-8 -*-
"""
Created on Tue May 10 16:18:08 2022

@author: jced0001
"""

import numpy as np
import scipy.signal as sp

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