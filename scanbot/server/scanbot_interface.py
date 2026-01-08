# -*- coding: utf-8 -*-
"""
Created on Fri August 8 22:06:37 2022

@author: Julian Ceddia
"""

from scanbot.server.scanbot import scanbot
from scanbot.server import global_

import os
import sys
import subprocess
from pathlib import Path
import shutil
import time

import ipaddress

import threading

class scanbot_interface(object):
    
###############################################################################
# Constructor
###############################################################################
    def __init__(self,run_mode, module_dir="./"):
        print("Initialising app...")
        self.run_mode   = run_mode
        self.module_dir = module_dir
        self.scanbot    = scanbot(self)
        self.loadConfig()
        self.initGlobals()
        self.initCommandDict()
    
###############################################################################
# Initialisation
###############################################################################
    def loadConfig(self):
        """
        Read in the scanbot_config.ini configuration file. File format is:
            key1=value1
            key2=value2

        """
        print("Loading scanbot_config.ini...")
        initDict = {'path'                      : 'sbData',                     # Path to save data
                    'port_list'                 : '6501,6502,6503,6504',        # Ports (see nanonis => Main Options => TCP Programming Interface)
                    'ip'                        : '127.0.0.1',                  # IP of the pc controlling nanonis
                    'temp_calibration_curve'    : '',                           # Path to temp calibration curve (see nanonis Temperature modules)
                    'topo_basename'             : '',                           # basename for topographic images
                    'safe_current'              : '5e-9',                       # When the current goes above this threhold the tip is considered crashed. Used when controlling the course piezos
                    'safe_retract_V'            : '200',                        # Voltage applied to the 'Z' piezo when retracting tip in case of crash
                    'safe_retract_F'            : '1500',                       # Frequency applied to the 'Z' piezo when retracting tip in case of crash
                    'piezo_z_max_V'             : '200',                        # Maximum voltage that can be applied to the Z piezo
                    'piezo_z_min_V'             : '0',                          # Minimum voltage that can be applied to the Z piezo
                    'piezo_xy_max_V'            : '130',                        # Maximum voltage that can be applied to the X or Y piezos
                    'piezo_xy_min_V'            : '0',                          # Minimum voltage that can be applied to the X or Y piezos
                    'piezo_z_max_F'             : '5000',                       # Maximum frequency that can be applied to the Z piezo
                    'piezo_z_min_F'             : '500',                        # Minimum frequency that can be applied to the Z piezo
                    'piezo_xy_max_F'            : '5000',                       # Maximum frequency that can be applied to the X or Y piezos
                    'piezo_xy_min_F'            : '500',                        # Minimum frequency that can be applied to the X or Y piezos
                    'hk_commands'               : '0',                          # Flag to look for customised commands in hk_commands
                    'nanonis_version'           : '99999999'}                   # Version of the host nanonis. See nanonis > help > info and take the RT Engine version number. Defaults to the latest version
        
        try:
            with open(self.module_dir + 'scanbot_config.ini','r') as f:         # Go through the config file to see what defaults need to be overwritten
                line = "begin"
                while(line):
                    line = f.readline()[:-1]
                    if(line.startswith('#')): print(line); continue             # Comment
                    if(not '=' in line):
                        print("WARNING: invalid line in config file: " + line)
                        continue
                    key, value = line.split('=')                                # Format for valid line is "Key=Value"
                    if(not key in initDict):                                    # Key must be one of initDict keys
                        print("WARNING: Invalid key in scanbot_config.ini: " + key)
                        continue
                    initDict[key] = value                                       # Overwrite value
        except:
            print("Config file not found, using defaults...")
        
        version = initDict['nanonis_version']
        if(version.startswith('R')):
            version = version.split('R')[1]
        self.nanonis_version = int(version)
        
        self.path         = initDict['path']
        if(not self.path):
            raise Exception("Check config file. Path is empty")
        self.path = self.path.replace('\\','/')
            
        Path(self.path).mkdir(parents=True, exist_ok=True)
        if(not self.path.endswith('/')):
            self.path += '/'
                
        if(self.setPortList(initDict['port_list'].replace(',',' ').split(' '))):
            raise Exception("Check port_list in config file. Must be space or comma delimited.")
            
        if(self.setIP([initDict['ip']])):
            raise Exception("Check config file... Invalid IP.")
        
        self.tempCurve = initDict['temp_calibration_curve']
        
        self.topoBasename = initDict['topo_basename']
        
        self.scanbot.safeCurrent  = float(initDict['safe_current'])
        self.scanbot.safeRetractV = float(initDict['safe_retract_V'])
        self.scanbot.safeRetractF = float(initDict['safe_retract_F'])
        
        self.scanbot.zMaxV  = float(initDict['piezo_z_max_V'])
        self.scanbot.zMinV  = float(initDict['piezo_z_min_V'])
        self.scanbot.xyMaxV = float(initDict['piezo_xy_max_V'])
        self.scanbot.xyMinV = float(initDict['piezo_xy_min_V'])
        
        self.scanbot.zMaxF  = float(initDict['piezo_z_max_F'])
        self.scanbot.zMinF  = float(initDict['piezo_z_min_F'])
        self.scanbot.xyMaxF = float(initDict['piezo_xy_max_F'])
        self.scanbot.xyMinF = float(initDict['piezo_xy_min_F'])
        
        self.hk_commands = []
        if(int(initDict['hk_commands'])):
           from hk_commands import hk_commands
           self.hk_commands = hk_commands(self)
        
    def initGlobals(self):
        global_.tasks   = []
        global_.running = threading.Event()                                     # event to stop threads
        global_.pause   = threading.Event()                                     # event to pause threads
        
    def initCommandDict(self):
        self.commands = {
                        # Configuration
                         'help'             : self._help,                       # Return the entire list of commands or help for a specific command.
                         'set_ip'           : self.setIP,                       # Configure the IP adress - the one for the PC controlling Nanonis. 127.0.0.1 for local machine
                         'get_ip'           : lambda args: self.IP,             # Return the IP scanbot is configured to talk to
                         'set_portlist'     : self.setPortList,                 # Configure which ports scanbot can use when talking to Nanonis
                         'get_portlist'     : lambda args: self.portList,       # Return the list of ports scanbot is configured to use
                         'set_path'         : self.setPath,                     # Changes the directory pngs are saved in. Creates the directory if it doesn't exist.
                         'get_path'         : lambda args: self.path,           # Path to save scan pngs (saves the channel of focus which can be set using plot_channel)
                         'plot_channel'     : self.plotChannel,                 # Read/select the current channel of focus
                         'set_crash_safety' : self.setCrashSafety,              # Set the safety current, 'Z' piezo voltage, and 'Z' piezo retract frequency
                         'get_crash_safety' : self.getCrashSafety,              # Return the safe retract settings
                        # Data Acquisition
                         'plot'             : self.plot,                        # Generate plot of the current scan frame. Select channel using plot_channel
                         'survey'           : self.survey,                      # Take a survey within the current scan area.
                         'survey2'          : self.survey2,                     # Take several surveys at different macroscopic locations by moving the tip between each survey.
                         'bias_dep'         : self.biasDep,                     # Take a series of bias dependent images.
                         'sts_grid'         : self.stsGrid,                     # Take a series of bias dependent images.
                         'zdep'             : self.zdep,                        # z-dependant scanning. Useful for nc-AFM or other constant height imaging
                         'afm_registration' : self.registration,                # Take a constant height scan and perform a tip-lift at a given line.
                        # Tip Actions
                         'move_area'        : self.moveArea,                    # Quickly move the tip to a new area (blindly)
                         'tip_shape_props'  : self.tipShapeProps,               # Read/write tip shaper properties.
                         'tip_shape'        : self.tipShape,                    # Execute a tip shape
                        # AutoSTM
                         'auto_init'        : self.autoInit,                    # Initialise tip location
                         'move_tip_to_sample':self.moveTipToSample,             # Automatically move the tip from its current location to the sample target location.
                         'move_tip_to_clean': self.moveTipToClean,              # Automatically move the tip from its current location to the clean metal target location.
                         'auto_tip_shape'   : self.autoTipShape,                # Routine that automatically prepares a nice tip. Assumes the substrate is a clean metal. Ag111 works best.
                        # Misc
                         'stop'             : self.stop,                        # Interrupt whatever scanbot is doing. Also stops the current scan.
                         'quit'             : self._quit                        # Quits scanbot
        }
        
