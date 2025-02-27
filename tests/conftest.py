import os
import sys
import pytest
from app import create_app, db
from app.config import Config

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestConfig(Config):
    """Test configuration that uses an in-memory SQLite database"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    # Use a temporary directory for file uploads during tests
    UPLOAD_FOLDER = os.path.abspath('test_uploads')


@pytest.fixture(scope='function')
def app():
    """Create and configure a Flask app for testing"""
    app = create_app(TestConfig)
    
    # Create a test client
    with app.app_context():
        # Create all tables in the test database
        db.create_all()
        
        # Create test uploads directory if it doesn't exist
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        
        yield app
        
        # Clean up after the test
        db.session.remove()
        db.drop_all()
        
        # Remove test upload files
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            import shutil
            shutil.rmtree(app.config['UPLOAD_FOLDER'])


@pytest.fixture(scope='function')
def client(app):
    """A test client for the app"""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """A test CLI runner for the app"""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def _db(app):
    """Provide the database object as a fixture"""
    return db