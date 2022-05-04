#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec 12 22:57:34 2016

@author: jack
"""

import numpy as _np

from scipy import optimize as _optimize
from scipy.stats import norm as _norm


### internal functions not loaded by core_functions:

def _plane(a0, a1, b1, x0, y0):
    return lambda x,y: a0 +a1*(x-x0) +b1*(y-y0)
    
def _planemoments(data):
    a0 = _np.abs(data).min()
    index = (data-a0).argmin()
    x, y = data.shape
    x0 = float(index / x)
    y0 = float(index % y)
    a1 = 0.0
    b1 = 0.0
    return a0, a1, b1, x0, y0
 
def _fitplane(data):
    params = _planemoments(data)
    errorfunction = lambda p: _np.ravel(_plane(*p)(*_np.indices(data.shape)) - data)
    p, success = _optimize.leastsq(errorfunction, params)
    return p
    
def _return_plane(params, data):
    _fit_data = _plane(*params)
    return _fit_data(*_np.indices(data.shape))
    
    
###externally visible functions loaded into gui:
    
def no_filter(scan_image):
    return scan_image
    
def plane_fit_2d(scan_image, region=None):
    '''
    Parameters
    ----------
    scan_image : 2d array
        image to be plane fit.
    region : list of 2 tuples, optional
        pass region of image to plane fit: [(x1, y1), (x2, y2)]

    Returns
    -------
    TYPE
        plane-subtracted image array

    '''
    if region == None:
        return scan_image - _return_plane(_fitplane(scan_image),scan_image)
    else:
        scan_fit_area = scan_image[region[0][0]:region[1][0], region[0][1]:region[1][1]]
        return scan_image - _return_plane(_fitplane(scan_fit_area), scan_image)
    
    
def row_line_fit(scan_image):
    x = _np.arange(scan_image.shape[0])
    for i in range(scan_image.shape[1]):
        fit = _np.polyfit(x,scan_image[i,],1)
        fit = _np.polyval(fit, x)
        scan_image[i,] -= fit
    return scan_image

def subtract_average(scan_image):
    return scan_image - _np.mean(scan_image)
    
def row_parabolic_fit(scan_image):
    x = _np.arange(scan_image.shape[0])
    for i in range(scan_image.shape[1]):
        fit = _np.polyfit(x,scan_image[i,],2)
        fit = _np.polyval(fit, x)
        scan_image[i,] -= fit
    return scan_image
    
def filter_sigma(image, sig=3):
    mu, sigma = _norm.fit(image)
    vmin = mu - sig * sigma
    vmax = mu + sig * sigma
    return vmin, vmax
    
    