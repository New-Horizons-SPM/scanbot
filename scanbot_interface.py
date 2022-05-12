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
        
        self.getWhitelist()                                                     # Load in whitelist file if there is one
        self.firebaseInit()                                                     # Initialise Firebase
        self.portList = [6501,6502,6503,6504]                                   # Default TCP ports for communicating with nanonis
        self.IP       = '127.0.0.1'                                             # Default IP to local host
        self.uploadMethod = 'firebase'                                          # Default upload method is firebase
        self.initCommandDict()
        self.scanbot = scanbot(self)
    
###############################################################################
# Initialisation
###############################################################################
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
            cred = credentials.Certificate('firebase.json')                     # Your firebase credentials
            firebase_admin.initialize_app(cred, {
                'storageBucket': 'g80live.appspot.com'                          # Your firebase storage bucket
            })
        except Exception as e:
            print(e)
    
    def initCommandDict(self):
        self.commands = {'list_commands'    : self.listCommands,
                         'add_user'         : self.addUsers,
                         'list_users'       : lambda args: str(self.whitelist),
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
                         'tip_shape'        : self.tipShape,
                         'pulse'            : self.pulse,
                         'bias_dep'         : self.biasDep
        }
    
###############################################################################
# Scanbot
###############################################################################
    def survey(self,args):
        func = lambda : self.scanbot.survey(args)
        return self.threadTask(func)
    
    def stop(self,args):
        if(global_.running.is_set()):
            self.scanbot.stop(args)
            global_.running.clear()
            global_.tasks.join()
        self.scanbot.stop(args)
        
    def enhance(self,args):
        func = lambda : self.scanbot.enhance(args)
        return self.threadTask(func,override=True)
        
    def plot(self,args):
        self.scanbot.plot(args)
    
    def tipShape(self,args):
        func = lambda : self.scanbot.tipShape(args)
        return self.threadTask(func)
        
    def pulse(self,args):
        self.scanbot.pulse(args)
        
    def biasDep(self,args):
        func = lambda : self.scanbot.biasDep(args)
        return self.threadTask(func)
    
    def threadTask(self,func,override=False):
        if(override): self.stop(args=[])
        if global_.running.is_set(): return "Error: something already running"
        global_.running.set()
        t = threading.Thread(target=func)
        global_.tasks = t
        t.start()
        return ""
        
###############################################################################
# Zulip
###############################################################################
    def handle_message(self, message, bot_handler=None):
        self.bot_handler = bot_handler
        if(bot_handler):
            if message['sender_email'] not in self.whitelist and self.whitelist:
                self.sendReply(message['sender_email'])
                self.sendReply('access denied')
                return
            
            self.bot_message = message
            
            message = message['content']
            
        command = message.split(' ')[0].lower()
        args    = message.split(' ')[1:]
        
        if(not command in self.commands):
            reply = "Invalid command. Run *list_commands* to see command list"
            self.sendReply(reply)
            return
        
        reply = self.commands[command](args)
        
        if(reply): self.sendReply(reply)
    
    def sendReply(self,reply):
        if(self.bot_handler):
            self.bot_handler.send_reply(self.bot_message, reply)
            return
        
        print(reply)
    
    def sendPNG(self,pngFilename):
        if(not self.bot_handler): print("pngs not supported yet"); return       # Don't support png
        path = os.getcwd() + '/' + pngFilename
        path = Path(path)
        path = path.resolve()
        
        if self.uploadMethod == 'zulip':
            upload = self.bot_handler.upload_file_from_path(str(path))
            uploaded_file_reply = "[{}]({})".format(path.name, upload["uri"])
            self.sendReply(uploaded_file_reply)
            self.sendReply(pngFilename)
            
        if self.uploadMethod == 'firebase':
            bucket = storage.bucket()
            blob   = bucket.blob('scanbot/' + pngFilename)
            blob.upload_from_filename(str(path))
        
            url = blob.generate_signed_url(expiration=9999999999)
            self.sendReply(pngFilename)
            self.sendReply(url)
        
        os.remove(path)
        
    def addUsers(self,user):
        try:
            self.whitelist.append(user)
            with open('whitelist.txt', 'w') as f:
                for w in self.whitelist:
                    f.write(w+'\n')
        except Exception as e:
            return str(e)
        
        return "user/s added sucessfully"
    
    def setIP(self,IP):
        try:
            IP = IP[0]
            ipaddress.ip_address(IP)
            self.IP = IP
            return "Set IP to " + self.IP
        except Exception as e:
            return str(e)
    
    def setPortList(self,portList):
        self.portList = [int(x) for x in portList]
        return "Updated ports: " + str(self.portList)
    
    def setUploadMethod(self,uploadMethod):
        uploadMethod = uploadMethod[0].lower()
        if(not uploadMethod in self.validUploadMethods):
            return "Invalid Method. Available methods:\n" + "\n". join(self.validUploadMethods)
        self.uploadMethod = uploadMethod
        return "Set upload method to " + self.uploadMethod
    
    def listCommands(self,args):
        return "\n". join([c for c in self.commands])
    
handler_class = scanbot_interface