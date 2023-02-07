# -*- coding: utf-8 -*-
"""
Created on Fri August 8 22:06:37 2022

@author: Julian Ceddia
"""

from scanbot import scanbot

import zulip

import os
import sys
import subprocess
from pathlib import Path

import ipaddress

import global_
import threading

class scanbot_interface(object):
    bot_message = []
    bot_handler = []
    validUploadMethods = ['path','zulip','firebase','no_upload']
    
###############################################################################
# Constructor
###############################################################################
    def __init__(self):
        print("Initialising app...")
        self.scanbot = scanbot(self)
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
        initDict = {'zuliprc'                   : '',                           # Zulip rc file. See https://zulip.com/api/running-bots
                    'upload_method'             : 'no_upload',                  # Ping data via this channel.
                    'path'                      : 'sbData',                     # Path to save data (if upload_method=path)
                    'firebase_credentials'      : '',                           # Credentials for firebase (if upload_method=firebase)
                    'firebase_storage_bucket'   : '',                           # Firebase bucket. Firebase path uses "path" key
                    'port_list'                 : '6501,6502,6503,6504',        # Ports (see nanonis => Main Options => TCP Programming Interface)
                    'ip'                        : '127.0.0.1',                  # IP of the pc controlling nanonis
                    'creeplist'                 : '',                           # IP addresses to creep
                    'notify_list'               : '',                           # Comma delimited zulip users to @notify when sending data
                    'temp_calibration_curve'    : '',                           # Path to temp calibration curve (see nanonis Temperature modules)
                    'topo_basename'             : '',                           # basename for topographic images
                    'send_to_cloud'             : '0',                          # Flag to send data to the cloud
                    'cloud_path'                : ''}                           # user@clouddatabase:path.
        
        try:
            with open('scanbot_config.ini','r') as f:                           # Go through the config file to see what defaults need to be overwritten
                line = "begin"
                while(line):
                    line = f.readline()[:-1]
                    if(line.startswith('#')): print(line); continue             # Comment
                    if(not '=' in line):
                        print("Warning, invalid line in config file: " + line)
                        continue
                    key, value = line.split('=')                                # Format for valid line is "Key=Value"
                    if(not key in initDict):                                    # Key must be one of initDict keys
                        print("Invalid key in scanbot_config.txt: " + key)
                        continue
                    initDict[key] = value                                       # Overwrite value
        except:
            print("Config file not found, using defaults...")
        
        self.zuliprc      = initDict['zuliprc']
        
        self.path         = initDict['path']
        
        self.uploadMethod = initDict['upload_method']
        
        if(self.uploadMethod == 'zulip'):
            if(not self.zuliprc):
                raise Exception("Check config file. zuliprc require for upload_method=zulip")
        
        if(self.uploadMethod in ['path','firebase']):
            if(not self.path):
                raise Exception("Check config file. Invalid path for upload_method=" + self.uploadMethod)
        
        if(self.uploadMethod not in self.validUploadMethods):
            raise Exception("Check config file. Invalid upload_method.\nMust be one of path, zulip, firebase")
            
        if(self.uploadMethod == 'path'):
            Path(self.path).mkdir(parents=True, exist_ok=True)
            if(not self.path.endswith('/')):
                self.path += '/'
        
        self.firebaseCert = initDict['firebase_credentials']
        self.firebaseStorageBucket = initDict['firebase_storage_bucket']
        
        if(self.uploadMethod == 'firebase'):
            if(not self.firebaseStorageBucket):
                raise Exception("Storage bucket must be provided for upload_method=firebase")
            if(not self.path):
                raise Exception("Storage path must be provided for upload_method=firebase")
            if(not self.path.endswith('/')):
                self.path += '/'
            self.firebaseInit()
        
        if(self.setPortList(initDict['port_list'].replace(',',' ').split(' '))):
            raise Exception("Check port_list in config file. Must be space or comma delimited.")
            
        if(self.setIP([initDict['ip']])):
            raise Exception("Check config file... Invalid IP.")
        
        self.notifyUserList = []
        if(initDict['notify_list']):
            self.notifyUserList = initDict['notify_list'].split(',')
        
        self.bot_message = ""
        self.zulipClient = []
        if(self.zuliprc):
            self.zulipClient = zulip.Client(config_file=self.zuliprc)
        
        self.tempCurve = initDict['temp_calibration_curve']
        
        self.topoBasename = initDict['topo_basename']
        
        self.sendToCloud = initDict['send_to_cloud']
        self.cloudPath = initDict['cloud_path']
        if(self.sendToCloud == 1):
            if(not self.cloudPath):
                raise Exception("Check config file... cloud path not provided")
                
        self.loadWhitelist()
        
    def firebaseInit(self):
        try:
            import firebase_admin
            from firebase_admin import credentials
            print("Initialising firebase app")
            cred = credentials.Certificate(self.firebaseCert)                   # Your firebase credentials
            firebase_admin.initialize_app(cred, {
                'storageBucket': self.firebaseStorageBucket                     # Your firebase storage bucket
            })
        except Exception as e:
            print("Firebase not initialised...")
            print(e)
        
    def loadWhitelist(self):
        self.whitelist = []
        try:
            print("Loading whitelist.txt...")
            with open('whitelist.txt', 'r') as f:
                d = f.read()
                self.whitelist = d.split('\n')[:-1]
        except:
            print('No whitelist found... create one with add_user')
    
    def initGlobals(self):
        global_.tasks   = []
        global_.running = threading.Event()                                     # event to stop threads
        global_.pause   = threading.Event()                                     # event to pause threads
        
    def initCommandDict(self):
        self.commands = {
                        # Configuration commands
                         'help'             : self._help,
                         'set_ip'           : self.setIP,
                         'get_ip'           : lambda args: self.IP,
                         'set_portlist'     : self.setPortList,
                         'get_portlist'     : lambda args: self.portList,
                         'set_upload_method': self.setUploadMethod,
                         'get_upload_method': lambda args: self.uploadMethod,
                         'add_user'         : self.addUser,
                         'get_users'        : lambda args: str(self.whitelist),
                         'set_path'         : self.setPath,
                         'get_path'         : lambda args: self.path,
                         'plot_channel'     : self.plotChannel,
                        # Scanbot commands
                         'stop'             : self.stop,
                         'plot'             : self.plot,
                         'survey'           : self.survey,
                         'survey2'          : self.survey2,
                         'move_area'        : self.moveArea,
                         'zdep'             : self.zdep,
                         'afm_registration' : self.registration,
                        # Misc
                         'quit'             : self._quit
                         
        }
        
