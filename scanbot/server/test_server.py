import pytest
from scanbot.server import app_

@pytest.fixture
def client(tmp_path):
    app = app_(test=True,tmp_path=tmp_path)
    app.config.update({
        "TESTING": True,
    })
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
    assert response.status_code == 200
    
