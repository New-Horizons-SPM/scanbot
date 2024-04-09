import pytest
from scanbot.server import app_
from unittest.mock import patch
import numpy as np
import threading
import time
import cv2
import os
from PIL import Image
import base64
import io

@pytest.fixture
def client(tmp_path):
    app = app_(test=True,tmp_path=tmp_path)
    with app.test_client() as client:
        yield client

def test_homepage(client):
    """
    Test that the server is able to provide the homepage
    """
    response = client.get('/')
    homepage_found = response.data.decode().startswith('<!doctype html>')
    assert homepage_found == True

def test_has_config(client, tmp_path):
    """
    Test that the config file can be found
    """
    fake_file = tmp_path / "scanbot_config.ini"
    fake_file.write_text("test")
    
    response = client.get('/has_config')
    json_data = response.json
    file_found = json_data['status']

    assert file_found == True

def test_has_no_config(client):
    """
    Test that the config file can't be found
    """
    response = client.get('/has_config')
    json_data = response.json
    file_found = json_data['status']

    assert file_found == False

def test_test_connection(client):
    """
    Test that the connection to nanonis can be verified
    """
    with patch('scanbot.server.scanbot.nanonisTCP') as mock_nanonisTCP, \
         patch('scanbot.server.scanbot.Bias') as mock_Bias:
         
        mock_nanonisTCP.return_value.close_connection.return_value = None

        mock_Bias.return_value.Get.return_value = 0 # Scanbot tests the connection by attempting to read the bias value in nanonis. Give it something

        response = client.get('/test_connection')
        assert response.status_code == 200
        
        json_data = response.json
        connected = json_data['status']
        assert connected

def test_reset_init(client):
    """
    Test that the tip initiliasation can be reset
    """
    response = client.get('/reset_init')
    json_data = response.json
    success = json_data['status']
    
    assert response.status_code == 200
    assert success == "success"

# Test initialisation

def test_is_not_auto_init(client):
    """
    Test to see if initialisation is not complete
    """
    response     = client.get('/is_auto_init')
    json_data    = response.json
    is_auto_init = json_data['status']
    
    assert response.status_code == 200
    assert is_auto_init == False

# Next, go through the demo initialisation then retest to see of is_auto_init == True
def wait_for_mouse_callback(mock_setMouseCallback):
    """
    This function grabs the mouse_callback function once it has been set by scanbot
    It waits a maximum of 5s (should be very quick) before timing out.
    """
    i = 0
    timeout = 5
    while mock_setMouseCallback.call_args is None:
        time.sleep(0.5)
        i += 0.5
        if(i > timeout):
            return -1
    return mock_setMouseCallback.call_args[0][1]

def simulate_autoInit(mock_setMouseCallback, mock_waitKey):
    """
    This function simulates the initialisation for automatic tip shaping.
    It simulates clicks for the tip, sample, and metal locations.
    """
    callback_fn = wait_for_mouse_callback(mock_setMouseCallback)
    if(callback_fn == -1):
        raise TimeoutError("Timeout while waiting for mouse callback.")
    
    # Initial frame and tip in frame clicks
    time.sleep(1); callback_fn(cv2.EVENT_LBUTTONUP, 100, 100, None, None)
    time.sleep(1); callback_fn(cv2.EVENT_LBUTTONUP, 100, 100, None, None)

    # Clicks for the initialisation of the tip, sample, and metal locations
    time.sleep(1); callback_fn(cv2.EVENT_LBUTTONUP, 100, 100, None, None)
    time.sleep(1); callback_fn(cv2.EVENT_LBUTTONUP, 100, 110, None, None)
    time.sleep(1); callback_fn(cv2.EVENT_LBUTTONUP, 100, 120, None, None)

    # Escape the 30s wait period
    time.sleep(1); mock_waitKey.return_value = 113  # ASCII value for 'q'

def test_demo_init(client, tmp_path):
    """
    Tests that the intialisation procedure can run and completes as expected
    """
    with patch('cv2.waitKey') as mock_waitKey, patch('cv2.VideoCapture') as mock_videoCapture, patch('cv2.imshow') as mock_imshow, patch('cv2.namedWindow'), patch('cv2.destroyAllWindows'), patch('cv2.setMouseCallback') as mock_setMouseCallback:
        mock_cap = mock_videoCapture.return_value

        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cap.read.return_value = (True, dummy_frame)
        mock_imshow.return_value  = None
        mock_waitKey.return_value = 0
        
        try:
            callback_thread = threading.Thread(target=simulate_autoInit, args=(mock_setMouseCallback, mock_waitKey))
            callback_thread.start()

            response = client.get('/demo_init')
            
            callback_thread.join()
        except TimeoutError as e:
            print(str(e))
            assert False, "Timed out while waiting for auto initialisation."

        json_data = response.json
        success = json_data['status']

        assert os.path.isfile(tmp_path / 'autoInit/initialisation.png')
        assert success == "success"

        # Next check that the initialisation flag has been set
        response     = client.get('/is_auto_init')
        json_data    = response.json
        is_auto_init = json_data['status']
        
        assert response.status_code == 200
        assert is_auto_init == True

        """
        Tests the move tip to sample function
        """
        data = {"target" : "sample",
                "userArgs": []}

        with patch('scanbot.server.scanbot.scanbot.moveTip') as mock_moveTip:
            mock_moveTip.return_value = "Target Hit"
            
            response = client.post('/run_go_to_target', json=data)

        assert response.status_code == 200
        
