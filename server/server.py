from flask import Flask, request, send_from_directory, jsonify
from scanbot_interface import scanbot_interface
from scanbot_config import scanbot_config
import numpy as np
import os
import shutil
from pathlib import Path
from PIL import Image
import base64
import time
import pickle
app = Flask(__name__)

@app.route('/reset_init')
def reset_init():
    scanbot.scanbot.autoInitSet = False
    return {"status": "success"}, 200

@app.route('/is_auto_init')
def is_auto_init():
    print(scanbot.scanbot.autoInitSet)
    return {"status": scanbot.scanbot.autoInitSet}, 200

@app.route('/check_hook', methods=['POST'])
def check_hook():
    data = request.json
    hookName = data['hook']
    try:
        if(hookName == 'hk_survey'):
            import hk_survey;
            return {"status": True}, 200
        if(hookName == 'hk_classifier'): import hk_classifier; return {"status": True}, 200
    except:
        pass
    
    return {"status": False}, 200
    
@app.route('/auto_init_frames', methods=['POST'])
def save_frame():
    data = request.json
    initialFrame = data['initialFrame']
    tipInFrame   = data['tipInFrame']

    Path('./autoinit').mkdir(parents=True, exist_ok=True)

    header, encoded = initialFrame.split(",", 1)
    binary_data = base64.b64decode(encoded)
    file_path = './autoinit/initialFrame.png'
    with open(file_path, 'wb') as file:
        file.write(binary_data)
    
    initialFrame = Image.open(file_path)
    if initialFrame.mode == 'RGBA':
        initialFrame = initialFrame.convert('RGB')
        
    header, encoded = tipInFrame.split(",", 1)
    binary_data = base64.b64decode(encoded)
    file_path = './autoinit/tipInFrame.png'
    with open(file_path, 'wb') as file:
        file.write(binary_data)
    
    tipInFrame = Image.open(file_path)
    if tipInFrame.mode == 'RGBA':
        tipInFrame = tipInFrame.convert('RGB')

    pk = {
        'tipLocation'     : np.array(data['tipLocation']),
        'metalLocation'   : np.array(data['metalLocation']),
        'sampleLocation'  : np.array(data['sampleLocation']),
        'initialFrame'    : np.array(initialFrame),
        'tipInFrame'      : np.array(tipInFrame)
    }

    pickle.dump(pk,open('./autoinit/autoinit.pk','wb'))

    userArgs = ['-reactInit=1']
    error = scanbot.autoInit(user_args=userArgs)
    if(error):
        return {"status": "Error: " + error}, 200
        
    return {"status": "success"}, 200

@app.route ('/get_initialised_frame')
def get_initialised_frame():
    return send_from_directory('./autoinit', 'initialisation.png', as_attachment=True)

@app.route('/scanbot_config')
def get_config():
    sbConfig = scanbot_config()
    return {'config': sbConfig.config}

@app.route('/save_config', methods=['POST'])
def save_config():
    config = request.json['config']

    with open('scanbot_config.ini', 'w') as file:
        for line in config:
            if(not line['value'][scanbot_config.value]): continue
            file.write(line['parameter'] + '=' + line['value'][scanbot_config.value] + '\n')

    scanbot.restart(run_mode='react')

    # Maybe have something like scanbot.errors where errors can be stored with varying priority levels (i.e. 1=code failure, 2=warning, etc.)

    return {"status": "success"}, 200

@app.route('/run_survey', methods=['POST'])
def run_survey():
    userArgs = request.json['userArgs']
    error = scanbot.survey2(user_args=userArgs)
    if(error):
        return {"status": error}, 503

    try:
        shutil.rmtree('./temp')
    except:
        pass
    return {"status": "success"}, 200

@app.route('/run_biasdep', methods=['POST'])
def run_biasdep():
    userArgs = request.json['userArgs']
    error = scanbot.biasDep(user_args=userArgs)
    if(error):
        return {"status": error}, 503

    try:
        shutil.rmtree('./temp')
    except:
        pass
    return {"status": "success"}, 200

@app.route('/image_updates', methods=['POST'])
def check_survey_updates():
    timestamp = request.json['timestamp']
    try:
        files = sorted(Path('./temp').iterdir(), key=os.path.getmtime)
        latestFile = str(files[-1].name)

        try:
            latestTimestamp = float(latestFile.split('_')[0])*1000
            if(latestTimestamp > timestamp):
                return send_from_directory('./temp', str(files[-1].name), as_attachment=True)
        except:
            pass
        
        return {"status": 'not found'}, 404
    except:
        pass

    return {"status": 'not found'}, 404

@app.route('/get_gif')
def get_gif():
    frames = []
    files = sorted(Path('./temp').iterdir(), key=os.path.getmtime)
    for file in files:
        if(str(file.name).endswith('.png')):
            im = Image.open(file)
            frames.append(im.copy())
            
    if(frames):
        frames[0].save('./temp/GIF.gif', format="GIF", append_images=frames, save_all=True, duration=500, loop=0)
        return send_from_directory('./temp', 'GIF.gif', as_attachment=True)
            
    return {"status": 'not found'}, 404

@app.route('/stop')
def stop():
    scanbot.stop(user_args=[])
    return {"status": "success"}, 200

# Running app
if __name__ == '__main__':
    scanbot = scanbot_interface(run_mode='react')
    app.run(debug=True)