###############################################################################
# Scanbot Commands
###############################################################################
    def stop(self,user_args,_help=False):
        arg_dict = {'-s' : ['1', lambda x: int(x), "(int) Stop scan in progress. 1=Yes"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help plot``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        if(global_.running.is_set()):
            global_.running.clear()
            global_.pause.clear()
            
            if(args[0] == 1): self.scanbot.stop()
            
            global_.tasks.join()
        else:
            if(args[0] == 1): self.scanbot.stop()
        
    def plot(self,user_args,_help=False):
        arg_dict = {'-c' : ['-1', lambda x: int(x), "(int) Channel to plot. -1 plots the default channel which can be set using plot_channel"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help plot``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        return self.scanbot.plot(*args)
    
    def survey(self,user_args,_help=False):
        arg_dict = {'-bias' : ['-default', lambda x: float(x), "(float) Scan bias"],
                    '-n'    : ['5',        lambda x: int(x),   "(int) Size of the nxn grid of scans"],
                    '-i'    : ['1',        lambda x: int(x),   "(int) Start the grid from this index"],
                    '-s'    : ['scanbot',  lambda x: str(x),   "(str) Suffix at the end of autosaved sxm files"],
                    '-xy'   : ['-default', lambda x: float(x), "(float) Length and width of the scan frame (m)"],
                    '-dx'   : ['-default', lambda x: float(x), "(float) Scan grid spacing (m). Default is -xy"],
                    '-px'   : ['-default', lambda x: int(x),   "(int) Number of pixels"],
                    '-st'   : ['10',       lambda x: float(x), "(float) Drift compensation time (s)"],
                    '-stitch':['1',        lambda x: float(x), "(int) Return the stitched survey after completion. 1: Yes, else No"],
                    '-hook' : ['',         lambda x: str(x),   "(str) Name of a custom python script to call after each image."],
                    '-autotip': ['0',      lambda x: str(x),   "(int) Automatic tip shaping. 0=off, 1=on. Properties for the auto tip shaper should be set with auto_tip_shaper command"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help survey``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        func = lambda : self.scanbot.survey(*args,message=self.bot_message.copy())
        return self.threadTask(func)
    
    def survey2(self,user_args,_help=False):
        arg_dict = {'-bias' : ['-default', lambda x: float(x), "(float) Scan bias"],
                    '-n'    : ['5',        lambda x: int(x),   "(int) Size of the nxn grid of scans within each survey"],
                    '-i'    : ['1',        lambda x: int(x),   "(int) Start the grid from this index"],
                    '-s'    : ['scanbot',  lambda x: str(x),   "(str) Suffix at the end of autosaved sxm files"],
                    '-xy'   : ['-default', lambda x: float(x), "(float) Length and width of the scan frame (m)"],
                    '-dx'   : ['-default', lambda x: float(x), "(float) Scan grid spacing (m)"],
                    '-px'   : ['-default', lambda x: int(x),   "(int) Number of pixels"],
                    '-st'   : ['10',       lambda x: float(x), "(float) Drift compensation time (s)"],
                    '-stitch':['1',        lambda x: float(x), "(int) Return the stitched survey after completion. 1: Yes, else No"],
                    '-hook' : ['',         lambda x: str(x),   "(str) Name of a custom python script to call after each image."],
                    '-autotip': ['0',      lambda x: str(x),   "(int) Automatic tip shaping. 0=off, 1=on. Properties for the auto tip shaper should be set with auto_tip_shaper command"],
                    
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
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help survey2``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        func = lambda : self.scanbot.survey2(*args,message=self.bot_message.copy())
        return self.threadTask(func)
        
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
        
        self.scanbot.moveArea(*args,message=self.bot_message.copy())
    
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
        
        func = lambda : self.scanbot.zdep(*args,message=self.bot_message.copy())
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
        
        func = lambda : self.scanbot.registration(*args,message=self.bot_message.copy())
        return self.threadTask(func)
###############################################################################
# Config Commands
###############################################################################
    def setPortList(self,portList,_help=False):
        arg_dict = {'' : ['6501 6502 6503 6504', 0, "(int array) List of ports delimited by a space"]}
        
        if(_help): return arg_dict
        
        try:
            portList = [int(x) for x in portList]
        except:
            self.reactToMessage('cross_mark')
            return "Invalid portlis. Ports must be integers delimited by spaces"
        
        if(not portList): return self.reactToMessage('cross_mark')
        
        self.portList = portList
        self.reactToMessage('computer')
    
    def setIP(self,IP,_help=False):
        arg_dict = {'' : ['127.0.0.1', lambda x: str(x), "(string) IP Address"]}
        
        if(_help): return arg_dict
        
        if(len(IP) != 1): return "Invalid IP: " + str(IP)
        try:
            IP = IP[0]
            ipaddress.ip_address(IP)
            self.IP = IP
            self.reactToMessage('computer')
            return
        except Exception as e:
            self.reactToMessage('cross_mark')
            return str(e)
        
    def setUploadMethod(self,uploadMethod,_help=False):
        arg_dict = {'' : ['', lambda x: str(x), "(string) Data upload method. One of " + ', '.join(self.validUploadMethods)]}
        
        if(_help): return arg_dict
        
        if(len(uploadMethod) != 1): self.reactToMessage('cross_mark'); return
        
        uploadMethod = uploadMethod[0].lower()
        if(not uploadMethod in self.validUploadMethods):
            self.reactToMessage('cross_mark')
            return "Invalid Method. Available methods:\n" + "\n". join(self.validUploadMethods)
        
        if(uploadMethod == 'path'):
            Path(self.path).mkdir(parents=True, exist_ok=True)
            if(not self.path.endswith('/')): self.path += '/'
            
        self.uploadMethod = uploadMethod
        self.reactToMessage('all_good')
        
    def addUser(self,user,_help=False):
        arg_dict = {'' : ['', 0, "(string) Add user email to whitelist (one at a time)"]}
        
        if(_help): return arg_dict
        
        if(len(user) != 1): self.reactToMessage("cross_mark"); return
        if(' ' in user[0]): self.reactToMessage("cross_mark"); return           # Replace this with proper email validation
        try:
            self.whitelist.append(user[0])
            with open('whitelist.txt', 'w') as f:
                for w in self.whitelist:
                    f.write(w+'\n')
            self.reactToMessage('all_good')
        except Exception as e:
            return str(e)
    
    def setPath(self,path,_help=False):
        arg_dict = {'' : ['', 0, "(string) Sets upload path. Creates the directory if path does not exist"]}
        
        if(_help): return arg_dict
        
        if(len(path) != 1): self.reactToMessage("cross_mark"); return
        path = path[0]
        
        try:
            if(self.uploadMethod == 'firebase'):
                self.sendReply("set_path not supported for Firebase, yet")
                
            if(self.uploadMethod == 'path'):
                self.path = path
                if(not self.path.endswith('/')):
                    self.path += '/'
                Path(self.path).mkdir(parents=True, exist_ok=True)
                self.reactToMessage('all_good')
        except Exception as e:
            return str(e)
        
    def plotChannel(self,user_args,_help=False):
        arg_dict = {'-c' : ['-1', lambda x: int(x), "(int) Set default channel for scanbot to look at. -1 means no change. Run without options to see available channels"],
                    '-a' : ['-1', lambda x: int(x), "(int) Add channel to the scan buffer. -1 means no change. Run without options to see available channels"],
                    '-r' : ['-1', lambda x: int(x), "(int) Remove channel from the scan buffer. -1 means no change. Run without options to see available channels"]}
        
        if(_help): return arg_dict
        
        if(not len(user_args)): return self.scanbot.plotChannel()
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help plot_channel``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        return self.scanbot.plotChannel(*args)
    
    def getStatus(self,user_args,_help=False):
        return ("Running flag: " + global_.running.is_set() + "\n" +
                "Pause flag:   " + global_.pause.is_set())
###############################################################################
# Comms
###############################################################################
    def handle_message(self, message, bot_handler=None):
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
        bot_handler : Zulip only.

        """
        messageContent   = message
        self.bot_message = []
        self.bot_handler = bot_handler
        if(bot_handler):                                                        # If there's a bot_handler, we're communicating via zulip
            if message['sender_email'] not in self.whitelist and self.whitelist:
                self.sendReply(message['sender_email'])
                self.sendReply('access denied')
                return
            
            self.bot_message = message
            messageContent = message['content']
            
        command = messageContent.split(' ')[0].lower()
        args    = messageContent.split(' ')[1:]
        
        if(not command in self.commands):
            reply = "Invalid command. Run *help* to see command list"
            self.sendReply(reply)
            return

        reply = self.commands[command](args)
        
        if(reply): self.sendReply(reply)
    
    def sendReply(self,reply,message=""):
        """
        Send reply text. Currently only supports zulip and console.

        Parameters
        ----------
        reply   : Reply string
        message : Zulip: message params for the specific message to reply ro.
                  If not passed in, replies to the last message sent by user.

        Returns
        -------
        message_id : Returns the message id of the sent message. (zulip only)

        """
        if(not reply): return                                                   # Can't send nothing
        if(self.bot_handler):                                                   # If our reply pathway is zulip
            replyTo = message                                                   # If we're replying to a specific message
            if(not replyTo): replyTo = self.bot_message                         # If we're just replying to the last message sent by user
            self.bot_handler.send_reply(replyTo, reply)                         # Send the message
            return
        
        print(reply)                                                            # Print reply to console
        
    def reactToMessage(self,reaction,message=""):
        """
        Scanbot emoji reaction to message
    
        Parameters
        ----------
        reaction : Emoji name (currently zulip only)
        message  : Specific zulip message to react to. If not passed in, reacts
                   to the last message sent by user.
    
        """
        if(not self.bot_handler):                                               # If we're not using zulip
            print("Scanbot reaction: " + reaction)                              # Send reaction to console
            return
        
        reactTo = message                                                       # If we're reacting to a specific zulip message
        if(not reactTo): reactTo = self.bot_message                             # Otherwise react to the last user message
        react_request = {
            'message_id': reactTo['id'],                                        # Message ID to react to
            'emoji_name': reaction,                                             # Emoji scanbot reacts with
            }
        self.zulipClient.add_reaction(react_request)                            # API call to react to the message
        
    def sendPNG(self,pngFilename,notify=True,message=""):
        notifyString = ""
        if(notify):
            for user in self.notifyUserList:
                notifyString += "@**" + user + "** "
            
        path = os.getcwd() + '/' + pngFilename
        path = Path(path)
        path = path.resolve()
        
        if(self.uploadMethod == 'zulip'):
            upload = self.bot_handler.upload_file_from_path(str(path))
            uploaded_file_reply = "[{}]({})".format(path.name, upload["uri"])
            self.sendReply(notifyString + pngFilename,message)
            self.sendReply(uploaded_file_reply,message)
            os.remove(path)
            
        if(self.uploadMethod == 'firebase'):
            from firebase_admin import storage
            bucket = storage.bucket()
            blob   = bucket.blob(self.path + pngFilename)
            blob.upload_from_filename(str(path))
        
            url = blob.generate_signed_url(expiration=9999999999)
            self.sendReply(notifyString + "[" + pngFilename + "](" + url + ")",message)
            os.remove(path)
        
        if(self.uploadMethod == 'path'):
            os.replace(path, self.path + pngFilename)
            self.sendReply(notifyString + self.path + pngFilename)
        
        if(self.uploadMethod == "no_upload"):
            os.remove(path)
            
###############################################################################
# Misc
###############################################################################
    def threadTask(self,func,override=False):
        if(override): self.stop(args=[])
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
            return "Run ```help``` to see a list of valid commands"
        
        try:
            helpStr = "**" + command + "**\n"
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
    
    def unpackArgs(self,arg_dict):
        args = []
        for key,value in arg_dict.items():
            if(value[0] == "-default"):                                         # If the value is -default...
                args.append("-default")                                         # leave it so the function can retrieve the value from nanonis
                continue
            
            args.append(value[1](value[0]))                                     # Convert the string into data type
        
        return args
    
    def uploadToCloud(self,filename):
        if(not filename.endswith(".pkl")): return filename
        try:
            subprocess.run(["scp", filename, self.cloudPath])
            os.remove(filename)
        except Exception as e:
            self.sendReply("Error uploading file to cloud with command\nscp " +
                           filename + " " + self.cloudPath + "\n\n" + str(e))
    
    def _quit(self,arg_dict):
        sys.exit()
        
###############################################################################
# Run
###############################################################################
handler_class = scanbot_interface

if('-z' in sys.argv):
    rcfile = ''
    try:
        with open('scanbot_config.ini','r') as f:                                   # Go through the config file to see what defaults need to be overwritten
            line = "begin"
            while(line):
                line = f.readline()[:-1]
                key, value = line.split('=')                                        # Format for valid line is "Key=Value"
                if(key == 'zuliprc'):                                               # Look for the bot rc file
                    rcfile = value
                    break
    except:
        print("scanbot_config.ini not found.")
        sys.exit()
    
    if(not rcfile):
        print("zulip bot rc file not in scanbot_config.ini")
        sys.exit()
    
    os.system("zulip-run-bot scanbot_interface.py --config=" + rcfile)
    
if('-c' in sys.argv):
    print("Console mode: type 'exit' to end scanbot")
    go = True
    handler_class = scanbot_interface()
    while(go):
        message = input("User: ")
        if(message == 'exit'):
            break
        handler_class.handle_message(message)
    
    finish = True

# if('-g' in sys.argv and not finish):
    # print("Booting in GUI mode...")
    # import tkinter as tk
    # from tkinter import *
    # from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    # import matplotlib.pyplot as plt
    # import subprocess
    
    # master    = tk.Tk()
    # dpi       = master.winfo_fpixels('1i')
    
    # # Set up canvas
    # width = 512; height = 512
    # # canvas = FigureCanvasTkAgg(master=master)
    # # canvas.get_tk_widget().configure(width=width, height=height)
    
    # # # Figure
    # # fig = plt.figure(figsize=(width/dpi,height/dpi),dpi=dpi)
    # # ax  = fig.add_subplot(111)
    # # canvas.figure = fig
    # # canvas.draw()
    # termf = Frame(master, height=height, width=width)
    
    # termf.pack(fill=BOTH, expand=YES)
    # wid = termf.winfo_id()
    # subprocess.run('cmd.exe -into %d -geometry 40x20 -sb &' % wid)
    
    # master.mainloop()
    
    