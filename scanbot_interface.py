# -*- coding: utf-8 -*-
"""
Created on Fri May  6 12:06:37 2022

@author: jack hellerstedt and julian ceddia
"""

from scanbot import scanbot
import threading

import firebase_admin
from firebase_admin import credentials, storage

import os
import ipaddress
from pathlib import Path

import global_
import nanonisUtils as nut

import zulip

class scanbot_interface(object):
    bot_message = []
    bot_handler = []
    validUploadMethods = ['zulip','firebase']
    
###############################################################################
# Constructor
###############################################################################
    def __init__(self):
        ## Globals
        global_.tasks   = []
        global_.running = threading.Event()                                     # event to stop threads
        global_.pause   = threading.Event()                                     # event to pause threads
        global_.creepTask = []                                                  # Dedicated creep task
        global_.creepRunning = threading.Event()                                # Dedicated creep thread
        
        self.init()
        
        self.getWhitelist()                                                     # Load in whitelist file if there is one
        self.firebaseInit()                                                     # Initialise Firebase
        self.initCommandDict()
        self.scanbot = scanbot(self)
    
###############################################################################
# Initialisation
###############################################################################
    def init(self):
        initDict = {'zuliprc'                   : '',
                    'upload_method'             : '',
                    'firebase_credentials'      : '',
                    'firebase_storage_bucket'   : '',
                    'firebase_storage_path'     : '',
                    'port_list'                 : '6501,6502,6503,6504',
                    'ip'                        : '127.0.0.1',
                    'notify_list'               : '',
                    'temp_calibration_curve'    : ''}
        
        try:
            with open('scanbot_config.txt','r') as f:
                line = "begin"
                while(line):
                    line = f.readline()[:-1]
                    if(not ': ' in line): print("From config: " + line); continue
                    key, value = line.split(': ')
                    if(not key in initDict):
                        print("Invalid key in scanbot_config.txt: " + key)
                        continue
                    
                    initDict[key] = value
        except:
            pass
        
        self.zuliprc      = initDict['zuliprc']
        self.uploadMethod = initDict['upload_method']
        self.firebaseCert = initDict['firebase_credentials']
        self.firebaseStorageBucket = initDict['firebase_storage_bucket']
        self.firebaseStoragePath   = initDict['firebase_storage_path']
        if(not self.firebaseStoragePath.endswith('/') and self.firebaseStoragePath):
            self.firebaseStoragePath += '/'
        
        portList = initDict['port_list']
        if(portList):
            if(',' in portList):
                portList = portList.split(',')
                self.setPortList(portList)
            else:
                self.setPortList([portList])
                
        self.setIP([initDict['ip']])
        
        self.notifyUserList = []
        notifyList = initDict['notify_list']
        if(notifyList):
            if(',' in notifyList):
                notifyList = notifyList.split(',')
                self.notifyUserList = notifyList
            else:
                self.notifyUserList = [notifyList]
        
        self.notifications = True
        self.bot_message = ""
        
        self.zulipClient = []
        if(self.zuliprc):
            self.zulipClient = zulip.Client(config_file=self.zuliprc)
        
        self.tempCurve = initDict['temp_calibration_curve']
        
    def getWhitelist(self):
        self.whitelist = []
        try:
            with open('whitelist.txt', 'r') as f:
                d = f.read()
                self.whitelist = d.split('\n')[:-1]
        except:
            print('No whitelist... add users to create one')
    
    def firebaseInit(self):
        print("Initialising firebase app")
        try:
            cred = credentials.Certificate(self.firebaseCert)                   # Your firebase credentials
            firebase_admin.initialize_app(cred, {
                'storageBucket': self.firebaseStorageBucket                     # Your firebase storage bucket
            })
        except Exception as e:
            print("Firebase not initialised...")
            print(e)
    
    def initCommandDict(self):
        self.commands = {'list_commands'    : self.listCommands,
                         'help'             : self._help,
                         'add_user'         : self.addUsers,
                         'list_users'       : lambda args: str(self.whitelist),
                         'noti'             : self.noti,
                         'set_ip'           : self.setIP,
                         'get_ip'           : lambda args: self.IP,
                         'set_portlist'     : self.setPortList,
                         'get_portlist'     : lambda args: self.portList,
                         'set_upload_method': self.setUploadMethod,
                         'get_upload_method': lambda args: self.uploadMethod,
                         'survey'           : self.survey,
                         'stop'             : self.stop,
                         'pause'            : lambda args: global_.pause.set(),
                         'resume'           : lambda args: global_.pause.clear(),
                         'enhance'          : self.enhance,
                         'plot'             : self.plot,
                         'move_tip'         : self.moveTip,
                         'tip_shape_props'  : self.tipShapeProps,
                         'tip_shape'        : self.tipShape,
                         'pulse_props'      : self.pulseProps,
                         'pulse'            : self.pulse,
                         'bias_dep'         : self.biasDep,
                         'make_gif'         : self.makeGif,
                         'set_bias'         : self.setBias,
                         'stitch_survey'    : self.stitchSurvey,
                         'watch'            : self.watch,
                         'creep'            : self.creep,
                         'stop_creeping'    : self.stopCreeping,
                         'add_notify_list'  : self.addNotifyUser,
                         'get_notify_list'  : lambda args: self.notifyUserList,
                         'move_area'        : self.moveArea,
                         'safety_props'     : self.safetyProps,
                         'channel'          : self.channelSelect,
                         'get_temp'         : self.getTemp,
                         'plot_channel'     : self.plotChannel
        }
    
