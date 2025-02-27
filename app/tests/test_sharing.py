import pytest
import re
from app.models.user import User
from app.models.file import File
from app.models.shared_link import SharedLink
from app.models.folder import Folder
from io import BytesIO


@pytest.fixture
def test_users(app):
    """Create test users for sharing operations"""
    with app.app_context():
        from werkzeug.security import generate_password_hash
        
        # Get or create user role
        from app.models.role import Role
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular User')
            db = app.extensions['sqlalchemy'].db
            db.session.add(user_role)
            db.session.commit()
        
        # Create owner user
        password = generate_password_hash('Password123!', method='pbkdf2')
        owner = User(username='owner', password=password, role_id=user_role.id)
        
        # Create recipient user
        recipient = User(username='recipient', password=password, role_id=user_role.id)
        
        db = app.extensions['sqlalchemy'].db
        db.session.add(owner)
        db.session.add(recipient)
        db.session.commit()
        
        # Store user IDs instead of objects to avoid DetachedInstanceError
        owner_id = owner.id
        recipient_id = recipient.id
        
        return {'owner_id': owner_id, 'recipient_id': recipient_id}


@pytest.fixture
def owner_client(client, test_users):
    """A test client authenticated as the owner user"""
    client.post('/login', data={
        'username': 'owner',
        'password': 'Password123!'
    })
    return client


@pytest.fixture
def recipient_client(app, test_users):
    """A test client authenticated as the recipient user"""
    test_client = app.test_client()
    test_client.post('/login', data={
        'username': 'recipient',
        'password': 'Password123!'
    })
    return test_client


@pytest.fixture
def test_file(app, test_users):
    """Create a test file for the owner user"""
    with app.app_context():
        # Create a file for the owner
        file = File(
            name='shared_test.txt',
            size=100,
            owner_id=test_users['owner_id']
        )
        
        # Save file to database
        db = app.extensions['sqlalchemy'].db
        db.session.add(file)
        db.session.commit()
        
        # Create the actual file in the filesystem
        import os
        # Get the owner's username
        owner = User.query.get(test_users['owner_id'])
        file_dir = os.path.join(app.config['UPLOAD_FOLDER'], owner.username)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
            
        file_path = os.path.join(file_dir, file.name)
        with open(file_path, 'wb') as f:
            f.write(b'This is a test file for sharing')
            
        return file


def test_create_share_link(owner_client, app, test_users, test_file):
    """Test creating a share link for a file"""
    response = owner_client.post(f'/share/file/{test_file.id}', data={
        'name': 'Test Share',
        'description': 'Test share description',
        'expires_in': 7
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    # Verify share link was created in database
    with app.app_context():
        share_link = SharedLink.query.filter_by(file_id=test_file.id).first()
        assert share_link is not None
        assert share_link.token is not None


def test_access_shared_file(client, app, test_users, test_file):
    """Test accessing a shared file with the share link"""
    # First create a share link
    with app.app_context():
        share_link = SharedLink(
            file_id=test_file.id,
            created_by=test_users['owner_id'],
            name='Test Share'
        )
        db = app.extensions['sqlalchemy'].db
        db.session.add(share_link)
        db.session.commit()
        
        # Access the shared file with the token
        response = client.get(f'/shared/{share_link.token}')
        
        assert response.status_code == 200
        assert b'shared_test.txt' in response.data


def test_download_shared_file(client, app, test_users, test_file):
    """Test downloading a shared file"""
    # Create a share link
    with app.app_context():
        share_link = SharedLink(
            file_id=test_file.id,
            created_by=test_users['owner_id'],
            name='Test Share'
        )
        db = app.extensions['sqlalchemy'].db
        db.session.add(share_link)
        db.session.commit()
        
        # Access the shared file first to establish the session
        client.get(f'/shared/{share_link.token}')
        
        # Then download the shared file
        response = client.get(f'/shared/{share_link.token}/download')
        
        assert response.status_code == 200
        assert response.data == b'This is a test file for sharing'


def test_share_folder(owner_client, app, test_users):
    """Test sharing a folder"""
    # First create a folder
    with app.app_context():
        folder = Folder(
            name='Shared Folder',
            owner_id=test_users['owner_id']
        )
        db = app.extensions['sqlalchemy'].db
        db.session.add(folder)
        db.session.commit()
        
        # Create the actual folder in the filesystem
        import os
        owner = User.query.get(test_users['owner_id'])
        folder_dir = os.path.join(app.config['UPLOAD_FOLDER'], owner.username, 'Shared Folder')
        if not os.path.exists(folder_dir):
            os.makedirs(folder_dir)
        
        # Create a share link for the folder with required form data
        response = owner_client.post(f'/share/folder/{folder.id}', data={
            'name': 'Shared Folder Link',
            'description': 'Test sharing a folder',
            'expires_in': 7
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify share link was created
        share_link = SharedLink.query.filter_by(folder_id=folder.id).first()
        assert share_link is not None
        
        # Test accessing the shared folder
        response = owner_client.get(f'/shared/{share_link.token}')
        assert response.status_code == 200
        assert b'Shared Folder' in response.data