def test_auto_init_frames(client,tmp_path):
    """
    Test auto-tip initialisation in live mode
    """
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    pil_image = Image.fromarray(dummy_frame, 'RGB')
    
    buffered = io.BytesIO()
    pil_image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    initialFrame = f"data:image/png;base64,{img_str}"
    tipInFrame   = f"data:image/png;base64,{img_str}"

    data = {'initialFrame': initialFrame,
            'tipInFrame':   tipInFrame,
            'tipLocation':  [0,0],
            'metalLocation':[0,0],
            'sampleLocation':[0,0]}
    
    response = client.post('/auto_init_frames', json=data)

    has_initialFrame = os.path.isfile(tmp_path / "autoinit/initialFrame.png")
    has_tipInFrame   = os.path.isfile(tmp_path / "autoinit/tipInFrame.png")
    has_pk           = os.path.isfile(tmp_path / "autoinit/autoinit.pk")

    assert has_initialFrame
    assert has_tipInFrame
    assert has_pk

    # Next check that the initialisation went through
    response     = client.get('/is_auto_init')
    json_data    = response.json
    is_auto_init = json_data['status']
    
    assert response.status_code == 200
    assert is_auto_init == True
    
    response = client.get('/get_initialised_frame')
    
    content_disposition = response.headers.get('Content-Disposition')
    assert 'filename=' in content_disposition

    filename = content_disposition.split('filename=')[1].strip('"')
    assert filename == 'initialisation.png'
    
    assert response.status_code == 200
    
    response     = client.get('/is_auto_init')
    json_data    = response.json
    is_auto_init = json_data['status']
    
    assert response.status_code == 200
    assert is_auto_init == True

def test_get_config(client):
    """
    Test config is returned
    """
    response   = client.get('/scanbot_config')
    json_data  = response.json
    has_config = json_data['config']

    assert response.status_code == 200
    assert has_config

def test_save_config(client,tmp_path):
    """
    Test config.ini can be saved
    """
    config = [{"parameter": "ip",
               "value": ['IP Address', 'IP address of the pc controlling nanonis', 'tcp', '127.0.0.1']}]
    data = {"config":config}
    response = client.post('/save_config', json=data)
    assert response.status_code == 200
    
    config_saved = os.path.isfile(tmp_path / "scanbot_config.ini")
    assert config_saved

def test_run_survey(client,tmp_path):
    """
    Test surveys can run and complete
    """
    with patch('scanbot.server.scanbot.nanonisTCP') as mock_nanonisTCP, \
         patch('scanbot.server.scanbot.Scan') as mock_Scan, \
         patch('scanbot.server.scanbot.Piezo') as mock_Piezo:
        
        dummy_frame = np.zeros((128,128))

        mock_nanonisTCP.return_value.close_connection.return_value = None

        mock_Scan.return_value.FrameGet.return_value      = [0,0,20e-9,20e-9,0]
        mock_Scan.return_value.PropsGet.return_value      = ["N/A","N/A","N/A","series name","N/A"]
        mock_Scan.return_value.BufferGet.return_value     = ["N/A","N/A",128,128]
        mock_Scan.return_value.WaitEndOfScan.return_value = [False, "N/A", "file_path"]
        mock_Scan.return_value.FrameDataGrab.return_value = ["N/A", dummy_frame, "N/A"]

        mock_Piezo.return_value.RangeGet.return_value = [1.6e-6,1.6e-6,"N/A"]
        
        data = {"userArgs":["-n=1","-st=0.1","-nx=1","-ny=1","-xy=10","-dx=20"]}
        response = client.post('/run_survey', json=data)
        time.sleep(3) # Need to wait for the survey thread to finish up

        assert response.status_code == 200
    
    data = {"timestamp":0}
    response = client.post('/image_updates', json=data)
    assert response.status_code == 200

    content_disposition = response.headers.get('Content-Disposition')
    assert 'filename=' in content_disposition

    filename = content_disposition.split('filename=')[1].strip('"')
    assert filename.endswith('.png')

def test_run_bias_dep(client):
    """
    Test bias dependent imaging can run and complete
    """
    with patch('scanbot.server.scanbot.nanonisTCP') as mock_nanonisTCP, \
         patch('scanbot.server.scanbot.Scan') as mock_Scan, \
         patch('scanbot.server.scanbot.Bias') as mock_Bias, \
         patch('scanbot.server.scanbot.ZController'):
        
        dummy_frame = np.zeros((128,128))
        dummy_frame[64,64] = 1

        mock_nanonisTCP.return_value.close_connection.return_value = None

        mock_Scan.return_value.FrameGet.return_value      = [0,0,20e-9,20e-9,0]
        mock_Scan.return_value.PropsGet.return_value      = ["N/A","N/A","N/A","series name","N/A"]
        mock_Scan.return_value.BufferGet.return_value     = ["N/A","N/A",128,128]
        mock_Scan.return_value.WaitEndOfScan.return_value = [False, "N/A", "file_path"]
        mock_Scan.return_value.FrameDataGrab.return_value = ["N/A", dummy_frame, "N/A"]
        mock_Scan.return_value.SpeedGet.return_value      = ["N/A","N/A",0.3,"N/A","N/A","N/A"]

        mock_Bias.return_value.Get.return_value = 0

        data = {"userArgs":["-n=1","-px=1"]}
        response = client.post('/run_biasdep', json=data)

        time.sleep(4)
        assert response.status_code == 200

    data = {"timestamp":0}
    response = client.post('/image_updates', json=data)
    assert response.status_code == 200

    content_disposition = response.headers.get('Content-Disposition')
    assert 'filename=' in content_disposition

    filename = content_disposition.split('filename=')[1].strip('"')
    assert filename.endswith('.png')
    
    response = client.get('/get_gif')
    assert response.status_code == 200

    content_disposition = response.headers.get('Content-Disposition')
    assert 'filename=' in content_disposition

    filename = content_disposition.split('filename=')[1].strip('"')
    assert filename.endswith('.gif')
