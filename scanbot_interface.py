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

class scanbot_test(object):
    message    = []
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
                         'tip_shape'        : self.tipShape
        }
    
###############################################################################
# Scanbot
###############################################################################
    def survey(self,args):
        if global_.running.is_set(): return "Error: something already running"
        global_.running.set()
        t = threading.Thread(target=lambda : self.scanbot.survey(args))
        global_.tasks = t
        t.start()
    
    def stop(self,args):
        self.scanbot.stop(args)
        global_.running.clear()
        global_.tasks.join()
    
    def enhance(self,args):
        self.stop(args=[])
        global_.running.set()
        t = threading.Thread(target=lambda : self.scanbot.enhance(args))
        global_.tasks = t
        t.start()
        
    def plot(self,args):
        self.scanbot.plot(args)
    
    def tipShape(self,args):
        if(global_.running.is_set()): self.stop(args=[])
        global_.running.set()
        t = threading.Thread(target=lambda : self.scanbot.tipShape(args))
        global_.tasks = t
        t.start()
        
###############################################################################
# Zulip
###############################################################################
    def handle_message(self, message, bot_handler):
        if message['sender_email'] not in self.whitelist and self.whitelist:
            self.sendReply(message['sender_email'])
            self.sendReply('access denied')
            return
        
        self.message = message
        self.bot_handler = bot_handler
        
        command = message['content'].split(' ')[0].lower()
        args    = message['content'].split(' ')[1:]
        # if(len(args) == 1): args = args.pop()
        
        if(not command in self.commands):
            reply = "Invalid command. Run *list_commands* to see command list"
            self.sendReply(reply)
            return
        
        reply = self.commands[command](args)
        
        if(reply): self.sendReply(reply)
    
    def sendReply(self,reply):
        if(self.bot_handler): self.bot_handler.send_reply(self.message, reply)
    
    def sendPNG(self,pngFilename):
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
        uploadMethod = uploadMethod.lower()
        if(not uploadMethod in self.validUploadMethods):
            return "Invalid Method. Available methods:\n" + "\n". join(self.validUploadMethods)
        self.uploadMethod = uploadMethod
        return "Set upload method to " + self.uploadMethod
    
    def listCommands(self,args):
        return "\n". join([c for c in self.commands])
    
handler_class = scanbot_test