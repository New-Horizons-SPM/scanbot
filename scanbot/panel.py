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
    prev_STMControlForm = {}
    tempFolder = "temp/"
    
    def __init__(self):
        pn.extension(template=self.template)
        self.interface = scanbot_interface(run_mode='p',panel=self)
        self.initFunctions()
        Path(self.tempFolder).mkdir(exist_ok=True)
    
    def initFunctions(self):
        options = ['Configuration','Survey','Bias Dependent', 'STM Control']
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
        
        if(name == 'STM Control'):
            self.sidebarForm = self.getSTMControlForm()
            
        for form in self.sidebarForm:
            if(len(form.keys())):
                for f in form.values(): self.sidebarColumn.append(f)
    
    def getSTMControlForm(self):
        if(self.prev_STMControlForm): return self.prev_STMControlForm
        
        form1 = {}
        form1['-up']    = pn.widgets.TextInput(name='Steps to take in Z+ before moving in X/Y', value="50")
        form1['-steps'] = pn.widgets.TextInput(name='Steps to move across', value="20")
        form1['-dir']   = pn.widgets.Select(name='Direction', options=["X+","X-","Y+","Y-"],value="X+")
        form1['-upV']   = pn.widgets.TextInput(name='Piezo amplitude during Z+ steps (V)', value="180")
        form1['-upF']   = pn.widgets.TextInput(name='Piezo frequency during Z+ steps (Hz)', value="2000")
        form1['-dirV']  = pn.widgets.TextInput(name='Piezo amplitude during X/Y steps (V)', value="130")
        form1['-dirF']  = pn.widgets.TextInput(name='Piezo frequency during X/Y steps (Hz)', value="2000")
        form1['-zon']   = pn.widgets.Select(name='Turn z-controller on after move', options={"Turn on": 1,"Leave off": 0},value=0)
        
        buttonMove = pn.widgets.Button(name='Start Move', button_type='primary')
        buttonMove.on_click(self.moveArea)
        
        form1['button1'] = pn.Row(buttonMove)
        
        form2 = {}
        form2['-sod']   = pn.widgets.TextInput(name='Switch off delay (s)', value="0.1")
        form2['-cb']    = pn.widgets.Select(name='Change bias?', options={"Yes":1,"No":0},value=0)
        form2['-b1']    = pn.widgets.TextInput(name='B1: Bias to change to if yes (V)', value="0.4")
        form2['-z1']    = pn.widgets.TextInput(name='Z1: First tip lift (m)', value="-2e-9")
        form2['-t1']    = pn.widgets.TextInput(name='T1: Time to ramp Z1 (s)', value="0.1")
        form2['-b2']    = pn.widgets.TextInput(name='B2: Bias applied just after the first Z ramping', value="-0.4")
        form2['-t2']    = pn.widgets.TextInput(name='T2: Time to wait before second tip lift (s)', value="0.1")
        form2['-z2']    = pn.widgets.TextInput(name='Z2: Second tip lift (m)', value="4e-9")
        form2['-t3']    = pn.widgets.TextInput(name='T3: Time to ramp Z2 (s)', value="0.1")
        form2['-wait']  = pn.widgets.TextInput(name='T4: Time to wait before restoring the initial bias (s)', value="0.1")
        form2['-fb']    = pn.widgets.Select(name='Turn feedback on after tip shape?', options={"Yes":1,"No":0},value=1)
        
        buttonUpdate = pn.widgets.Button(name='Update Props', button_type='primary')
        buttonUpdate.on_click(self.updateTipShape)
        
        buttonTipShape = pn.widgets.Button(name='Tip Shape', button_type='primary')
        buttonTipShape.on_click(self.tipShape)
        
        form2['buttons'] = pn.Row(buttonTipShape,buttonUpdate)
        
        return [form1,form2]
    
    def tipShape(self,event):
        if(self.running):
            print("Already running",self.running)
            return
        
        self.prev_STMControlForm = self.sidebarForm.copy()
        
        args = self.unpack(self.sidebarForm[1])
        error = self.interface.tipShapeProps(args)
        print(error)
        if(not error):
            print(self.interface.tipShape([]))
    
    def updateTipShape(self,event):
        self.prev_STMControlForm = self.sidebarForm.copy()
        
        args = self.unpack(self.sidebarForm[1]) 
        print(self.interface.tipShapeProps(args))
    
    def moveArea(self,event):
        if(self.running):
            print("Already running",self.running)
            return
        
        self.prev_STMControlForm = self.sidebarForm.copy()
        
        args = self.unpack(self.sidebarForm[0]) 
        print(self.interface.moveArea(args))
        
    def getConnectionForm(self):
        form = {}
        form['IP']            = pn.widgets.TextInput(name='IP Address', value=self.interface.IP)
        form['Ports']         = pn.widgets.TextInput(name='Port list (space delimited)', value=' '.join(np.array(self.interface.portList).astype(str)))
        form['Upload Method'] = pn.widgets.Select(name='Upload method', options=self.interface.validUploadMethods,value=self.interface.uploadMethod)
        form['Path']          = pn.widgets.TextInput(name='Save path', value=self.interface.path)
        # form['Crash Safety']  = pn.widgets.TextInput(name='IP Address', value=self.interface.IP)self.interface.getCrashSafety([])
        
        submitButton = pn.widgets.Button(name='Update Configuration', button_type='primary')
        submitButton.on_click(self.updateConfig)
        
        form['buttons'] = pn.Row(submitButton)
        
        return [form]
    
    def updateConfig(self,event):
        config = self.sidebarForm[0]
        self.interface.setIP([config['IP'].value])
        self.interface.setPortList(config['Ports'].value.split(' '))
        self.interface.setUploadMethod(config['Upload Method'].value)
        self.interface.setPath([config['Path'].value])
        
        
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
        
        return [form]
        
        
    def getSurveyForm(self):
        if(self.prev_surveyForm):
            form = self.prev_surveyForm
            return form
        
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
        
        return [form]
    
    def updatePNG(self,path):
        fig = plt.figure()
        ax = fig.add_subplot(111)
        im  = Image.open(path)
        img = np.array(im)
        ax.imshow(img)
        ax.axis('off')
        ax.set_position([0,0,1,1])
        if(self.running == "Survey"):
            n = int(self.sidebarForm[0]['-n'].value) - 1
            ny,nx = self.surveyIDX
            self.mainGridSpec[n-int(ny),n-int(nx)] = pn.pane.Matplotlib(fig)
            
            if(nx*ny == n**2):
                self.running = ""
                self.functionWidget.disabled_options = []
            
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
            
            self.biasDepIDX += 1
            if(self.biasDepIDX == int(self.sidebarForm[0]['-n'].value)):
                self.running = ""
            
        plt.close(fig)
        
    def make_gif(self,frames,path="biasdep.gif"):
        frame_one = frames[0]
        frame_one.save(self.tempFolder + path, format="GIF", append_images=frames,
                   save_all=True, duration=500, loop=0)
        return self.tempFolder + path
    
    def stop(self,event):
        self.interface.stop()
        self.running = ""
        self.functionWidget.disabled_options = []
        
    def startSurvey(self,event):
        if(self.running):
            print("Already running",self.running)
            return
        
        disabled_options = self.functionWidget.options.copy()
        disabled_options.remove("Survey")
        self.functionWidget.disabled_options = disabled_options
        self.prev_surveyForm = self.sidebarForm.copy()
        
        args = self.unpack(self.sidebarForm[0]) 
        self.interface.survey(args)
        
        surveyForm = self.sidebarForm[0]
        n = int(surveyForm['-n'].value)
        
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
        
        args = self.unpack(self.sidebarForm[0]) 
        self.interface.biasDep(args)
        
        self.mainGridSpec.objects = OrderedDict()
        self.mainGridSpec[0,1] = pn.Spacer(styles=dict(background='grey'))
        self.mainGridSpec[0,0] = pn.Spacer(styles=dict(background='red'))
        
        self.biasDepImages = []
        
        self.biasDepIDX = 0
        self.running = "BiasDep"
        
    def unpack(self,form):
        args = []
        for key,value in form.items():
            if(key.startswith("-")):
                args.append(key + "=" + str(value.value))
        return args
    
ScanbotPanel()