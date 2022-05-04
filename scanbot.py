#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May  2 14:51:27 2022

@author: jack
"""

import os
import signal
import time
from pathlib import Path
import threading

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
    
    def __init__(self):
        ## read in list of authorised users from whitelist.txt:
        self.whitelist = []
        try:
            with open('whitelist.txt', 'r') as f:
                d = f.read()
                self.whitelist = d.split('\n')[:-1]
        except:
            print('no whitelist')
    
    def send_plot(self, bot_handler, message, scan_data, scan_direction='up'):
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
        fig.savefig('im.png', dpi=60, bbox_inches='tight', pad_inches=0)
        plt.close('all')
        path = os.getcwd() + '/im.png'
        path = Path(path)
        path = path.resolve()
        upload = bot_handler.upload_file_from_path(str(path))
        uploaded_file_reply = "[{}]({})".format(path.name, upload["uri"])
        bot_handler.send_reply(message, uploaded_file_reply)
    
    def survey_function(self, bot_handler, message):
        IP = str(bot_handler.storage.get('IP'))
        PORT = int(bot_handler.storage.get('PORT'))
        NTCP = nanonisTCP(IP, PORT)
        scan = Scan(NTCP)

        frames = [] ## x,y,w,h,angle=0
        dx = 150e-9
        scansize = 100e-9
        for ii in range(-2,3):
            if ii % 2 == 0:
                for jj in range(-2,3):
                    frames.append([jj*dx, ii*dx, scansize, scansize])
            else:
                for jj in range(-2,3):
                    frames.append([-jj*dx, ii*dx, scansize, scansize])
            
        for frame in frames:
            if running.is_set():
                reply = 'running scan' + str(frame)
                bot_handler.send_reply(message, reply)
                scan.FrameSet(*frame)
                scan.Action('start')
                if not running.is_set(): break
                time.sleep(10)
                if not running.is_set(): break
                scan.Action('start')
                timeout_status, file_path_size, file_path = scan.WaitEndOfScan()
                channel_name,scan_data,scan_direction = scan.FrameDataGrab(14, 1) ## 14 is Z
                
                self.send_plot(bot_handler, message, scan_data, scan_direction)
                
                # fig, ax = plt.subplots(1,1)
                # ## light image processing
                # mask = np.isnan(scan_data)
                # scan_data[mask == True] = np.nanmean(scan_data)
                # scan_data = nap.plane_fit_2d(scan_data)
                # vmin, vmax = nap.filter_sigma(scan_data)
                #
                # ax.imshow(scan_data, origin='lower', cmap='Blues_r', vmin=vmin, vmax=vmax)
                # ax.axis('off')
                # fig.savefig('im.png', dpi=60, bbox_inches='tight', pad_inches=0)
                # plt.close('all')
                # path = os.getcwd() + '/im.png'
                # path = Path(path)
                # path = path.resolve()
                # upload = bot_handler.upload_file_from_path(str(path))
                # uploaded_file_reply = "[{}]({})".format(path.name, upload["uri"])
                # bot_handler.send_reply(message, uploaded_file_reply)
        NTCP.close_connection()
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
            
        if message['content'].find('set_PORT') > -1:
            PORT = message['content'].split('set_PORT ')[1].split('\n')[0]
            bot_handler.storage.put('PORT',PORT)
            
        if message['content'].find('set_stop_PORT') > -1:
            PORT = message['content'].split('set_stop_PORT ')[1].split('\n')[0]
            bot_handler.storage.put('stop_PORT',PORT)
            
        if message['content'].find('get_PORT') > -1:
            PORT = bot_handler.storage.get('PORT')
            reply_message = 'PORT is: ' + str(PORT)
            bot_handler.send_reply(message, reply_message)
            
        # if message['content'].find('auto approach') > -1:
        
        if message['content'].find('survey') > -1:
            if not running.is_set():
                running.set()
                t = threading.Thread(target=lambda : self.survey_function(bot_handler, message))
                tasks.append(t)
                t.start()
            else:
                bot_handler.send_reply(message, 'error: something already running')
            
        if message['content'].find('stop') > -1:
            ## press the stop button
            IP = str(bot_handler.storage.get('IP'))
            try:
                PORT = int(bot_handler.storage.get('stop_PORT'))
            except:
                PORT = 6504
            try:
                NTCP = nanonisTCP(IP, PORT)
                scan = Scan(NTCP)
                scan.Action('stop')
                NTCP.close_connection()
            except Exception as e:
                bot_handler.send_reply(message, e)
            
            while len(tasks) > 0:
                running.clear()
                tasks.pop().join()
                
        if message['content'].find('plot') > -1:
            try:
                IP = str(bot_handler.storage.get('IP'))
                PORT = int(bot_handler.storage.get('PORT'))
                NTCP = nanonisTCP(IP, PORT)
                scan = Scan(NTCP)
                channel_name,scan_data,scan_direction = scan.FrameDataGrab(14, 1) ## 14 is Z
                self.send_plot(bot_handler, message, scan_data)
                NTCP.close_connection()
            except Exception as e:
                bot_handler.send_reply(message, e)
                
            
        
handler_class = ScanBot