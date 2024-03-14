from flask import Flask, request, send_from_directory
from flask_cors import CORS
from scanbot.server.scanbot_interface import scanbot_interface
from scanbot.server.scanbot_config import scanbot_config
from scanbot.server import global_
import numpy as np
import os
import shutil
from pathlib import Path
from PIL import Image
import base64
import sys
import pickle
import webbrowser
from threading import Timer

# pyinstaller --onefile --icon=..\App\public\favicon.ico --add-data "..\App\build;static" --name scanbot_v4.1 server.py
app = Flask(__name__, static_url_path='')

# Determine if we're running in a PyInstaller bundle and adjust paths
if getattr(sys, 'frozen', False):
    # If the app is run from a PyInstaller bundle
    app.static_folder = os.path.join(sys._MEIPASS, "static")
    module_dir = "./"
else:
    # Otherwise, use the normal base directory
    app.static_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'App', 'build'))
    module_dir = str(os.path.dirname(os.path.abspath(__file__))).replace('\\','/')
    if(not module_dir.endswith('/')): module_dir += '/'

scanbot = scanbot_interface(run_mode='react',module_dir=module_dir)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

@app.route('/has_config')
def has_config():
    hasConfig = os.path.isfile(module_dir + "scanbot_config.ini")
    return {"status": hasConfig}, 200

@app.route('/test_connection')
def test_connection():
    status = scanbot.testConnection()
    return {"status": status}, 200

@app.route('/reset_init')
def reset_init():
    scanbot.scanbot.autoInitSet = False
    return {"status": "success"}, 200

@app.route('/demo_init')
def demo_init():
    scanbot.autoInit(user_args=['-demo=1','-reactInit=1'])
    return {"status": "success"}, 200

@app.route('/is_auto_init')
def is_auto_init():
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

    Path(module_dir + 'autoinit').mkdir(parents=True, exist_ok=True)

    header, encoded = initialFrame.split(",", 1)
    binary_data = base64.b64decode(encoded)
    file_path = module_dir + 'autoinit/initialFrame.png'
    with open(file_path, 'wb') as file:
        file.write(binary_data)
    
    initialFrame = Image.open(file_path)
    if initialFrame.mode == 'RGBA':
        initialFrame = initialFrame.convert('RGB')
        
    header, encoded = tipInFrame.split(",", 1)
    binary_data = base64.b64decode(encoded)
    file_path = module_dir + 'autoinit/tipInFrame.png'
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

    pickle.dump(pk,open(module_dir + 'autoinit/autoinit.pk','wb'))

    userArgs = ['-reactInit=1']
    error = scanbot.autoInit(user_args=userArgs)
    if(error):
        return {"status": "Error: " + error}, 200
        
    return {"status": "success"}, 200

@app.route ('/get_initialised_frame')
def get_initialised_frame():
    autoinit_dir = getDir(module_dir + 'autoinit')
    return send_from_directory(autoinit_dir, 'initialisation.png', as_attachment=True)

@app.route('/run_go_to_target', methods=['POST'])
def run_go_to_target():
    data = request.json

    target   = data['target']
    userArgs = data['userArgs']
    if(target == 'sample'):
        error = scanbot.moveTipToSample(user_args=userArgs)

    if(target == 'metal'):
        error = scanbot.moveTipToClean(user_args=userArgs)

    if(error):
        print("ERROR:",error)
        return {"status": error}, 503
    
    try:
        shutil.rmtree('./temp')
    except:
        pass
    
    return {"status": "success"}, 200

@app.route('/scanbot_config')
def get_config():
    sbConfig = scanbot_config(module_dir=module_dir)
    return {'config': sbConfig.config}

