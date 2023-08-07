# -*- coding: utf-8 -*-
"""
Created on Thu Aug  3 08:43:33 2023

@author: jced0001
"""

import panel as pn
from scanbot_interface import scanbot_interface
import param
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from collections import OrderedDict
matplotlib.use('agg')

from PIL import Image
from pathlib import Path

class ScanbotPanel(param.Parameterized):
    template = 'fast'
    sidebarColumn = []
    function = {}
    running = ""
    prev_surveyForm  = {}
    prev_biasdepForm = {}
    tempFolder = "temp/"
    
    def __init__(self):
        pn.extension(template=self.template)
        self.interface = scanbot_interface(run_mode='p',panel=self)
        self.initFunctions()
        Path(self.tempFolder).mkdir(exist_ok=True)
    
    def initFunctions(self):
        options = ['Configuration','Survey','Bias Dependent']
        # Connection
        self.functionWidget = pn.widgets.Select(name='Select', options=options)
        interactive = pn.bind(self.selectFunction,self.functionWidget)
        
        self.sidebarColumn = pn.Column(self.functionWidget,interactive)
        self.sidebarColumn.servable(target="sidebar")
        
        self.selectFunction(name=options[0])
        
        self.mainGridSpec = pn.GridSpec(sizing_mode='stretch_both',mode='override')
        self.mainGridSpec.servable(target="main")
        # self.mainGridSpec[0, :3] = pn.Spacer(styles=dict(background='#FF0000'))
        
    
    def selectFunction(self,name):
        while(len(self.sidebarColumn) > 2):
            self.sidebarColumn.pop(-1)
        
        self.sidebarForm = []
        if(name == 'Configuration'):
            self.sidebarForm = self.getConnectionForm()
        
        if(name == 'Survey'):
            self.sidebarForm = self.getSurveyForm()
        
        if(name == 'Bias Dependent'):
            self.sidebarForm = self.getBiasDepForm()
        
        if(len(self.sidebarForm.keys())):
            for f in self.sidebarForm.values(): self.sidebarColumn.append(f)
        
    def getConnectionForm(self):
        fields = {}
        fields['IP']            = self.interface.IP
        fields['Ports']         = ','.join(np.array(self.interface.portList).astype(str))
        fields['Upload Method'] = self.interface.uploadMethod
        fields['Path']          = self.interface.path
        fields['Whitelist']     = ','.join(np.array(self.interface.whitelist))
        if(not fields['Whitelist']): fields['Whitelist'] = "Open"
        fields['Crash Safety']  = "\n" + self.interface.getCrashSafety([])
        
        return {'fields': pn.panel(fields)}
    
    def getBiasDepForm(self):
        if(self.prev_biasdepForm):
            form = self.prev_biasdepForm.copy()
            return form
        
        form = {}
        options = list(np.arange(20)+1)
        form['-n']     = pn.widgets.Select(name='Number of images', options=options)
        form['-bi']    = pn.widgets.TextInput(name='Initial bias', value="-1")
        form['-bf']    = pn.widgets.TextInput(name='Final bias', value="1")
        form['-px']    = pn.widgets.TextInput(name='Pixels in data image', value="256")
        form['-lx']    = pn.widgets.TextInput(name='Lines in data image (0 = same as pixels)', value="0")
        form['-tlf']   = pn.widgets.TextInput(name='Time per line during data acquisition (s)', value="0.5")
        form['-tb']    = pn.widgets.TextInput(name='Backwards time per line multiplier (s)', value="1")
        form['-pxdc']  = pn.widgets.TextInput(name='Pixels in drift correction image (0 = off)', value="128")
        form['-lxdc']  = pn.widgets.TextInput(name='Lines in drift correction image (0 = same ratio as data)', value="0")
        form['-bdc']   = pn.widgets.TextInput(name='Bias during drift correction (V)', value="0.5")
        form['-tdc']   = pn.widgets.TextInput(name='Time per line during drift correction (s)', value="0.3")
        form['-tbdc']  = pn.widgets.TextInput(name='Backwards time per line multiplier (s)', value="1")
        form['-s']     = pn.widgets.TextInput(name='Suffix', value='scanbot_biasdep')
        
        buttonStart = pn.widgets.Button(name='Start Bias Dep', button_type='primary')
        buttonStart.on_click(self.startBiasDep)
        
        buttonStop = pn.widgets.Button(name='Stop Bias Dep', button_type='primary')
        buttonStop.on_click(self.stop)
        
        form['buttons'] = pn.Row(buttonStart,buttonStop)
        
        return form
        
        
    def getSurveyForm(self):
        form = {}
        options = list(np.arange(10)+1)
        form['-n']     = pn.widgets.Select(name='Grid size (NxN)', options=options)
        form['-xy']    = pn.widgets.TextInput(name='Scan size (m)', value="50e-9")
        form['-dx']    = pn.widgets.TextInput(name='Scan spacing (m)', value="50e-9")
        form['-px']    = pn.widgets.TextInput(name='Number of pixels', value="256")
        form['-bias']  = pn.widgets.TextInput(name='Scan bias', value="1")
        form['-s']     = pn.widgets.TextInput(name='Suffix', value='scanbot_survey')
        form['-st']    = pn.widgets.TextInput(name='Drift compensation (s)', value="10")
        
        buttonStart = pn.widgets.Button(name='Start Survey', button_type='primary')
        buttonStart.on_click(self.startSurvey)
        
        buttonStop = pn.widgets.Button(name='Stop Survey', button_type='primary')
        buttonStop.on_click(self.stop)
        
        form['buttons'] = pn.Row(buttonStart,buttonStop)
        
        return form
    
    def updatePNG(self,path):
        fig = plt.figure()
        ax = fig.add_subplot(111)
        im  = Image.open(path)
        img = np.array(im)
        ax.imshow(img)
        ax.axis('off')
        ax.set_position([0,0,1,1])
        if(self.running == "Survey"):
            n = int(self.sidebarForm['-n'].value) - 1
            ny,nx = self.surveyIDX
            self.mainGridSpec[n-int(ny),n-int(nx)] = pn.pane.Matplotlib(fig)
            
            if(nx*ny == n**2):
                self.running = ""
            
            self.surveyIDX += np.array([0,1])
            
            if(nx == n):
                self.surveyIDX[0] += 1
                self.surveyIDX[1]  = 0
                
        if(self.running == "BiasDep"):
            self.biasDepImages.append(im.copy())
            path1 = self.make_gif([im],"lastim.gif")
            path2  = self.make_gif(self.biasDepImages)
            self.mainGridSpec[0,0] = pn.pane.GIF(path1)
            self.mainGridSpec[0,1] = pn.pane.GIF(path2)
            
        plt.close(fig)
        
    def make_gif(self,frames,path="biasdep.gif"):
        frame_one = frames[0]
        frame_one.save(self.tempFolder + path, format="GIF", append_images=frames,
                   save_all=True, duration=500, loop=0)
        return self.tempFolder + path
    
    def stop(self,event):
        self.interface.stop()
        self.surveyIDX = 0
        self.running = ""
        
    def startSurvey(self,event):
        if(self.running):
            print("Already running",self.running)
            return
        
        self.prev_surveyForm = self.sidebarForm.copy()
        
        args = self.unpack(self.sidebarForm) 
        self.interface.survey(args)
        n = int(self.sidebarForm['-n'].value)
        
        self.surveyIDX = np.array([0,0])
        
        self.mainGridSpec.objects = OrderedDict()
        for i in range(n):
            for j in range(n):
                self.mainGridSpec[i,j] = pn.Spacer(styles=dict(background='grey'))
                
        self.running = "Survey"
    
    def startBiasDep(self,event):
        if(self.running):
            print("Already running",self.running)
            return
        
        self.prev_biasdepForm = self.sidebarForm.copy()
        
        args = self.unpack(self.sidebarForm) 
        self.interface.biasDep(args)
        
        self.mainGridSpec.objects = OrderedDict()
        self.mainGridSpec[0,1] = pn.Spacer(styles=dict(background='grey'))
        self.mainGridSpec[0,0] = pn.Spacer(styles=dict(background='red'))
        
        self.biasDepImages = []
        
        self.running = "BiasDep"
        
    def unpack(self,form):
        args = []
        for key,value in form.items():
            if(key.startswith("-")):
                args.append(key + "=" + str(value.value))
        return args
    
ScanbotPanel()