###############################################################################
# Data Acquisition
###############################################################################
    def plot(self,user_args,_help=False):
        arg_dict = {'-c' : ['', lambda x: str(x), "(str) Channel to plot. '' plots the default channel which can be set using plot_channel"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help plot``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        return self.scanbot.plot(*args)
    
    def survey(self,user_args,_help=False,surveyParams=[]):
        arg_dict = {'-bias' : ['-default', lambda x: float(x), "(float) Scan bias"],
                    '-n'    : ['5',        lambda x: int(x),   "(int) Size of the nxn grid of scans"],
                    '-i'    : ['1',        lambda x: int(x),   "(int) Start the grid from this index"],
                    '-s'    : ['scanbot',  lambda x: str(x),   "(str) Suffix at the end of autosaved sxm files"],
                    '-xy'   : ['-default', lambda x: float(x), "(float) Length and width of the scan frame (m)"],
                    '-dx'   : ['-default', lambda x: float(x), "(float) Scan grid spacing (m). Default is -xy"],
                    '-px'   : ['-default', lambda x: int(x),   "(int) Number of pixels"],
                    '-st'   : ['10',       lambda x: float(x), "(float) Drift compensation time (s)"],
                    '-stitch':['0',        lambda x: float(x), "(int) Return the stitched survey after completion. 1: Yes, else No"],
                    '-hk_survey': ['0',    lambda x: int(x),   "(int) Flag to call a custom python script after each image. Script must be ~/scanbot/scanbot/hk_survey.py. 0=Don't call, 1=Call"],
                    '-hk_classifier': ['0',lambda x: int(x),   "(int) Flag to call a custom classifier after each image. Script must be ~/scanbot/scanbot/hk_classifier.py. Only called if -autotip=1. 0=Don't call, 1=Call"],
                    '-autotip': ['0',      lambda x: int(x),   "(int) Automatic tip shaping. 0=off, 1=on"]}
        
        if(_help): return arg_dict
        
        args = surveyParams
        if(not args):
            error,user_arg_dict = self.userArgs(arg_dict,user_args)
            if(error): return error + "\nRun ```help survey``` if you're unsure."
            
            args = self.unpackArgs(user_arg_dict)
        
        func = lambda : self.scanbot.survey(*args)
        return self.threadTask(func)
    
    def survey2(self,user_args,_help=False,survey2Params=[]):
        arg_dict = {'-bias' : ['-default', lambda x: float(x), "(float) Scan bias"],
                    '-n'    : ['5',        lambda x: int(x),   "(int) Size of the nxn grid of scans within each survey"],
                    '-i'    : ['1',        lambda x: int(x),   "(int) Start the grid from this index"],
                    '-s'    : ['scanbot',  lambda x: str(x),   "(str) Suffix at the end of autosaved sxm files"],
                    '-xy'   : ['-default', lambda x: float(x), "(float) Length and width of the scan frame (m)"],
                    '-dx'   : ['-default', lambda x: float(x), "(float) Scan grid spacing (m)"],
                    '-px'   : ['-default', lambda x: int(x),   "(int) Number of pixels"],
                    '-st'   : ['10',       lambda x: float(x), "(float) Drift compensation time (s)"],
                    '-stitch':['0',        lambda x: float(x), "(int) Return the stitched survey after completion. 1: Yes, else No"],
                    '-hk_survey': ['0',    lambda x: int(x),   "(int) Flag to call a custom python script after each image. Script must be ~/scanbot/scanbot/hk_survey.py. 0=Don't call, 1=Call"],
                    '-hk_classifier': ['0',lambda x: int(x),   "(int) Flag to call a custom classifier after each image. Script must be ~/scanbot/scanbot/hk_classifier.py. Only called if -autotip=1. 0=Don't call, 1=Call"],
                    '-autotip': ['0',      lambda x: int(x),   "(int) Automatic tip shaping. 0=off, 1=on"],
                    
                    '-nx'    : ['2',       lambda x: int(x),   "(int) Size of the nx x ny grid of surveys. This sets up nx x ny surveys each taken after moving -x/yStep motor steps"],
                    '-ny'    : ['2',       lambda x: int(x),   "(int) Size of the nx x ny grid of surveys. This sets up nx x ny surveys each taken after moving -x/yStep motor steps"],
                    '-xStep' : ['20',      lambda x: int(x),   "(int) Number of motor steps between surveys in the X direction. Negative value snakes course grid in opposite direction"],
                    '-yStep' : ['20',      lambda x: int(x),   "(int) Number of motor steps between surveys in the Y+ direction. Negative value reverses to Y- direction"],
                    '-zStep' : ['500',     lambda x: int(x),   "(int) Number of motor steps to move in +Z (upwards) before moving the tip in x/y"],
                    '-xyV'   : ['120',     lambda x: float(x), "(float) Piezo voltage when moving motor steps in xy direction"],
                    '-zV'    : ['180',     lambda x: float(x), "(float) Piezo voltage when moving motor steps in z direction"],
                    '-xyF'   : ['1100',    lambda x: float(x), "(float) Piezo frequency when moving motor steps in xy direction"],
                    '-zF'    : ['1100',    lambda x: float(x), "(float) Piezo frequency when moving motor steps in z direction"],
                    }
        
        if(_help): return arg_dict
        
        args = survey2Params
        if(not args):
            error,user_arg_dict = self.userArgs(arg_dict,user_args)
            if(error): return error + "\nRun ```help survey2``` if you're unsure."
            
            args = self.unpackArgs(user_arg_dict)
            if(self.run_mode == 'react'):   # React interface passes scan size and spacing in units of nm. convert to m
                args[4] *= 1e-9
                args[5] *= 1e-9
        
        func = lambda : self.scanbot.survey2(*args)
        return self.threadTask(func)
    
    def biasDep(self,user_args,_help=False):
        arg_dict = {'-n'   : ['5',          lambda x: int(x),   "(int) Number of images to take b/w initial and final bias"],
                    '-bdc' : ['-1',         lambda x: float(x), "(float) Bias of the drift correction images (V). 0 = dc off"],
                    '-tdc' : ['0.3',        lambda x: float(x), "(float) Time per line for drift correction images (s)"],
                    '-tbdc': ['1',          lambda x: float(x), "(float) Backward direction speed multiplier for drift correct image. E.g. 1=same speed, 2=twice as fast, 0.5=half speed"],
                    '-pxdc': ['128',        lambda x: int(x),   "(int) Number of pixels in drift correct images."],
                    '-lxdc': ['0',          lambda x: int(x),   "(int) Number of lines in drift correct image. 0=keep same ratio as px:lx"],
                    '-bi'  : ['-1',         lambda x: float(x), "(float) Initial Bias (V)"],
                    '-bf'  : ['1',          lambda x: float(x), "(float) Final Bias (V)"],
                    '-px'  : ['-default',   lambda x: int(x),   "(int) Number of pixels in images"],
                    '-lx'  : ['0',          lambda x: int(x),   "(int) Number of lines in images. 0=same as px"],
                    '-tlf' : ['-default',   lambda x: float(x), "(float) Time per line (forward direction) (s)"],
                    '-tb'  : ['1',          lambda x: float(x), "(float) Backward direction speed multiplier. E.g. 1=same speed, 2=twice as fast, 0.5=half speed"],
                    '-s'   : ['sb-biasdep', lambda x: str(x),   "(str) Suffix for the set of bias dep sxm files"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help bias_dep``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        func = lambda : self.scanbot.biasDep(*args)
        return self.threadTask(func)
    
    def stsGrid(self,user_args,_help=False):
        arg_dict = {'-NDC' : ['5',          lambda x: int(x),   "(int) Take a drift correction image after every NDC STS acquisitions. 0 = off"],
                    '-VDC' : ['-1',         lambda x: float(x), "(float) Bias of the drift correction images (V). 0 = dc off"],
                    '-IDC' : ['10e-12',     lambda x: float(x), "(float) Bias of the drift correction images (V). 0 = dc off"],
                    '-tdc' : ['0',          lambda x: float(x), "(float) Time per line for drift correction images (s). 0 = leave settings in nanonis"],
                    '-tbdc': ['1',          lambda x: float(x), "(float) Backward direction speed multiplier for drift correct image. E.g. 1=same speed, 2=twice as fast, 0.5=half speed"],
                    '-pxdc': ['0',          lambda x: int(x),   "(int) Number of pixels in drift correct images. 0 = leave settings in nanonis"],
                    '-Vset': ['0',          lambda x: float(x), "(float) Bias applied to the tip when moving between grid points (V). 0 = do not change"],
                    '-Iset': ['0',          lambda x: float(x), "(float) Setpoint current when the tip is moving between points (A). 0 = do not change"],
                    '-Vmov': ['0',          lambda x: float(x), "(float) Bias applied to the tip when moving between grid points (V). 0 = do not change"],
                    '-Imov': ['0',          lambda x: float(x), "(float) Setpoint current when the tip is moving between points (A). 0 = do not change"],
                    '-path': ['',           lambda x: str(x),   "(str) Full path to save pickled grid data. Leave blank to use current nanonis path."],
                    '-s'   : ['sb-stsgrid', lambda x: str(x),   "(str) Suffix for the saved filename"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help bias_dep``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict,keep_as_dict=True)
        
        if(self.run_mode == 'react'):   # React interface passes currents in as units of pm. convert to m
            args['-IDC']  *= 1e-12
            args['-Iset'] *= 1e-12
            args['-Imov'] *= 1e-12

        func = lambda : self.scanbot.stsGrid(args)
        return self.threadTask(func)

    def zdep(self,user_args,_help=False):
        arg_dict = {'-zi'       : ['-10e-12',  lambda x: float(x), "(float) Initial tip lift from setpoint (m)"],
                    '-zf'       : ['10e-12',   lambda x: float(x), "(float) Final tip lift from setpoint (m)"],
                    '-nz'       : ['5',        lambda x: int(x),   "(int) Number of scans between zi and zf"],
                    '-iset'     : ['-default', lambda x: float(x), "(float) Setpoint current (A). Limited to 1 nA. zi and zf are relative to this setpoint"],
                    '-bset'     : ['-default', lambda x: float(x), "(float) Setpoint bias (V)"],
                    '-dciset'   : ['-default', lambda x: float(x), "(float) Setpoint current for drift correction (A)"],
                    '-bias'     : ['-default', lambda x: float(x), "(float) Scan bias during constant height (V)"],
                    '-dcbias'   : ['-default', lambda x: float(x), "(float) Scan bias during drift correction. 0 = dc off(V)"],
                    '-ft'       : ['-default', lambda x: float(x), "(float) Forward scan time per line during constant height (s)"],
                    '-bt'       : ['-default', lambda x: float(x), "(float) Backward scan time per line during constant height (s)"],
                    '-dct'      : ['-default', lambda x: float(x), "(float) Forward and backward time per line during drift correction (s)"],
                    '-px'       : ['-default', lambda x: int(x),   "(int) Number of pixels for constant height image"],
                    '-dcpx'     : ['-default', lambda x: int(x),   "(int) Number of pixels for drift correction image"],
                    '-lx'       : ['0',        lambda x: int(x),   "(int) Number of lines for constant height image. 0=same as -px"],
                    '-dclx'     : ['0',        lambda x: int(x),   "(int) Number of lines for drift correction image. 0=same as -dcpx"],
                    '-s'        : ['sb-zdep',  lambda x: str(x),   "(str) Suffix at the end of autosaved sxm files"],
                    '-gif'      : ['1',        lambda x: int(x),   "(int) Turn scans into a gif after completion. 0=No,1=Yes"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help zdep``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        func = lambda : self.scanbot.zdep(*args)
        return self.threadTask(func)
    
    def registration(self,user_args,_help=False):
        arg_dict = {'-zset'     : ['0',        lambda x: float(x), "(float) Initial tip lift from setpoint (m)"],
                    '-iset'     : ['-default', lambda x: float(x), "(float) Setpoint current (A). Limited to 1 nA. zi and zf are relative to this setpoint"],
                    '-bset'     : ['-default', lambda x: float(x), "(float) Bias at which the setpoint is measured (V)"],
                    '-bias'     : ['-default', lambda x: float(x), "(float) Scan bias during constant height (V)"],
                    '-ft'       : ['-default', lambda x: float(x), "(float) Forward scan time per line during constant height (s)"],
                    '-bt'       : ['-default', lambda x: float(x), "(float) Backward scan time per line during constant height (s)"],
                    '-px'       : ['-default', lambda x: int(x),   "(int) Number of pixels for constant height image"],
                    '-lx'       : ['0',        lambda x: int(x),   "(int) Number of lines for constant height image. 0=same as -px"],
                    '-lz'       : ['0',        lambda x: int(x),   "(int) Line number to perform tip lift -dz. lz is measured from the TOP of the scan frame, regardless of whether scan direction is up or down. i.e. lz=0 is at the top of the frame"],
                    '-dz'       : ['0',        lambda x: float(x), "(float) Tip lift (m) at line number -lz"],
                    '-dir'      : ['down',     lambda x: str(x),   "(str) Scan dirction. Can be either 'up' or 'down'"],
                    '-s'        : ['sb-rego',  lambda x: str(x),   "(str) Suffix at the end of autosaved sxm files"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help afm_registration``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        func = lambda : self.scanbot.registration(*args)
        return self.threadTask(func)
    
###############################################################################
# Tip Actions
###############################################################################
    def moveArea(self,user_args,_help=False):
        arg_dict = {'-up'    : ['20',   lambda x: int(x),   "(int) Steps to go up before moving across. min 10"],
                    '-upV'   : ['270',  lambda x: float(x), "(float) Controller amplitude during up motor steps"],
                    '-upF'   : ['2100', lambda x: float(x), "(float) Controller frequency during up motor steps"],
                    '-dir'   : ['Y+',   lambda x: str(x),   "(str) Direction to go across (either X+, X-, Y+, Y-)"],
                    '-steps' : ['10',   lambda x: int(x),   "(int) Steps to move across after moving -up number of steps"],
                    '-dirV'  : ['130',  lambda x: float(x), "(float) Controller amplitude during across motor steps"],
                    '-dirF'  : ['2100', lambda x: float(x), "(float) Controller frequency during across motor steps"],
                    '-zon'   : ['1',    lambda x: int(x),   "(int) Turn the z-controller on after approaching. 1=on, 0=off"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help move_area``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        self.scanbot.moveArea(*args)
    
    def tipShape(self,user_args,_help=False):
        arg_dict = {}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help tip_shape``` if you're unsure."
        
        self.scanbot.tipShape()
        
    def tipShapeProps(self,user_args,_help=False):
        arg_dict = {'-sod'    : ['-default',lambda x: float(x), "(float) Switch off delay: the time (s) during which the Z position is averaged before switching the Z controller off"],
                    '-cb'     : ['-default',lambda x: int(x),   "(int) Change bias flag (0=Nanonis,1=Change Bias,2=Don't Change"],
                    '-b1'     : ['-default',lambda x: float(x), "(float) The value applied to the Bias signal if cb is true"],
                    '-z1'     : ['-default',lambda x: float(x), "(float) First tip lift (m) (i.e. -2e-9)"],
                    '-t1'     : ['-default',lambda x: float(x), "(float) Defines the time to ramp Z from current Z position to z1"],
                    '-b2'     : ['-default',lambda x: float(x), "(float) Bias voltage applied just after the first Z ramping"],
                    '-t2'     : ['-default',lambda x: float(x), "(float) Time to wait after applying the Bias Lift value b2"],
                    '-z2'     : ['-default',lambda x: float(x), "(float) Height the tip is going to ramp for the second time (m) i.e. +5nm"],
                    '-t3'     : ['-default',lambda x: float(x), "(float) Time to ramp Z in the second ramping [s]."],
                    '-wait'   : ['-default',lambda x: float(x), "(float) Time to wait after restoring the initial Bias voltage"],
                    '-fb'     : ['-default',lambda x: int(x),   "(int) Restore the initial Z-Controller status. 0: off. 1: on"]}
        
        if(_help): return arg_dict
        
        if(not len(user_args)): return self.scanbot.tipShapePropsGet()
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help tip_shape_props``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        self.scanbot.tipShapeProps(*args)

###############################################################################
# Auto STM
###############################################################################
    def autoInit(self,user_args,_help=False):
        arg_dict = {'-light'      : ['0',   lambda x: int(x),   "(int) Flag to turn the light on/off before/after initialisation. This uses hk_light.turn_on() and hk_light.turn_off() functions. 0=Don't, 1=Do"],
                    '-cameraPort' : ['0',   lambda x: int(x),   "(int) cv2 camera port - usually 0 for desktops or 1 for laptops with an inbuilt camera."],
                    '-demo'       : ['0',   lambda x: int(x),   "(int) Load in an mp4 recording of the tip moving instead of using live feed"],}
        
        if(_help): return arg_dict
        
        arg_dict['-reactInit'] = ['0', lambda x: int(x), "(int) User-hidden flag when running in react mode. 1=running from react - use data in ./autoInit/"]
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help auto_init``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        if(self.run_mode == 'react'):
            return self.scanbot.autoInit(*args)
        
        func = lambda : self.scanbot.autoInit(*args)
        return self.threadTask(func)
    
    def moveTipToSample(self,user_args,_help=False):
        return self.moveTipToTarget(user_args,_help=_help,target="sample")
    
    def moveTipToClean(self,user_args,_help=False):
        return self.moveTipToTarget(user_args,_help=_help,target="clean")
    
    def moveTipToTarget(self,user_args,_help=False,target=""):
        arg_dict = {'-light'      : ['0',   lambda x: int(x),   "(int) Flag to turn the light on before moving and off after moving. This uses hk_light.turn_on() and hk_light.turn_off() functions. 0=Don't, 1=Do"],
                    '-cameraPort' : ['0',   lambda x: int(x),   "(int) cv2 camera port - usually 0 for desktops or 1 for laptops with an inbuilt camera."],
                    '-xStep'      : ['100', lambda x: int(x),   "(int) Number of motor steps in the X direction before updating tip position. More=Faster but might lose the tip"],
                    '-zStep'      : ['250', lambda x: int(x),   "(int) Number of motor steps to move in +Z (upwards) before updating tip position. More=Faster but might lose the tip"],
                    '-xV'         : ['130', lambda x: float(x), "(float) Piezo voltage when moving motor steps in x direction"],
                    '-zV'         : ['180', lambda x: float(x), "(float) Piezo voltage when moving motor steps in z direction"],
                    '-xF'         : ['1100',lambda x: float(x), "(float) Piezo frequency when moving motor steps in x direction"],
                    '-zF'         : ['1100',lambda x: float(x), "(float) Piezo frequency when moving motor steps in z direction"],
                    '-approach'   : ['1',   lambda x: int(x),   "(int) Approach when tip reaches target. 0=No,1=Yes"],
                    '-tipshape'   : ['0',   lambda x: int(x),   "(int) Flag to initiate auto_tip_shape on approach (applies to move_tip_to_clean only)"],
                    '-hk_tipShape': ['0',   lambda x: int(x),   "(int) Flag to call hk_tipShape when auto tip shaping. 1=Yes, 0=No"],
                    '-return'     : ['0',   lambda x: int(x),   "(int) Return to sample after tipshaping (applies to move_tip_to_clean when -tipshape=1)"],
                    '-run'        : ['',    lambda x: str(x),   "(str) Name of the command to run upon appraching sample (applies when -return=1). Can be one of 'survey' or 'survey2'."]}
        
        if(_help): return arg_dict
        
        if(self.run_mode != 'c' and self.run_mode != 'react'): return "This function is not available."
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help move_tip_to_" + target + "``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        func = lambda : self.scanbot.moveTipToTarget(*args,target=target)
        return self.threadTask(func)
        
    def autoTipShape(self,user_args,_help=False):
        arg_dict = {'-n'    : ['10',        lambda x: int(x),   "(int) Max number of tip shapes to perform"],
                    '-wh'   : ['10e-9',     lambda x: float(x), "(float) Size of the square scan frame when imaging the clean surface"],
                    '-sym'  : ['0.7',       lambda x: float(x), "(float) Minimum circularity requirement. 0=don't care, 1=perfectly circle"],
                    '-size' : ['1.2',       lambda x: float(x), "(float) Max size of the desired tip imprint in units of nm2"],
                    '-zQA'  : ['-0.9e-9',   lambda x: float(x), "(float) z-lift when performing a light tip shape to asses quality of tip (m)"],
                    '-ztip' : ['-1.5e-9',   lambda x: float(x), "(float) z-lift when performing a tip shape to alter the tip (m)"],
                    '-rng'  : ['1',         lambda x: int(x),   "(int) Flag to randomise -ztip from 1 nm to -ztip value. 1=Yes, 0=No"],
                    '-st'   : ['10',        lambda x: int(x),   "(int) Drift compensation time (s)"],
                    '-demo' : ['0',         lambda x: int(x),   "(int) Flag to call in demo mode (1=demo, 0=live)"],
                    '-hk_tipShape' : ['0',  lambda x: int(x),   "(int) Flag to call the hook hk_tipShape. Use this hook to adjust the tip shaping parameters based on size/symmetry scores, or based on the image of the tip imprint itself. 0=Don't call, 1=Call"],}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help auto_tip_shape``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        if(self.run_mode == 'react'):   # React interface passes scan size and spacing in units of nm. convert to m
            args[1] *= 1e-9
            args[4] *= 1e-9
            args[5] *= 1e-9
        
        func = lambda : self.scanbot.autoTipShape(*args)
        return self.threadTask(func)
    
###############################################################################
# Configuration
###############################################################################
    def setPortList(self,portList,_help=False):
        arg_dict = {'' : ['6501 6502 6503 6504', 0, "(int array) List of ports delimited by a space"]}
        
        if(_help): return arg_dict
        
        try:
            portList = [int(x) for x in portList]
        except:
            return "Invalid portlis. Ports must be integers delimited by spaces"
        
        if(not portList): return "Port list cannot be empty"
        
        self.portList = portList
    
    def setIP(self,IP,_help=False):
        arg_dict = {'' : ['127.0.0.1', lambda x: str(x), "(string) IP Address"]}
        
        if(_help): return arg_dict
        
        if(len(IP) != 1): return "Invalid IP: " + str(IP)
        try:
            IP = IP[0]
            ipaddress.ip_address(IP)
            self.IP = IP
            return
        except Exception as e:
            return str(e)
        
    def setPath(self,path,_help=False):
        arg_dict = {'' : ['', 0, "(string) Sets upload path. Creates the directory if path does not exist"]}
        
        if(_help): return arg_dict
        
        if(len(path) != 1): return
        path = path[0]
        
        try:
            self.path = path
            if(not self.path.endswith('/')):
                self.path += '/'
            Path(self.path).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return str(e)
        
    def plotChannel(self,user_args,_help=False):
        arg_dict = {'-c' : ['', lambda x: str(x), "(str) Set default channel for scanbot to look at. '' means no change. Run without options to see available channels"],
                    '-a' : ['', lambda x: str(x), "(str) Add channel to the scan buffer. '' means no change. Run without options to see available channels"],
                    '-r' : ['', lambda x: str(x), "(str) Remove channel from the scan buffer. '' means no change. Run without options to see available channels"]}
        
        if(_help): return arg_dict
        
        if(not len(user_args)): return self.scanbot.plotChannel()
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help plot_channel``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        return self.scanbot.plotChannel(*args)
    
    def getStatus(self,user_args,_help=False):
        return ("Running flag: " + global_.running.is_set() + "\n" +
                "Pause flag:   " + global_.pause.is_set())
    
    def setCrashSafety(self,user_args,_help=False):
        arg_dict = {'-c' : ['-1', lambda x: float(x), "(float) When moving the course piezos, a current above this value will be considered a crash and the tip will retract. -1 means no change"],
                    '-V' : ['-1', lambda x: float(x), "(float) Voltage applied to the 'Z' piezo during tip retraction after a crash is detected. -1 means no change"],
                    '-F' : ['-1', lambda x: float(x), "(float) Frequency applied to the 'Z' piezo during tip retraction after a crash is detected. -1 means no change"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help set_crash_safety``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        if(args[0] > 0): self.scanbot.safeCurrent  = args[0]
        if(args[1] > 0): self.scanbot.safeRetractV = args[1]
        if(args[2] > 0): self.scanbot.safeRetractF = args[2]
        
        self.sendReply("----------------")
        return(self.getCrashSafety(user_args=[]))
    
    def getCrashSafety(self,user_args,_help=False):
        message  = "Safe current:           " + str(self.scanbot.safeCurrent*1e9) + " nA\n"
        message += "Safe retract Voltage:   " + str(self.scanbot.safeRetractV) + " V\n"
        message += "Safe retract Frequency: " + str(self.scanbot.safeRetractF) + " Hz\n"
        return message
        
###############################################################################
# Comms
###############################################################################
    def handle_message(self, message):
        """
        Process commands from incoming messages.
        Command format:
            for commands that take optional arguments:
                command_name -arg1=x -arg2=y
            for commands that take mandatory arguments, delimit with space:
                command_name arg1 arg2

        Parameters
        ----------
        message     : Incoming message

        """
        messageContent   = message

        command = messageContent.split(' ')[0].lower()
        args    = messageContent.split(' ')[1:]

        if(args and '=' in args[0]):
            args = ['-' + arg for arg in messageContent.split(' -')[1:]]
        
        if(self.hk_commands and command in self.hk_commands.commands):
            self.hk_commands.commands[command](args)
            return
        
        if(not command in self.commands):
            print("Invalid command. Run *help* to see command list")
            return

        self.commands[command](args)
        
       
    def sendPNG(self,pngFilename):
        path = self.module_dir + pngFilename
        
        if(self.run_mode == 'react'):
            timestamp = time.time()
            Path(self.module_dir + 'temp').mkdir(parents=True, exist_ok=True)
            shutil.copy(path,self.module_dir + 'temp/' + str(timestamp) + '_' + pngFilename)
            
        os.replace(path, self.path + pngFilename)
        print(self.path + pngFilename)
    
    def sendReply(self,message):
        if(self.run_mode == 'react'):
            print(message)
        else:
            print("Scanbot: " + message)
###############################################################################
# Misc
###############################################################################
    def getAction(self):
        """
        Returns the current action of Scanbot.
        """
        return self.scanbot.currentAction
    
    def testConnection(self):
        """
        Used by the react app to see if we can connect to nanonis.

        Returns
        -------
        status : bool
            True if connection successful, False if not
        """
        status = True
        try:
            from nanonisTCP.Bias import Bias
            NTCP,connection_error = self.scanbot.connect()                      # Connect to nanonis via TCP
            biasModule = Bias(NTCP)
            bias = biasModule.Get()
            self.scanbot.disconnect(NTCP)
        except:
            status = False

        return status

    def stop(self,user_args=[],_help=False):
        arg_dict = {'-s' : ['1', lambda x: int(x), "(int) Stop scan in progress. 1=Yes"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help stop``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        if(global_.running.is_set()):
            global_.running.clear()
            global_.pause.clear()
            
            if(args[0] == 1): self.scanbot.stop()
            
            global_.tasks.join()
        else:
            if(args[0] == 1): self.scanbot.stop()
            
    def threadTask(self,func,override=False):
        if(override): self.stop()
        if global_.running.is_set(): return "Error: something already running"
        global_.running.set()
        t = threading.Thread(target=func)
        global_.tasks = t
        t.start()
        
    def _help(self,args):
        if(not len(args)):
            helpStr = "Type ```help <command name>``` for more info\n"
            return helpStr + "\n". join([c for c in self.commands])
        
        command = args[0]
        if(not command in self.commands):
            if(self.hk_commands and not command in self.hk_commands.commands):
                return "Run ```help``` to see a list of valid commands"
        
        try:
            helpStr = "**" + command + "**\n"
            try:
                arg_dict = self.hk_commands.commands[command](args,_help=True)
            except:
                arg_dict = self.commands[command](args,_help=True)
            for key,value in arg_dict.items():
                if(key == 'help'): continue
                if(key):
                    helpStr += "```"
                    helpStr += key + "```: " 
                helpStr += value[2] + ". "
                if(value[0]):
                    helpStr += "Default: ```" +  value[0].replace("-default","nanonis settings") 
                    helpStr += "```"
                helpStr += "\n"
        except:
            return "No help for this command"
        
        return helpStr

    def userArgs(self,arg_dict,user_args):
        error = ""
        for arg in user_args:                                                   # Override the defaults if user inputs them
            try:
                key,value = arg.split('=')
            except:
                error = "Invalid argument"
                break
            if(not key in arg_dict):
                error = "invalid argument: " + key                              # return error message
                break
            try:
                arg_dict[key][1](value)                                         # Validate the value
            except:
                error  = "Invalid value for arg " + key + "."                   # Error if the value doesn't match the required data type
                break
            
            arg_dict[key][0] = value
        
        return [error,arg_dict]
    
    def unpackArgs(self,arg_dict,keep_as_dict=False):
        args = []
        if(keep_as_dict): args = arg_dict.copy()
        for key,value in arg_dict.items():
            if(keep_as_dict):
                try:
                    args[key] = arg_dict[key][1](value[0])
                except:
                    args[key] = value[0]
                continue

            if(value[0] == "-default"):                                         # If the value is -default...
                args.append("-default")                                         # leave it so the function can retrieve the value from nanonis
                continue
            
            args.append(value[1](value[0]))                                     # Convert the string into data type
        return args
    
    def _quit(self,arg_dict=[]):
        sys.exit()

    def restart(self,run_mode,module_dir="./"):
        self.stop(user_args=[])
        self.__init__(run_mode=run_mode,module_dir=module_dir)

###############################################################################
# Run
###############################################################################
finish = False
    
if('-c' in sys.argv and not finish):
    print("Console mode: type 'exit' to end scanbot")
    handler_class = scanbot_interface(run_mode='c')
    while(True):
        message = input("User: ")
        if(message == 'exit'):
            break
        handler_class.handle_message(message)
    
    finish = True

if('-react' in sys.argv and not finish):
    handler_class = scanbot_interface(run_mode='react')
    while(True):
        message = input("User: ")
        if(message == 'exit'):
            break
        handler_class.handle_message(message)
    
    finish = True
    