@app.route('/save_config', methods=['POST'])
def save_config():
    config = request.json['config']

    with open(module_dir + 'scanbot_config.ini', 'w') as file:
        for line in config:
            if(not line['value'][scanbot_config.value]): continue
            file.write(line['parameter'] + '=' + line['value'][scanbot_config.value] + '\n')

    scanbot.restart(run_mode='react',module_dir=module_dir)

    # Maybe have something like scanbot.errors where errors can be stored with varying priority levels (i.e. 1=code failure, 2=warning, etc.)

    return {"status": "success"}, 200

@app.route('/run_survey', methods=['POST'])
def run_survey():
    userArgs = request.json['userArgs']
    error = scanbot.survey2(user_args=userArgs)
    if(error):
        return {"status": error}, 503

    try:
        shutil.rmtree(module_dir + 'temp')
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
        shutil.rmtree(module_dir + 'temp')
    except:
        pass
    return {"status": "success"}, 200

@app.route('/run_autotipshape', methods=['POST'])
def run_autotipshape():
    userArgs = request.json['userArgs']
    error = scanbot.autoTipShape(user_args=userArgs)
    if(error):
        return {"status": error}, 503
    try:
        shutil.rmtree(module_dir + 'temp')
    except:
        pass
    return {"status": "success"}, 200

@app.route('/get_imprint_score')
def get_imprint_score():
    files = sorted([file for file in Path(module_dir + 'temp').iterdir() if file.suffix == '.png'], key=os.path.getmtime)
    latestFile = str(files[-1].name)
    size = latestFile.split("size--")[1].split("_")[0]
    symm = latestFile.split("symm--")[1].split(".png")[0]
    running = global_.running.is_set()
    return {"size": size,"sym": symm, "running": running}, 200
    

@app.route('/image_updates', methods=['POST'])
def check_survey_updates():
    timestamp = request.json['timestamp']
    try:
        files = sorted([file for file in Path(module_dir + 'temp').iterdir() if file.suffix == '.png'], key=os.path.getmtime)
        latestFile = str(files[-1].name)
        try:
            latestTimestamp = float(latestFile.split('_')[0])*1000
            if(latestTimestamp > timestamp):
                temp_dir = getDir(module_dir + 'temp')
                return send_from_directory(temp_dir, str(files[-1].name), as_attachment=True)
        except Exception as e:
            print(e)
        
        return {"status": 'not found'}, 404
    except:
        pass

    return {"status": 'not found'}, 404

@app.route('/get_gif')
def get_gif():
    frames = []
    files = sorted([file for file in Path(module_dir + 'temp').iterdir() if file.suffix == '.png'], key=os.path.getmtime)
    for file in files:
        if(str(file.name).endswith('.png')):
            im = Image.open(file)
            frames.append(im.copy())
            
    if(frames):
        frames[0].save(module_dir + 'temp/GIF.gif', format="GIF", append_images=frames, save_all=True, duration=500, loop=0)
        temp_dir = getDir(module_dir + 'temp')
        return send_from_directory(temp_dir, 'GIF.gif', as_attachment=True)
            
    return {"status": 'not found'}, 404

@app.route('/get_state')
def get_running():
    running = global_.running.is_set()
    action  = scanbot.getAction()
    return {"running": running, "action": action['action']}, 200

@app.route('/remove_temp')
def remove_temp():
    try:
        shutil.rmtree(module_dir + 'temp')
    except:
        pass
    return {"status": "success"}, 200

@app.route('/stop')
def stop():
    scanbot.stop(user_args=[])
    return {"status": "success"}, 200

def getDir(path):
    if getattr(sys, 'frozen', False):
        # If running as a PyInstaller executable, the base directory is the directory of the executable
        base_dir = os.path.dirname(sys.executable)
    else:
        # If running directly with Python, the base directory can be the current working directory
        base_dir = module_dir
    
    return os.path.join(base_dir, path)

def open_browser():
      webbrowser.open_new('http://127.0.0.1:5000/')

# Running app
if __name__ == '__main__':
    Timer(1, open_browser).start()
    app.run(debug=False)

def app_():
    Timer(1, open_browser).start()
    app.run(debug=False)
