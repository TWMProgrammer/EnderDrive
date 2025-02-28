import pytest

def test_favicon_ico(client):
    """Test that the favicon.ico route returns the correct file"""
    response = client.get('/favicon.ico')
    assert response.status_code == 200
    assert response.mimetype == 'image/vnd.microsoft.icon'

def test_favicon_png(client):
    """Test that the favicon.png route returns the correct file"""
    response = client.get('/favicon.png')
    assert response.status_code == 200
    assert response.mimetype == 'image/png'