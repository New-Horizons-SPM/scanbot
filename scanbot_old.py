#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May  2 14:51:27 2022

@author: jack
"""

import os
import ntpath # os.path but for windows paths
import signal
import time
from pathlib import Path
import threading


## these are needed if uploading png to google firebase
import firebase_admin
from firebase_admin import credentials, storage

import numpy as np
import nanonispyfit as nap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


from nanonisTCP import nanonisTCP
from nanonisTCP.Scan import Scan


class ScanBot(object):
    
    global tasks ## queue of threads
    tasks = []
    global running
    running = threading.Event() # event to stop threads
    global pause
    pause = threading.Event() # event to pause threads
    
    def __init__(self):
        ## read in list of authorised users from whitelist.txt:
        self.whitelist = []
        self.portlist = [6501,6502,6503,6504]
        try:
            with open('whitelist.txt', 'r') as f:
                d = f.read()
                self.whitelist = d.split('\n')[:-1]
        except:
            print('no whitelist')
            
        try:
            cred = credentials.Certificate('firebase.json')
            firebase_admin.initialize_app(cred, {
                'storageBucket': 'g80live.appspot.com'
            })
        except:
            pass
    
    def send_plot(self, bot_handler, message, scan_data, scan_direction='up', file_path=''):
        fig, ax = plt.subplots(1,1)
        ## light image processing
        if scan_direction == 'up':
            scan_data = np.flipud(scan_data)
        mask = np.isnan(scan_data)
        scan_data[mask == True] = np.nanmean(scan_data)
        scan_data = nap.plane_fit_2d(scan_data)
        vmin, vmax = nap.filter_sigma(scan_data)
    
        ax.imshow(scan_data, origin='lower', cmap='Blues_r', vmin=vmin, vmax=vmax)
        ax.axis('off')
        
        filename = 'im.png'
        if file_path == '':
            filename = 'im.png'
        else:
            filename = ntpath.split(file_path)[1] + '.png'
        
        fig.savefig(filename, dpi=60, bbox_inches='tight', pad_inches=0)
        plt.close('all')
            
        path = os.getcwd() + '/' + filename
        path = Path(path)
        path = path.resolve()
        
        try:
            image_upload = bot_handler.storage.get('upload_method')
        except:
            image_upload = 'zulip'
        
        if image_upload == 'zulip':
            upload = bot_handler.upload_file_from_path(str(path))
            uploaded_file_reply = "[{}]({})".format(path.name, upload["uri"])
            bot_handler.send_reply(message, uploaded_file_reply)
            bot_handler.send_reply(message, filename)
            
        if image_upload == 'firebase':

            bucket = storage.bucket()
            blob   = bucket.blob('scanbot/' + filename)
            blob.upload_from_filename(str(path))

            url = blob.generate_signed_url(expiration=9000000000)
            bot_handler.send_reply(message, url)
        
        os.remove(path)
    
    def survey_function(self, bot_handler, message, N_scans=5, suffix=""):
        IP = str(bot_handler.storage.get('IP'))
        try:
            PORT = self.portlist.pop()
        except:
            bot_handler.send_reply(message, "No ports available")
            return
        NTCP = nanonisTCP(IP, PORT)
        scan = Scan(NTCP)
        
        ## get current scan savename
        savename = scan.PropsGet()[3]
        bot_handler.storage.put('savename', savename)
        if suffix: savename += '_' + suffix + '_'
        scan.PropsSet(series_name=savename)

        frames = [] ## x,y,w,h,angle=0
        dx = 150e-9
        scansize = 100e-9
        N_scans = int(N_scans/2)
        for ii in range(-N_scans,N_scans+1):
            if ii % 2 == 0:
                for jj in range(-N_scans,N_scans+1):
                    frames.append([jj*dx, ii*dx, scansize, scansize])
            else:
                for jj in range(-N_scans,N_scans+1):
                    frames.append([-jj*dx, ii*dx, scansize, scansize])
            
        for frame in frames:
            while pause.is_set():
                time.sleep(2)
                
            if running.is_set():
                reply = 'running scan' + str(frame)
                bot_handler.send_reply(message, reply)
                scan.FrameSet(*frame)
                scan.Action('start')
                if not running.is_set(): break
                while pause.is_set():
                    time.sleep(2)
                time.sleep(10)
                if not running.is_set(): break
                while pause.is_set():
                    time.sleep(2)
                scan.Action('start')
                timeout_status, file_path_size, file_path = scan.WaitEndOfScan()
                channel_name,scan_data,scan_direction = scan.FrameDataGrab(14, 1) ## 14 is Z
                if timeout_status:
                    file_path = ''
                self.send_plot(bot_handler, message, scan_data, scan_direction, file_path)
        
        ## reset the scan savename
        savename = bot_handler.storage.get('savename')
        scan.PropsSet(series_name=savename)
        
        NTCP.close_connection()
        self.portlist.append(PORT)
        bot_handler.send_reply(message, 'survey done')
    
    def handle_message(self, message, bot_handler):
        if message['sender_email'] not in self.whitelist and self.whitelist:
            bot_handler.send_reply(message, 'access denied')
            return
            
        if message['content'].find('add_user') > -1:
            try:
                user = message['content'].split('add_user ')[1].split('\n')[0]
                self.whitelist.append(user)
                with open('whitelist.txt', 'w') as f:
                    for w in self.whitelist:
                        f.write(w+'\n')
            except Exception as e:
                bot_handler.send_reply(message, e)
            
        if message['content'].find('list_users') > -1:
            bot_handler.send_reply(message, str(self.whitelist))
        
        if message['content'].find('set_IP') > -1:
            IP = message['content'].split('set_IP ')[1].split('\n')[0]
            bot_handler.storage.put('IP',IP)
            
        if message['content'].find('get_IP') > -1:
            IP = bot_handler.storage.get('IP')
            reply_message = 'IP is: ' + IP
            bot_handler.send_reply(message, reply_message)
            
        if message['content'].find('set_PORTLIST') > -1:
            self.portlist = [int(x) for x in message['content'].split('set_PORTLIST ')[1].split(' ')]
            
        if message['content'].find('get_PORTLIST') > -1:
            reply_message = 'Available ports: ' + str(self.portlist)
            bot_handler.send_reply(message, reply_message)
            
        if message['content'].find('set_upload_method') > -1:
            upload_method = message['content'].split('set_upload_method ')[1].split('\n')[0]
            bot_handler.storage.put('upload_method', upload_method)
        
        if message['content'].find('survey') > -1:
            N_scans = 5
            if message['content'].find('-N=') > -1:
                N_scans = int(message['content'].split('-N=')[1].split(' ')[0])
            suffix = ''
            if message['content'].find('-S=') > -1:
                suffix = str(message['content'].split('-S=')[1].split(' ')[0])
            if not running.is_set():
                running.set()
                t = threading.Thread(target=lambda : self.survey_function(bot_handler, message, N_scans, suffix))
                tasks.append(t)
                t.start()
            else:
                bot_handler.send_reply(message, 'error: something already running')
            
        if message['content'].find('stop') > -1:
            ## press the stop button
            IP = str(bot_handler.storage.get('IP'))
            try:
                PORT = self.portlist.pop()
            except:
                bot_handler.send_reply(message, "No ports available")
                return
            try:
                NTCP = nanonisTCP(IP, PORT)
                scan = Scan(NTCP)
                scan.Action('stop')
                NTCP.close_connection()
            except Exception as e:
                bot_handler.send_reply(message, e)
            finally:
                self.portlist.append(PORT)
            
            while len(tasks) > 0:
                running.clear()
                tasks.pop().join()
                
        if message['content'].find('pause') > -1:
            pause.set()
            
        if message['content'].find('resume') > -1:
            pause.clear()
                
        if message['content'].find('plot') > -1:
            try:
                IP = str(bot_handler.storage.get('IP'))
                try:
                    PORT = self.portlist.pop()
                except:
                    bot_handler.send_reply(message, "No ports available")
                    return
                NTCP = nanonisTCP(IP, PORT)
                scan = Scan(NTCP)
                channel_name,scan_data,scan_direction = scan.FrameDataGrab(14, 1) ## 14 is Z
                self.send_plot(bot_handler, message, scan_data, scan_direction, file_path='')
                NTCP.close_connection()
            except Exception as e:
                bot_handler.send_reply(message, e)
            finally:
                self.portlist.append(PORT)
                
            
        
handler_class = ScanBot