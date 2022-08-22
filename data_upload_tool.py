# -*- coding: utf-8 -*-
"""
Created on Thu Aug 18 09:44:57 2022

Script to dump files from a local folder into a zulip thread for labelling.
Currently, only firebase is supported

@author: Julian
"""

import zulip
import firebase_admin
from firebase_admin import credentials, storage

import os
import sys
import subprocess
from pathlib import Path
from tkinter import filedialog
import utilities
import nanonispy as nap
import nanonispyfit as napfit
import numpy as np
import matplotlib.pyplot as plt
import ntpath
import time
import pickle

def firebaseInit(firebaseCert,firebaseStorageBucket):
    try:
        print("Initialising firebase app")
        cred = credentials.Certificate(firebaseCert)                            # Your firebase credentials
        firebase_admin.initialize_app(cred, {
            'storageBucket': firebaseStorageBucket                              # Your firebase storage bucket
        })
    except Exception as e:
        print(e)

def loadConfig():
    """
    Read in the scanbot_config.ini configuration file. File format is:
        key1=value1
        key2=value2

    """
    print("Loading scanbot_config.ini...")
    initDict = {'zuliprc'                   : 'zuliprc',                        # Zulip rc file. See https://zulip.com/api/running-bots
                'path'                      : 'scanbot/uploads',                # Firebase path to save data
                'firebase_credentials'      : 'firebase.json',                  # Credentials for firebase (if upload_method=firebase)
                'firebase_storage_bucket'   : '',                               # Firebase bucket. Firebase path uses "path" key
                'notify_list'               : '',                               # Comma delimited zulip users to @notify when sending data
                'send_to_cloud'             : '0',                              # Flag to send data to the cloud. cloud_path is also used to save data locally when send_to_cloud = 0
                'cloud_path'                : ''}                               # user@clouddatabase:path. cloud_path is also used to save data locally when send_to_cloud = 0
    
    try:
        with open('scanbot_config.ini','r') as f:                               # Go through the config file to see what defaults need to be overwritten
            line = "begin"
            while(line):
                line = f.readline()[:-1]
                if(line.startswith('#')): print(line); continue                 # Comment
                if(not '=' in line):
                    print("Warning, invalid line in config file: " + line)
                    continue
                key, value = line.split('=')                                    # Format for valid line is "Key=Value"
                if(not key in initDict):                                        # Key must be one of initDict keys
                    # print("Invalid key in scanbot_config.txt: " + key)
                    continue
                initDict[key] = value                                           # Overwrite default value
    except:
        print("Config file not found, using defaults...")
    
    zuliprc = initDict['zuliprc']
    path    = initDict['path']
    
    if(not zuliprc):
        raise Exception("Check config file. zuliprc required")
    
    if(not path):
        raise Exception("Check config file. Missing path")
    
    if(not path.endswith('/')):
        path += '/'
    
    firebaseCert = initDict['firebase_credentials']
    firebaseStorageBucket = initDict['firebase_storage_bucket']
    
    if(not firebaseStorageBucket):
        raise Exception("Storage bucket must be provided for upload_method=firebase")
    if(not path):
        raise Exception("Storage path must be provided for upload_method=firebase")
        
    firebaseInit(firebaseCert,firebaseStorageBucket)                            # Initialise Firebase
    
    zulipClient = zulip.Client(config_file=zuliprc)
    
    sendToCloud = initDict['send_to_cloud']
    cloudPath   = initDict['cloud_path']
    if(not cloudPath):
        raise Exception("Check config file... cloud path not provided\n" + 
                        "cloud_path is also used to save data locally when send_to_cloud = 0")
    if(not cloudPath.endswith('/')):
        cloudPath += '/'
        
    return zulipClient, path, sendToCloud, cloudPath

def uploadToCloud(filename,cloudPath):
    if(not filename.endswith(".pkl")):
        print("Error, not a pickle file")
    try:
        subprocess.run(["scp", filename, cloudPath])
        os.remove(filename)
    except Exception as e:
        print("Error uploading file to cloud with command\nscp " +
                       filename + " " + cloudPath + "\n\n" + str(e))