###############################################################################
# Scanbot
###############################################################################
    def plotChannel(self,user_args,_help=False):
        arg_dict = {'-c' : ['14', lambda x: int(x), "(int) Scan buffer channel display. Run without -c to see available channels"]}
        
        if(_help): return arg_dict
        
        if(not len(user_args)): return self.scanbot.plotChannel()
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help plot_channel``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        return self.scanbot.plotChannel(*args)
        
    def getTemp(self,user_args,_help=False):
        arg_dict = {'' : ['', 0, "Call this function to return STM and Cryo Temps"]}
        
        if(_help): return arg_dict
        
        stmTemp,cryoTemp = self.scanbot.getTemp()
        tempStr = "STM Temp: " + str(stmTemp) + " K\n"
        tempStr = "Cryo Temp: " + str(cryoTemp) + " K\n"
        return tempStr
        
    def channelSelect(self,user_args,_help=False):
        arg_dict = {'-ch'     : ['-default', lambda x: int(x),                         "(int) Index of the channel to plot"],
                    '-inslot' : ['-default', lambda x: [int(c) for c in x.split(',')], "(int array) Comma delimited signal indexes to move 'in slot'. Negative indexes remove from slot"]}
        
        if(_help): return arg_dict
        
        if(not len(user_args)): return self.scanbot.channelsGet()
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help channel``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        return self.scanbot.channelSet(*args)
        
    def safetyProps(self,user_args,_help=False):
        safetyParams = self.scanbot.safetyParams                                # Using this to update the dict with current settings
        maxcur = str(safetyParams[0])                                           # So that they don't change when only updaing some params
        motorF = str(safetyParams[1])
        motorV = str(safetyParams[2])
        arg_dict = {'-maxcur' : [maxcur, lambda x: float(x), "(float) Current threshold that triggers safe retract (A)"],
                    '-motorF' : [motorF, lambda x: float(x), "(float) Motor control piezo frequency during safe retract (Hz)"],
                    '-motorV' : [motorV, lambda x: float(x), "(float) Motor control piezo voltage during safe retract (V)"]}
        
        if(_help): return arg_dict
        
        if(not len(user_args)): return self.scanbot.safetyPropsGet()
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help safety_props``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        return self.scanbot.safetyPropsSet(*args)
        
    def moveArea(self,user_args,_help=False):
        arg_dict = {'-up'    : ['10',   lambda x: int(x),   "(int) Steps to go up before moving across. min 10"],
                    '-upV'   : ['180',  lambda x: float(x), "(float) Controller amplitude during up motor steps"],
                    '-upF'   : ['1100', lambda x: float(x), "(float) Controller frequency during up motor steps"],
                    '-dir'   : ['Y+',   lambda x: str(x),   "(str) Direction to go across (either X+, X-, Y+, Y-)"],
                    '-steps' : ['10',   lambda x: int(x),   "(int) Steps to move across after moving -up number of steps"],
                    '-dirV'  : ['130',  lambda x: float(x), "(float) Controller amplitude during across motor steps"],
                    '-dirF'  : ['1100', lambda x: float(x), "(float) Controller frequency during across motor steps"],
                    '-zon'   : ['1',    lambda x: int(x),   "(int) Turn the z-controller on after approaching. 1=on, 0=off"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help move_area``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        self.scanbot.moveArea(*args)
    
    def stopCreeping(self,user_args=[],_help=False):
        if(global_.creepRunning.is_set()):
            global_.creepRunning.clear()
            global_.creepTask.join()
        
    def creep(self,user_args,_help=False):
        arg_dict = {'-ip'   : [self.IP, lambda x: str(x), "(str) Creep IP"],
                    '-port' : ['6501',  lambda x: int(x), "(int) Creep Port"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help creep``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        func = lambda : self.scanbot.watch("",*args,message=self.bot_message.copy())
        if global_.creepRunning.is_set(): return "Error: already creeping"
        global_.creepRunning.set()
        global_.creepTask = threading.Thread(target=func)
        global_.creepTask.start()
    
    def watch(self,user_args,_help=False):
        arg_dict = {'-s' : ['sbwatch', lambda x: str(x), "(str) Suffix at the end of autosaved sxm files"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help watch``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        func = lambda : self.scanbot.watch(*args,message=self.bot_message.copy())
        return self.threadTask(func)
        
    def survey(self,user_args,_help=False):
        arg_dict = {'-bias' : ['-default', lambda x: float(x), "(float) Scan bias"],
                    '-n'    : ['5',        lambda x: int(x),   "(int) Size of the nxn grid of scans"],
                    '-i'    : ['1',        lambda x: int(x),   "(int) Start the grid from this index"],
                    '-s'    : ['scanbot',  lambda x: str(x),   "(str) Suffix at the end of autosaved sxm files"],
                    '-xy'   : ['100e-9',   lambda x: float(x), "(float) Length and width of the scan frame (m)"],
                    '-dx'   : ['150e-9',   lambda x: float(x), "(float) Scan grid spacing (m)"],
                    '-st'   : ['10',       lambda x: float(x), "(float) Drift compensation time (s)"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help survey``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        func = lambda : self.scanbot.survey(*args,message=self.bot_message.copy())
        return self.threadTask(func)
        
    def enhance(self,user_args,_help=False):
        arg_dict = {'-bias' : ['-default', lambda x: float(x), "(float) Scan bias. (-default=unchanged)"],
                    '-n'    : ['2',        lambda x: int(x),   "(int) Size of nxn grid within enhanced frame"],
                    '-i'    : ['-1',       lambda x: int(x),   "(int) Start the grid from this index"],
                    '-s'    : ['enhance',  lambda x: str(x),   "(str) Suffix at the end of autosaved sxm files"],
                    '-st'   : ['-default', lambda x: float(x), "(float) Drift compensation time (s)"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help enhance``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        inSurvey = self.scanbot.inSurvey
        func = lambda : self.scanbot.enhance(*args,message=self.bot_message.copy(),inSurvey=inSurvey)
        return self.threadTask(func,override=True)
        
    def plot(self,args):
        self.scanbot.plot(args)
    
    def moveTip(self,user_args,_help=False):
        arg_dict = {'-pos'     : ['0,0', lambda x: [float(p) for p in x.split(',')], "(float array) position of the tip x,y"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help move_tip``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        self.scanbot.moveTip(*args)
        
    def tipShape(self,user_args,_help=False):
        arg_dict = {'-np'     : ['1',   lambda x: int(x),   "(int) Number of bias pulses after tip shape"], 
                    '-pw'     : ['0.1', lambda x: float(x), "(float) Pulse width (s)"],
                    '-bias'   : ['3',   lambda x: float(x), "(float) Bias pulse value (V)"],
                    '-zhold'  : ['0',   lambda x: int(x),   "(int) Z-Controller on hold (0=nanonis setting, 1=deactivated, 2=activated)"],
                    '-abs'    : ['0',   lambda x: int(x),   "(int) Abs or rel mode (0=nanonis, 1=relative, 2=absolute)"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help tip_shape``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        self.scanbot.tipShape(*args)
        
    def tipShapeProps(self,user_args,_help=False):
        arg_dict = {'-sod'    : ['-default',lambda x: float(x), "(float) Switch off delay: the time (s) during which the Z position is averaged before switching the Z controller off"],
                    '-cb'     : ['-default',lambda x: int(x),   "(int) Change bias flag (0=Nanonis,1=Change Bias,2=Don't Change"],
                    '-b1'     : ['-default',lambda x: float(x), "(float) The value applied to the Bias signal if cb is true"],
                    '-z1'     : ['-default',lambda x: float(x), "(float) First tip lift (m) (i.e. -2e-9)"],
                    '-t1'     : ['-default',lambda x: float(x), "(float) Defines the time to ramp Z from current Z position to z1"],
                    '-b2'     : ['-default',lambda x: float(x), "(float) Bias voltage applied just after the first Z ramping"],
                    '-t2'     : ['-default',lambda x: float(x), "(float) Time to wait after applying the Bias Lift value b2"],
                    '-z3'     : ['-default',lambda x: float(x), "(float) Height the tip is going to ramp for the second time (m) i.e. +5nm"],
                    '-t3'     : ['-default',lambda x: float(x), "(float) Time to ramp Z in the second ramping [s]."],
                    '-wait'   : ['-default',lambda x: float(x), "(float) Time to wait after restoring the initial Bias voltage"],
                    '-fb'     : ['-default',lambda x: int(x),   "(int) Restore the initial Z-Controller status. 0: off. 1: on"],
                    '-area'   : ['-600e-9,-600e-9,300e-9,300e-9', lambda x: [float(p) for p in x.split(',')], "(float array) Designated tip-shaping area [x_centre,y_centre,width,height]"],
                    '-grid'   : ['10',      lambda x: int(x),   "(int) Grid size in the designated area"]}
        
        if(_help): return arg_dict
        
        if(not len(user_args)): return self.scanbot.tipShapePropsGet()
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help tip_shape_props``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        self.scanbot.tipShapeProps(*args)
    
    def pulseProps(self,user_args,_help=False):
        arg_dict = {'-n'      : ['1',  lambda x: int(x),   "(Int) Number of pulses"],
                    '-pw'     : ['.1', lambda x: float(x), "(float) Pulse width (s)"],
                    '-bias'   : ['3',  lambda x: float(x), "(float) Bias value (V)"],
                    '-zhold'  : ['0',  lambda x: int(x),   "(int) Z-Controller on hold (0=nanonis setting, 1=deactivated, 2=activated)"],              # 
                    '-abs'    : ['0',  lambda x: int(x),   "(int) Abs or rel mode (0=nanonis,1=rel,2=abs)"]
                    }
        
        if(_help): return arg_dict
        
        if(not len(user_args)): return self.scanbot.pulsePropsGet()
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help pulse_props``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        self.scanbot.pulseProps(*args)
        
    def pulse(self,user_args,_help=False):
        self.scanbot.pulse()
        
    def biasDep(self,user_args,_help=False):
        arg_dict = {'-n'   : ['5',   lambda x: int(x),   "(int) Number of images to take b/w initial and final bias"],
                    '-bdc' : ['-1',  lambda x: float(x), "(float) Drift correct image bias"],
                    '-bi'  : ['-1',  lambda x: float(x), "(float) Initial Bias"],
                    '-bf'  : ['1',   lambda x: float(x), "(float) Final Bias"],
                    '-px'  : ['128', lambda x: int(x),   "(int) Pixels in drift correct image. 0=no drift correction"],
                    '-s'   : ['sb-biasdep', lambda x: str(x), "(str) Suffix for the set of bias dep sxm files"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help bias_dep``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        
        func = lambda : self.scanbot.biasDep(*args,message=self.bot_message.copy())
        return self.threadTask(func)
    
    def setBias(self,user_args,_help=False):
        arg_dict = {'-bias'   : ['0',   lambda x: float(x), "(float) Change the tip bias to this value. 0=No change"]}
        
        if(_help): return arg_dict
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help set_bias``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        self.scanbot.setBias(*args)
    
    def stop(self,args):
        if(global_.running.is_set()):
            self.scanbot.stop(args)
            global_.running.clear()
            global_.pause.clear()
            global_.tasks.join()
        self.scanbot.stop(args)
        
    def threadTask(self,func,override=False):
        if(override): self.stop(args=[])
        if global_.running.is_set(): return "Error: something already running"
        global_.running.set()
        t = threading.Thread(target=func)
        global_.tasks = t
        t.start()
        
###############################################################################
# Zulip
###############################################################################
    def handle_message(self, message, bot_handler=None):
        messageContent   = message
        self.bot_message = []
        self.bot_handler = bot_handler
        if(bot_handler):
            if message['sender_email'] not in self.whitelist and self.whitelist:
                self.sendReply(message['sender_email'])
                self.sendReply('access denied')
                return
            
            self.bot_message = message
            messageContent = message['content']
            
        command = messageContent.split(' ')[0].lower()
        args    = messageContent.split(' ')[1:]
        
        if(not command in self.commands):
            reply = "Invalid command. Run *list_commands* to see command list"
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
        if(self.notifications):                                                 # Only send reply if notifications are turned on
            if(self.bot_handler):                                               # If our reply pathway is zulip
                replyTo = message                                               # If we're replying to a specific message
                if(not replyTo): replyTo = self.bot_message                     # If we're just replying to the last message sent by user
                r = self.bot_handler.send_reply(replyTo, reply)                 # Send the message. The sent message dict is returnred to r
                return r['id']                                                  # Return the ID of the sent message
        
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
            
        if(not self.bot_handler): print("pngs not supported yet"); return       # Don't support png
        
        path = os.getcwd() + '/' + pngFilename
        path = Path(path)
        path = path.resolve()
        
        if self.uploadMethod == 'zulip':
            upload = self.bot_handler.upload_file_from_path(str(path))
            uploaded_file_reply = "[{}]({})".format(path.name, upload["uri"])
            self.sendReply(notifyString + pngFilename,message)
            self.sendReply(uploaded_file_reply,message)
            
        if self.uploadMethod == 'firebase':
            bucket = storage.bucket()
            blob   = bucket.blob(self.firebaseStoragePath + pngFilename)
            blob.upload_from_filename(str(path))
        
            url = blob.generate_signed_url(expiration=9999999999)
            self.sendReply(notifyString + "[" + pngFilename + "](" + url + ")",message)
        os.remove(path)
    
    def addNotifyUser(self,username):
        self.notifyUserList.append(" ".join(username))
        
    def addUsers(self,user,_help=False):
        arg_dict = {'' : ['', 0, "(string) Add user email to whitelist (one at a time)"]}
        
        if(_help): return arg_dict
        
        if(len(user) != 1): self.reactToMessage("cross_mark"); return
        if(' ' in user[0]): self.reactToMessage("cross_mark"); return
        try:
            self.whitelist.append(user[0])
            with open('whitelist.txt', 'w') as f:
                for w in self.whitelist:
                    f.write(w+'\n')
        except Exception as e:
            return str(e)
        
        return "user/s added sucessfully"
    
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
            return str(e)
    
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
    
    def setUploadMethod(self,uploadMethod):
        if(len(uploadMethod) != 1): self.reactToMessage('cross_mark'); return
        
        uploadMethod = uploadMethod[0].lower()
        if(not uploadMethod in self.validUploadMethods):
            self.reactToMessage('cross_mark')
            return "Invalid Method. Available methods:\n" + "\n". join(self.validUploadMethods)
        self.uploadMethod = uploadMethod
        self.reactToMessage('all_good')
    
    def noti(self,args,_help=False):
        arg_dict = {'' : ['', 0, '(string) Notifications either "on" or "off"']}
        
        if(_help): return arg_dict
        
        if(not args[0].lower() in ["off","on"]):
            self.reactToMessage('cross_mark')
            self.sendReply("Choose on or off")
            return
        
        if(args[0].lower() == "on"):
            self.notifications = True
            self.reactToMessage('speaking_head')
            
        if(args[0].lower() == "off"):
            self.notifications = False
            self.reactToMessage('quiet')
    
    def listCommands(self,args):
        return "\n". join([c for c in self.commands])
    
###############################################################################
# Utilities
###############################################################################
    def makeGif(self,user_args,_help=False):
        arg_dict = {'-s' : ['*', lambda x: str(x), "(str) Survey name"],
                    '-d' : ['0', lambda x: int(x), "(int) Delete survey after stitch. 0: Don't delete. 1: Delete"]}
        
        if(_help): return arg_dict
        
        if(self.uploadMethod == 'zulip'): return "Unsupported upload method"
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help make_gif``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        url,reply = nut.makeGif(storage,self.firebaseStoragePath,*args)
        if(reply): self.sendReply(reply)
        return url
        
    def stitchSurvey(self,user_args,_help=False):
        arg_dict = {'-s' : ['*', lambda x: str(x), "(str) Survey name"],
                    '-d' : ['0', lambda x: int(x), "(int) Delete survey after stitch. 0: Don't delete. 1: Delete"]}
        
        if(_help): return arg_dict
        
        if(self.uploadMethod == 'zulip'): return "Unsupported upload method"
        
        error,user_arg_dict = self.userArgs(arg_dict,user_args)
        if(error): return error + "\nRun ```help stitch_survey``` if you're unsure."
        
        args = self.unpackArgs(user_arg_dict)
        return nut.stitchSurvey(storage,self.firebaseStoragePath,*args)
                
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
    
    def _help(self,args):
        if(not len(args)):
            helpStr = "Type ```help <command name>``` for more info\n"
            return helpStr + self.listCommands(args=[])
        
        command = args[0]
        if(not command in self.commands):
            return "Run ```list_commands``` to see valid commands"
        
        try:
            helpStr = "**" + command + "**\n"
            arg_dict = self.commands[command](args,_help=True)
            for key,value in arg_dict.items():
                if(key):
                    helpStr += "```"
                    helpStr += key + "```: " 
                helpStr += value[2] + ". "
                if(value[0]):
                    helpStr += "Default: ```" +  value[0].replace("-default","nanonis") 
                    helpStr += "```"
                helpStr += "\n"
        except:
            return "No help for this command"
        
        return helpStr
    
handler_class = scanbot_interface