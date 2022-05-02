#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May  2 14:51:27 2022

@author: jack
"""

import os
import time
from pathlib import Path

import matplotlib.pyplot as plt

from nanonisTCP import nanonisTCP
from nanonisTCP.Scan import Scan


class ScanBot(object):

    
    def handle_message(self, message, bot_handler):
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
            
        if message['content'].find('get_PORT') > -1:
            PORT = bot_handler.storage.get('PORT')
            reply_message = 'PORT is: ' + str(PORT)
            bot_handler.send_reply(message, reply_message)
            
        # if message['content'].find('auto approach') > -1:
        
        if message['content'].find('survey') > -1:
            IP = str(bot_handler.storage.get('IP'))
            PORT = int(bot_handler.storage.get('PORT'))
            NTCP = nanonisTCP(IP, PORT)
            scan = Scan(NTCP)
            frames = [[0,0,100e-9,100e-9], ## x,y,w,h,angle=0
                      [100e-9,100e-9,100e-9,100e-9],
                      [200e-9,100e-9,100e-9,100e-9],
                      [200e-9,-100e-9,100e-9,100e-9],
                ]

            for frame in frames:
                reply = 'running scan' + str(frame)
                bot_handler.send_reply(message, reply)
                scan.FrameSet(*frame)
                scan.Action('start')
                time.sleep(10)
                scan.Action('start')
                timeout_status, file_path_size, file_path = scan.WaitEndOfScan()
                channel_name,scan_data,scan_direction = scan.FrameDataGrab(14, 1) ## 14 is Z
                fig, ax = plt.subplots(1,1)
                ax.imshow(scan_data, origin='lower', cmap='Blues')
                ax.axis('off')
                fig.savefig('im.png', dpi=200, bbox_inches='tight', pad_inches=0)
                plt.close('all')
                path = os.getcwd() + '/im.png'
                path = Path(path)
                path = path.resolve()
                upload = bot_handler.upload_file_from_path(str(path))
                uploaded_file_reply = "[{}]({})".format(path.name, upload["uri"])
                bot_handler.send_reply(message, uploaded_file_reply)
            
        
handler_class = ScanBot