def makePNG(scanData,filePath):
    fig, ax = plt.subplots(1,1)
    
    mask = np.isnan(scanData)                                                   # Mask the Nan's
    scanData[mask == True] = np.nanmean(scanData)                               # Replace the Nan's with the mean so it doesn't affect the plane fit
    scanData = napfit.plane_fit_2d(scanData)                                    # Flattern the image
    vmin, vmax = napfit.filter_sigma(scanData)                                  # cmap saturation
    
    ax.imshow(scanData, cmap='Blues_r', vmin=vmin, vmax=vmax)                   # Plot
    ax.axis('off')
    
    pngFilename = ntpath.split(filePath)[1] + '.png'
    
    fig.savefig(pngFilename, dpi=60, bbox_inches='tight', pad_inches=0)
    plt.close('all')
    
    return pngFilename

def uploadPNG(pngFilename,path,uploadMethod="firebase"):
    notifyString = ""
    # if(notify):
    #     for user in self.notifyUserList:
    #         notifyString += "@**" + user + "** "
        
    localPath = os.getcwd() + '/' + pngFilename
    localPath = Path(localPath)
    localPath = localPath.resolve()
    
    message = ""
    # if(self.uploadMethod == 'zulip'):
    #     upload = self.bot_handler.upload_file_from_path(str(path))
    #     uploaded_file_reply = "[{}]({})".format(path.name, upload["uri"])
    #     self.sendReply(notifyString + pngFilename,message)
    #     self.sendReply(uploaded_file_reply,message)
    #     os.remove(path)
        
    if(uploadMethod == 'firebase'):
        bucket = storage.bucket()
        blob   = bucket.blob(path + pngFilename)
        blob.upload_from_filename(str(localPath))
    
        url = blob.generate_signed_url(expiration=9999999999)
        message = notifyString + "[" + pngFilename + "](" + url + ")"
        os.remove(localPath)
    return message
    
def sendMessage(zulipClient,message):
    request = {
        "type": "stream",
        "to": "scanbot",
        "topic": "Data Upload",
        "content": message}
    zulipClient.send_message(request)
    
def browseFolder():
    path = filedialog.askdirectory(title='Select Folder')                       # shows dialog box and return the path
    return path
###############################################################################
#
###############################################################################
zulipClient, path, sendToCloud, cloudPath = loadConfig()

try:
    alreadyUploaded = pickle.load(open(cloudPath + 'uploaded_directories.pkl','rb')) # Keep track of directories we've already uploaded
except:
    alreadyUploaded = []
    
uploadFolder = browseFolder()
while(uploadFolder):
    if(uploadFolder in alreadyUploaded):
        print("Path already uploaded:\n" + uploadFolder)
        uploadFolder = browseFolder()
        continue
        
    file_list = os.listdir(uploadFolder)
    sxmFiles = [uploadFolder + "/" + f for f in file_list if f.endswith(".sxm")]    # Get .sxm filenames in selected directory
    sendMessage(zulipClient,"---\nUploading data from local path\n" + uploadFolder)
    for sxmFile in sxmFiles:
        try:
            sxm = nap.read.Scan(sxmFile)
            scanData = np.array(sxm.signals["Z"]['forward'])
            if(np.isnan(scanData).any()): continue
            x,y = sxm.header['scan_offset']
            w,h = sxm.header['scan_range']
            angle = float(sxm.header['scan_angle'])
            pixels,lines = sxm.header['scan_pixels']
            comments = "Data upload tool"
            
            pngFilename = makePNG(scanData,sxmFile)
            message = uploadPNG(pngFilename,path,uploadMethod="firebase")
            sendMessage(zulipClient,message)
            
            pklFile = utilities.pklDict(scanData, sxmFile, x, y, w, h, angle, pixels, lines)
            uploadToCloud(pklFile,cloudPath)
            time.sleep(0.2)
        except:
            print("error processing " + sxmFile)
    
    alreadyUploaded.append(uploadFolder)
    uploadFolder = browseFolder()


pickle.dump(alreadyUploaded, open(cloudPath + 'uploaded_directories.pkl', 'wb'))     # Pickle containing entire list of directories already uploaded
