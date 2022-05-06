# -*- coding: utf-8 -*-
"""
Created on Fri May  6 12:06:37 2022

@author: jced0001
"""

from ScanBot import ScanBot
import threading

import firebase_admin
from firebase_admin import credentials, storage

import os
import ipaddress
from pathlib import Path

class ScanbotInterface(object):
    global tasks;   tasks   = []                                                # queue of threads
    global running; running = threading.Event()                                 # event to stop threads
    global pause;   pause   = threading.Event()                                 # event to pause threads
    
    message    = []
    botHandler = []
    validUploadMethods = ['zulip','firebase']
    
###############################################################################
# Constructor
###############################################################################
    def __init__(self):
        ## Globals
        
        self.getWhitelist()                                                     # Load in whitelist file if there is one
        self.firebaseInit()                                                     # Initialise Firebase
        self.portList = [6501,6502,6503,6504]                                   # Default TCP ports for communicating with nanonis
        self.IP       = '127.0.0.1'                                             # Default IP to local host
        self.uploadMethod = 'zulip'                                             # Default upload method is zulip
        self.scanbot = ScanBot(self)
    
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
        try:
            cred = credentials.Certificate('firebase.json')                     # Your firebase credentials
            firebase_admin.initialize_app(cred, {
                'storageBucket': 'g80live.appspot.com'                          # Your firebase storage bucket
            })
        except:
            pass                                                                # Firebase error or already initialised
    
    def initCommandDict(self):
        self.commands = {'list_commands'    : self.listCommands,
                         'add_user'         : self.addUsers,
                         'list_users'       : lambda: str(self.whitelist),
                         'set_ip'           : self.setIP,
                         'get_ip'           : lambda: self.IP,
                         'set_portlist'     : self.setPortList,
                         'get_portlist'     : lambda: self.portList,
                         'set_upload_method': self.setUploadMethod,
                         'get_upload_method': lambda: self.uploadMethod,
                         'survey'           : self.survey,
                         'stop'             : self.stop,
                         'pause'            : lambda: pause.set(),
                         'resume'           : lambda: pause.clear(),
                         'plot'             : self.plot
        }
        
###############################################################################
# Scanbot
###############################################################################
    def survey(self,args):
        if running.is_set(): return "Error: something already running"
        running.set()
        t = threading.Thread(target=lambda : self.scanbot.survey(args))
        tasks.append(t)
        t.start()
    
    def stop(self,args):
        self.scanbot.stop(args)
        while len(tasks) > 0:
            running.clear()
            tasks.pop().join()
    
    def plot(self,args):
        self.scanbot.plot(args)
        
###############################################################################
# Zulip
###############################################################################
    def handle_message(self, message, botHandler):
        if message['sender_email'] not in self.whitelist and self.whitelist:
            self.sendReply('access denied')
            return
        
        self.message = message
        self.botHandler = botHandler
        
        command = message['content'].split(' ')[0].lower()
        args    = message['content'].split(' ')[1:]
        
        reply = self.command_dict[command](args)
        self.sendReply(reply)
    
    def sendReply(self,reply):
        if(self.botHandler): self.botHandler.send_reply(self.message, reply)
    
    def sendPNG(self,pngFilename):
        path = os.getcwd() + '/' + pngFilename
        path = Path(path)
        path = path.resolve()
        
        if self.uploadMethod == 'zulip':
            upload = self.botHandler.upload_file_from_path(str(path))
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
        
    def addUsers(self,users):
        try:
            for u in users: self.whitelist.append(u)
            with open('whitelist.txt', 'w') as f:
                for w in self.whitelist:
                    f.write(w+'\n')
        except Exception as e:
            return e
        
        return "user/s added sucessfully"
    
    def setIP(self,IP):
        try:
            ipaddress.ip_address(IP)
            self.IP = IP
            return "Set IP to " + self.IP
        except Exception as e:
            return e
    
    def setPortList(self,portList):
        self.portList = [int(x) for x in portList]
        return "Updated ports: " + str(self.portList)
    
    def setUploadMethod(self,uploadMethod):
        uploadMethod = uploadMethod.lower()
        if(not uploadMethod in self.validUploadMethods): return "Invalid Method"
        self.uploadMethod = uploadMethod
        return "Set upload method to " + self.uploadMethod
    
    def listCommands(self):
        return str([c for c in self.commands])