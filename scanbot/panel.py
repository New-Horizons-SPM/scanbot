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
    sidebarColumn = []
    function = {}
    running = ""
    prev_surveyForm  = {}
    prev_biasdepForm = {}
    prev_STMControlForm = {}
    prev_AutomationForm = {}
    tempFolder = "temp/"
    
    def __init__(self):
        pn.extension(template="fast")
        pn.config.template.title = "Scanbot"
        self.interface = scanbot_interface(run_mode='p',panel=self)
        self.initFunctions()
        Path(self.tempFolder).mkdir(exist_ok=True)
        
        
    def initFunctions(self):
        options = ['Configuration','Survey','Bias Dependent', 'STM Control','Automation']
        # Connection
        self.functionWidget = pn.widgets.Select(name='Select', options=options)
        interactive = pn.bind(self.selectFunction,self.functionWidget)
        
        self.sidebarColumn = pn.Column(self.functionWidget,interactive)
        self.sidebarColumn.servable(target="sidebar")
        
        self.selectFunction(name=options[0])
        
        self.mainGridSpec = pn.GridSpec(sizing_mode='stretch_both',mode='override')
        self.mainGridSpec.servable(target="main")
        
    
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
        
        if(name == 'Automation'):
            self.sidebarForm = self.getAutomationForm()
            
        for form in self.sidebarForm:
            if(len(form.keys())):
                for f in form.values(): self.sidebarColumn.append(f)
    
    def getAutomationForm(self):
        if(self.prev_AutomationForm): return self.prev_AutomationForm
        
        form1 = {}
        form1['-cameraPort'] = pn.widgets.Select(name='Camera port', options={"0":0,"1":1,"2":2,"3":3,"4":4},value=0)
        form1['-demo']       = pn.widgets.Select(name='Demo/Live mode', options={"Live":0,"Demo":1},value=1)
        
        buttonInit = pn.widgets.Button(name='Initialise Tip Position', button_type='primary')
        buttonInit.on_click(self.autoInit)
        
        form1['button1'] = pn.Row(buttonInit)
        
        form2 = {}
        form2['-light']      = pn.widgets.Select(name='Control light with hk_light.py?', options={"No":0,"Yes":1},value=0)
        form2['-cameraPort'] = pn.widgets.Select(name='Camera port', options={"0":0,"1":1,"2":2,"3":3,"4":4},value=0)
        form2['-demo']       = pn.widgets.Select(name='Demo/Live mode', options={"Live":0,"Demo":1},value=1)
        form2['-zStep']      = pn.widgets.TextInput(name='Steps at a time in Z+ direction', value="250")
        form2['-zV']         = pn.widgets.TextInput(name='Piezo voltage when moving tip in Z+ (V)', value="150")
        form2['-zF']         = pn.widgets.TextInput(name='Piezo frequency when moving tip in Z+ (Hz)', value="2000")
        form2['-xStep']      = pn.widgets.TextInput(name='Steps at a time in X+/- direction', value="100")
        form2['-xV']         = pn.widgets.TextInput(name='Piezo voltage when moving tip in X+/- (V)', value="80")
        form2['-xF']         = pn.widgets.TextInput(name='Piezo frequency when moving tip in X+/- (Hz)', value="2000")
        form2['-approach']   = pn.widgets.Select(name='Approach when tip reaches target?', options={"No":0,"Yes":1},value=0)
        form2['-tipshape']   = pn.widgets.Select(name='Initiate auto tip shape on approach?', options={"No":0,"Yes":1},value=0)
        form2['-return']     = pn.widgets.Select(name='Return to sample after auto tip shape?', options={"No":0,"Yes":1},value=0)
        form2['-run']        = pn.widgets.Select(name='Run a survey upon return?', options={"No":"","Yes":"survey"},value="")
        
        buttonSample = pn.widgets.Button(name='Go to sample', button_type='primary')
        buttonSample.on_click(self.goToSample)
        
        buttonMetal = pn.widgets.Button(name='Go to metal', button_type='primary')
        buttonMetal.on_click(self.goToMetal)
        
        form2['button2'] = pn.Row(buttonSample,buttonMetal)
        
        return [form1,form2]
    
    def goToSample(self,event):
        if(self.running):
            print("Already running",self.running)
            return
        
        self.prev_AutomationForm = self.sidebarForm.copy()
        
        args = self.unpack(self.sidebarForm[1])
        print(self.interface.moveTipToSample(args))
    
    def goToMetal(self,event):
        if(self.running):
            print("Already running",self.running)
            return
        
        self.prev_AutomationForm = self.sidebarForm.copy()
        
        args = self.unpack(self.sidebarForm[1])
        print(self.interface.moveTipToClean(args))
        
    def autoInit(self,event):
        if(self.running):
            print("Already running",self.running)
            return
        
        self.prev_AutomationForm = self.sidebarForm.copy()
        
        args = self.unpack(self.sidebarForm[0])
        print("Args:",args)
        self.interface.autoInit(args)
        
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
        form['-n']     = pn.widgets.Select(name='Survey fine grid size (NxN)', options=options)
        form['-nx']    = pn.widgets.Select(name='Survey course grid size X', options=options)
        form['-ny']    = pn.widgets.Select(name='Survey course grid size Y', options=options)
        form['-i']     = pn.widgets.TextInput(name='Start index', value="0")
        
        form['-xy']    = pn.widgets.TextInput(name='Scan size (m)', value="5e-9")
        form['-dx']    = pn.widgets.TextInput(name='Scan spacing (m)', value="5e-9")
        form['-px']    = pn.widgets.TextInput(name='Number of pixels', value="128")
        form['-bias']  = pn.widgets.TextInput(name='Scan bias', value="1")
        
        form['-s']     = pn.widgets.TextInput(name='Filename suffix', value='scanbot_survey')
        form['-st']    = pn.widgets.TextInput(name='Drift compensation (s)', value="0.1")
        
        # Motor params
        form['-zStep'] = pn.widgets.TextInput(name='Number of motor steps (Z+)', value="50")
        form['-zV']    = pn.widgets.TextInput(name='Piezo voltage during Z+ motor steps (V)', value="100")
        form['-zF']    = pn.widgets.TextInput(name='Piezo frequency during Z+ motor steps (Hz)', value="2000")
        form['-xStep'] = pn.widgets.TextInput(name='Number of motor steps (X)', value="20")
        form['-yStep'] = pn.widgets.TextInput(name='Number of motor steps (Y)', value="20")
        form['-xyV']   = pn.widgets.TextInput(name='Piezo voltage during XY motor steps (V)', value="120")
        form['-xyF']   = pn.widgets.TextInput(name='Piezo frequency during XY motor steps (Hz)', value="2000")
        
        # Hooks
        form["-hk_survey"]     = pn.widgets.Select(name='Call hk_survey.py after each image?', options={"No":0,"Yes":1},value=0)
        form["-hk_classifier"] = pn.widgets.Select(name='Call hk_classifier.py instead of default classifier?', options={"No":0,"Yes":1},value=0)
        form["-autotip"]       = pn.widgets.Select(name='Auto tip shaping?', options={"No":0,"Yes":1},value=0)
        
        buttonStart = pn.widgets.Button(name='Start Survey', button_type='primary')
        buttonStart.on_click(self.startSurvey)
        
        buttonStop = pn.widgets.Button(name='Stop Survey', button_type='primary')
        buttonStop.on_click(self.stop)
        
        form['buttons'] = pn.Row(buttonStart,buttonStop)
        
        return [form]
    
    def updatePNG(self,path):
        """
        This function is called by sendPNG in scanbot_interface each time a PNG
        is generated. This function handles incoming PNGs for all scanbot 
        functions that are called via the holoviz panel interface.

        Parameters
        ----------
        path : Path to the PNG

        """
        fig = plt.figure()                                                      # Backend figure
        ax = fig.add_subplot(111)
        im  = Image.open(path)                                                  # Open the PNG file
        img = np.array(im)                                                      # Convert it to numpy array
        ax.imshow(img)                                                          # Show it on an axis
        ax.axis('off')
        ax.set_position([0,0,1,1])                                              # Make it take up the entire axis
        if(self.running == "Survey"):                                           # When we're running a survey, the images are related to that survey
            if("_stitch.png" in path.name):                                     # Skip the stitched survey PNGs
               return
           
            n = int(self.sidebarForm[0]['-n'].value) - 1                        # Number of images in each survey (nxn)
            NX = int(self.sidebarForm[0]['-nx'].value)                          # Number of surveys to do in X direction of course grid
            NY = int(self.sidebarForm[0]['-ny'].value)                          # Number of surveys to do in Y direction of course grid
            
            ny,nx = self.surveyIDX                                              # Keeping track of the index of the image we're up to in the survey
            self.mainGridSpec[n-int(ny),n-int(nx)] = pn.pane.Matplotlib(fig)    # Plot the next image at this locatino in the gridspec
            
            self.surveyIDX += np.array([0,1])                                   # Incremeent the image index
            if(nx == n):                                                        # If we've reached the end of a column...
                self.surveyIDX[0] += 1                                          # Incrememnt the row
                self.surveyIDX[1]  = 0                                          # Reset the column number. Not quite correct because the survey snakes. Fix later
            
            if(nx*ny == n**2):                                                  # If that was the last image in a survey...
                self.surveyCount += 1                                           # Incrememnt the survey number (this is for when multiple surveys are being carried out automatically)
                self.surveyIDX = np.array([0,0])
                if(self.surveyCount == NX*NY - 1):                              # If the final survey has been completed...
                    self.running = ""                                           # Clear the running flag
                    self.functionWidget.disabled_options = []                   # and re-enable the other options in the commands dropdown
                
        if(self.running == "BiasDep"):                                          # Bias dependent images
            self.biasDepImages.append(im.copy())                                # Running array of all the bias dep images - to be turned into a gif
            path1 = self.make_gif([im],"lastim.gif")                            # Create a gif of the current image (easier this way for some reason)
            path2  = self.make_gif(self.biasDepImages)                          # Create a gif of all previous images
            self.mainGridSpec[0,0] = pn.pane.GIF(path1)                         # Show the latest image on the left
            self.mainGridSpec[0,1] = pn.pane.GIF(path2)                         # Show a gif of all the completed bias dependent images on the right
            
            self.biasDepIDX += 1                                                # Keep track of the image index we're up to
            if(self.biasDepIDX == int(self.sidebarForm[0]['-n'].value)):        # If we've completed all our images
                self.running = ""                                               # Clear the running flag
                self.functionWidget.disabled_options = []                       # and re-enable the other options in the commands dropdown
            
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
        self.interface.survey2(args)
        
        surveyForm = self.sidebarForm[0]
        n = int(surveyForm['-n'].value)
        
        self.surveyIDX = np.array([0,0])
        self.surveyCount = 0
        
        self.mainGridSpec.objects = OrderedDict()
        for i in range(n):
            for j in range(n):
                self.mainGridSpec[i,j] = pn.Spacer(styles=dict(background='grey'))
                
        self.running = "Survey"
    
    def startBiasDep(self,event):
        if(self.running):
            print("Already running",self.running)
            return
        
        disabled_options = self.functionWidget.options.copy()
        disabled_options.remove("Bias Dependent")
        self.functionWidget.disabled_options = disabled_options
        
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