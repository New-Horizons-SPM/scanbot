import pytest
from scanbot.server import app_
from unittest.mock import patch
import numpy as np
import threading
import time
import cv2
import os

@pytest.fixture
def client(tmp_path):
    app = app_(test=True,tmp_path=tmp_path)
    with app.test_client() as client:
        yield client

def test_homepage(client):
    response = client.get('/')
    homepage_found = response.data.decode().startswith('<!doctype html>')
    assert homepage_found == True

def test_has_config(client, tmp_path):
    fake_file = tmp_path / "scanbot_config.ini"
    fake_file.write_text("test")
    
    response = client.get('/has_config')
    json_data = response.json
    file_found = json_data['status']

    assert file_found == True

def test_has_no_config(client):
    response = client.get('/has_config')
    json_data = response.json
    file_found = json_data['status']

    assert file_found == False

def test_test_connection(client):
    response = client.get('/test_connection')
    assert response.status_code == 200          # Hard to test anything else here since nanonis needs to be open

def test_reset_init(client):
    response = client.get('/reset_init')
    json_data = response.json
    success = json_data['status']
    
    assert response.status_code == 200
    assert success == "success"

# %%
# Test demo initialisation
# 
# First test that /is_auto_init returns False (since initialisation has not been run yet)
def test_is_not_auto_init(client):
    response     = client.get('/is_auto_init')
    json_data    = response.json
    is_auto_init = json_data['status']
    
    assert response.status_code == 200
    assert is_auto_init == False

# Next, go through the demo initialisation then retest to see of is_auto_init == True
def wait_for_mouse_callback(mock_setMouseCallback):
    i = 0
    timeout = 5
    while mock_setMouseCallback.call_args is None:
        time.sleep(0.5)
        i += 0.5
        if(i > timeout):
            return -1
    return mock_setMouseCallback.call_args[0][1]

def simulate_autoInit(mock_setMouseCallback, mock_waitKey):
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
