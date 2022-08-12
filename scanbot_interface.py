# -*- coding: utf-8 -*-
"""
Created on Fri August 8 22:06:37 2022

@author: Julian Ceddia
"""

from scanbot import scanbot

import zulip
import firebase_admin
from firebase_admin import credentials, storage

import os
import sys
from pathlib import Path

import ipaddress

class scanbot_interface(object):
    bot_message = []
    bot_handler = []
    validUploadMethods = ['path','zulip','firebase']
    
###############################################################################
# Constructor
###############################################################################
    def __init__(self):
        print("Initialising app...")
        self.loadConfig()
        self.initCommandDict()
        self.scanbot = scanbot(self)
    
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
                    'upload_method'             : 'path',                       # Ping data via this channel.
                    'path'                      : './sbData',                   # Path to save data (if upload_method=path)
                    'firebase_credentials'      : '',                           # Credentials for firebase (if upload_method=firebase)
                    'firebase_storage_bucket'   : '',                           # Firebase bucket. Firebase path uses "path" key
                    'port_list'                 : '6501,6502,6503,6504',        # Ports (see nanonis => Main Options => TCP Programming Interface)
                    'ip'                        : '127.0.0.1',                  # IP of the pc controlling nanonis
                    'creeplist'                 : '',                           # IP addresses to creep
                    'notify_list'               : '',                           # Comma delimited zulip users to @notify when sending data
                    'temp_calibration_curve'    : ''}                           # Path to temp calibration curve (see nanonis Temperature modules)
        
        try:
            with open('scanbot_config.ini','r') as f:                           # Go through the config file to see what defaults need to be overwritten
                line = "begin"
                while(line):
                    line = f.readline()[:-1]
                    if(line.startswith('#')): print(line); continue             # Comment
                    if(not '=' in line):      print(line); continue             # Comment
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
        
        self.loadWhitelist()
        
    def firebaseInit(self):
        try:
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
    
    def initCommandDict(self):
        self.commands = {'help'             : self._help,
                         'set_ip'           : self.setIP,
                         'get_ip'           : lambda args: self.IP,
                         'set_portlist'     : self.setPortList,
                         'get_portlist'     : lambda args: self.portList,
                         'set_upload_method': self.setUploadMethod,
                         'get_upload_method': lambda args: self.uploadMethod,
                         'add_user'         : self.addUser,
                         'get_users'        : lambda args: str(self.whitelist),
                         'set_path'         : self.setPath,
                         'get_path'         : lambda args: self.path
        }
        
###############################################################################
# Scanbot Commands
###############################################################################
    
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
                Path(self.path).mkdir(parents=True, exist_ok=True)
                if(not self.path.endswith('/')):
                    self.path += '/'
                self.reactToMessage('all_good')
        except Exception as e:
            return str(e)
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
            
        if(self.uploadMethod == 'firebase'):
            bucket = storage.bucket()
            blob   = bucket.blob(self.firebaseStoragePath + pngFilename)
            blob.upload_from_filename(str(path))
        
            url = blob.generate_signed_url(expiration=9999999999)
            self.sendReply(notifyString + "[" + pngFilename + "](" + url + ")",message)
        
        if(self.uploadMethod == 'path'):
            os.replace(path, self.path + pngFilename)
            self.sendReply(notifyString + self.path + pngFilename)
            
        os.remove(path)
###############################################################################
# Misc
###############################################################################
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

###############################################################################
# Run
###############################################################################
handler_class = scanbot_interface

if('-c' in sys.argv):
    print("Console mode: type 'exit' to end scanbot")
    go = True
    handler_class = scanbot_interface()
    while(go):
        message = input("User: ")
        if(message == 'exit'):
            break
        handler_class.handle_message(message)
    
    