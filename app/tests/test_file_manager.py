import os
import pytest
from io import BytesIO
from app.models.file import File
from app.models.folder import Folder
from app.models.user import User
from app.models.role import Role


@pytest.fixture
def test_user(app):
    """Create a test user for file operations"""
    with app.app_context():
        from werkzeug.security import generate_password_hash
        password = generate_password_hash('Password123!', method='pbkdf2')
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular User')
            db = app.extensions['sqlalchemy']
            db.session.add(user_role)
            db.session.commit()
        user = User(username='fileuser', password=password, role_id=user_role.id, storage_quota=1024*1024*10)  # 10MB quota
        db = app.extensions['sqlalchemy']
        db.session.add(user)
        db.session.commit()
        
        # Create user folder
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'fileuser')
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)
        
        # Store user ID instead of object to avoid DetachedInstanceError
        user_id = user.id
        return user_id


@pytest.fixture
def authenticated_client(client, test_user):
    """A test client that is authenticated as the test user"""
    client.post('/login', data={
        'username': 'fileuser',
        'password': 'Password123!'
    })
    return client


def test_folder_creation_filesystem(authenticated_client, app, test_user):
    """Test creating a new folder in the filesystem"""
    with app.app_context():
        db = app.extensions['sqlalchemy']
        user = db.session.get(User, test_user)
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], user.username)
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)
    
    response = authenticated_client.post('/browse/upload/', data={
        'folder_name': 'Test Folder'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    with app.app_context():
        db = app.extensions['sqlalchemy']
        user = db.session.get(User, test_user)
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], user.username, 'Test Folder')
        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        
        assert os.path.exists(folder_path)


def test_folder_creation_database(authenticated_client, app, test_user):
    """Test creating a new folder in the database"""
    response = authenticated_client.post('/browse/upload/', data={
        'folder_name': 'Database Test Folder'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    # Verify folder was created in database
    with app.app_context():
        db = app.extensions['sqlalchemy']
        user = db.session.get(User, test_user)
        # The controller uses secure_filename which sanitizes the folder name
        folder = Folder.query.filter_by(name='Database_Test_Folder', owner_id=test_user).first()
        
        assert folder is not None
        assert folder.owner_id == test_user
        assert folder.name == 'Database_Test_Folder'


def test_successful_file_upload(authenticated_client, app, test_user):
    """Test successful file upload and verify file creation"""
    data = {
        'file': (BytesIO(b'test file content'), 'test.txt')
    }
    
    response = authenticated_client.post(
        '/browse/upload/',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True
    )
    
    assert response.status_code == 200
    
    # Verify file was created in database and filesystem
    with app.app_context():
        file = File.query.filter_by(name='test.txt', owner_id=test_user).first()
        assert file is not None
        
        db = app.extensions['sqlalchemy']
        user = db.session.get(User, test_user)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], user.username, file.name)
        assert os.path.exists(file_path)

def test_upload_invalid_filename(authenticated_client, app, test_user):
    """Test uploading file with invalid filename containing special characters"""
    data = {
        'file': (BytesIO(b'special chars'), 'test@#$%.txt')
    }
    response = authenticated_client.post(
        '/browse/upload/',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b'Invalid filename' in response.data

def test_upload_empty_file(authenticated_client, app, test_user):
    """Test uploading an empty file"""
    data = {
        'file': (BytesIO(b''), 'empty.txt')
    }
    response = authenticated_client.post(
        '/browse/upload/',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b'File cannot be empty' in response.data

def test_upload_exceeding_quota(authenticated_client, app, test_user):
    """Test uploading file that exceeds user's storage quota"""
    large_content = b'x' * (10 * 1024 * 1024 + 1)  # 10MB + 1 byte
    data = {
        'file': (BytesIO(large_content), 'large.txt')
    }
    response = authenticated_client.post(
        '/browse/upload/',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b'Storage quota exceeded' in response.data

def test_file_download(authenticated_client, app, test_user):
    """Test downloading a file"""
    # First upload a file
    data = {
        'file': (BytesIO(b'test download content'), 'download.txt')
    }
    
    authenticated_client.post(
        '/browse/upload/',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True
    )
    
    # Get the file ID
    with app.app_context():
        file = File.query.filter_by(name='download.txt', owner_id=test_user).first()
        assert file is not None
        
        # Test downloading the file
        response = authenticated_client.get(f'/browse/download/download.txt')
        assert response.status_code == 200
        assert response.data == b'test download content'

def test_file_deletion(authenticated_client, app, test_user):
    """Test deleting a file"""
    # First upload a file
    data = {
        'file': (BytesIO(b'delete me'), 'delete.txt')
    }
    
    authenticated_client.post(
        '/browse/upload/',
        data=data,
        content_type='multipart/form-data'
    )
    
    # Get the file ID
    with app.app_context():
        file = File.query.filter_by(name='delete.txt', owner_id=test_user).first()
        assert file is not None
        file_id = file.id
        
        # Test deleting the file
        response = authenticated_client.post(
            f'/browse/delete/delete.txt',
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Verify file was deleted from database
        file = File.query.filter_by(id=file_id).first()
        assert file is None