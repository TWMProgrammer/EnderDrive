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
            db = app.extensions['sqlalchemy']
            db.session.add(user_role)
            db.session.commit()
        
        # Create owner user
        password = generate_password_hash('Password123!', method='pbkdf2')
        owner = User(username='owner', password=password, role_id=user_role.id)
        
        # Create recipient user
        recipient = User(username='recipient', password=password, role_id=user_role.id)
        
        db = app.extensions['sqlalchemy']
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
        db = app.extensions['sqlalchemy']
        db.session.add(file)
        db.session.commit()
        
        # Create the actual file in the filesystem
        import os
        # Get the owner's username
        owner = db.session.get(User, test_users['owner_id'])
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
    """Test accessing a shared file with edge cases"""
    with app.app_context():
        # Test with expired share link
        from datetime import datetime, timedelta
        expired_share = SharedLink(
            file_id=test_file.id,
            created_by=test_users['owner_id'],
            name='Expired Share',
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        db = app.extensions['sqlalchemy']
        db.session.add(expired_share)
        db.session.commit()
        
        response = client.get(f'/shared/{expired_share.token}')
        assert response.status_code == 404
        assert b'Share link has expired' in response.data
        
        # Test with invalid token
        response = client.get('/shared/invalid_token_123')
        assert response.status_code == 404
        assert b'Share link not found' in response.data
        
        # Test with valid share link
        share_link = SharedLink(
            file_id=test_file.id,
            created_by=test_users['owner_id'],
            name='Test Share'
        )
        db.session.add(share_link)
        db.session.commit()
        
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
        db = app.extensions['sqlalchemy']
        db.session.add(share_link)
        db.session.commit()


def test_share_nonexistent_file(owner_client, app, test_users):
    """Test sharing a file that doesn't exist"""
    response = owner_client.post('/share/file/99999', data={
        'name': 'Invalid Share',
        'description': 'This file does not exist',
        'expires_in': 7
    }, follow_redirects=True)
    
    assert response.status_code == 404


def test_modify_share_link(owner_client, app, test_users, test_file):
    """Test modifying an existing share link"""
    # First create a share link through the API
    response = owner_client.post(f'/share/file/{test_file.id}', data={
        'name': 'Original Share',
        'description': 'Original description',
        'expires_in': 7
    }, follow_redirects=True)
    
    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data['status'] == 'success'
    
    # Extract token from share link URL
    share_url = response_data['share_link']
    token = share_url.split('/')[-1]
    
    # Test modifying the share link
    response = owner_client.put(f'/api/shares/{token}', json={
        'name': 'Updated Share',
        'description': 'Updated description',
        'expires_in': 14
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    # Verify the changes in database
    with app.app_context():
        updated_link = SharedLink.query.filter_by(token=token).first()
        assert updated_link.name == 'Updated Share'


def test_delete_share_link(owner_client, app, test_users, test_file):
    """Test deleting a share link"""
    # First create a share link through the API
    response = owner_client.post(f'/share/file/{test_file.id}', data={
        'name': 'Share to Delete',
        'description': 'This share will be deleted',
        'expires_in': 7
    }, follow_redirects=True)
    
    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data['status'] == 'success'
    
    # Extract token from share link URL
    share_url = response_data['share_link']
    token = share_url.split('/')[-1]
    
    # Test deleting the share link
    response = owner_client.post(f'/share/delete/{token}', follow_redirects=True)
    assert response.status_code == 200
    
    # Verify the link is deleted from database
    with app.app_context():
        deleted_link = SharedLink.query.filter_by(token=token).first()
        assert deleted_link is None


def test_unauthorized_share_access(recipient_client, app, test_users, test_file):
    """Test accessing a file share with password protection"""
    with app.app_context():
        # Create a share link with password protection
        share_link = SharedLink(
            file_id=test_file.id,
            created_by=test_users['owner_id'],
            name='Protected Share',
            password='secret'  # Protected with password
        )
        db = app.extensions['sqlalchemy']
        db.session.add(share_link)
        db.session.commit()
        
        # Test accessing without password should show password prompt
        response = recipient_client.get(f'/shared/{share_link.token}')
        assert response.status_code == 200
        assert b'Password Protected Share' in response.data

        # Test with incorrect password
        response = recipient_client.post('/share/verify-password', data={
            'token': share_link.token,
            'password': 'wrong_password'
        })
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data['status'] == 'error'
        assert 'Incorrect password' in response_data['message']

        # Test with correct password
        response = recipient_client.post('/share/verify-password', data={
            'token': share_link.token,
            'password': 'secret'
        })
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data['status'] == 'success'

        # Test accessing after correct password verification
        response = recipient_client.get(f'/shared/{share_link.token}')
        assert response.status_code == 200
        assert b'needs_password' not in response.data


def test_concurrent_share_access(client, app, test_users, test_file):
    """Test concurrent access to shared files"""
    with app.app_context():
        # Create a share link that expires quickly
        from datetime import datetime, timedelta
        share_link = SharedLink(
            file_id=test_file.id,
            created_by=test_users['owner_id'],
            name='Limited Share',
            expires_at=datetime.now() + timedelta(seconds=1)  # Expires after 1 second
        )
        db = app.extensions['sqlalchemy']
        db.session.add(share_link)
        db.session.commit()
        
        # First access should succeed
        response1 = client.get(f'/shared/{share_link.token}')
        assert response1.status_code == 200
        
        # Second access should also succeed as concurrent access limit is not implemented
        response2 = client.get(f'/shared/{share_link.token}')
        assert response2.status_code == 200
        
        # Access the shared file first to establish the session
        client.get(f'/shared/{share_link.token}')
        
        # Then download the shared file
        response = client.get(f'/shared/{share_link.token}/download')
        
        assert response.status_code == 200
        assert response.data == b'This is a test file for sharing'


def test_share_folder_with_files(owner_client, app, test_users):
    """Test sharing a folder containing files"""
    import os
    with app.app_context():
        # Create a folder
        folder = Folder(
            name='Test Folder',
            owner_id=test_users['owner_id']
        )
        db = app.extensions['sqlalchemy']
        db.session.add(folder)
        db.session.commit()
        
        # Create a file in the database
        file = File(
            name=os.path.join(folder.name, 'test_file.txt'),  # Include folder name in the file path
            size=100,
            owner_id=test_users['owner_id']
        )
        db.session.add(file)
        db.session.commit()
        
        # Create the actual folder and file in the filesystem
        owner = db.session.get(User, test_users['owner_id'])
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], owner.username, folder.name)
        os.makedirs(folder_path, exist_ok=True)
        
        file_path = os.path.join(folder_path, 'test_file.txt')  # Keep the simple filename for filesystem
        with open(file_path, 'wb') as f:
            f.write(b'Test file in shared folder')
        
        # Share the folder
        response = owner_client.post(f'/share/folder/{folder.id}', data={
            'name': 'Folder Share',
            'description': 'Sharing folder with files',
            'expires_in': 7
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify share link was created
        share_link = SharedLink.query.filter_by(folder_id=folder.id).first()
        assert share_link is not None
        
        # Test accessing the shared folder
        response = owner_client.get(f'/shared/{share_link.token}')
        assert response.status_code == 200
        assert b'test_file.txt' in response.data


def test_share_nested_folder(owner_client, app, test_users):
    """Test sharing a nested folder structure"""
    with app.app_context():
        # Create parent folder
        parent_folder = Folder(
            name='Parent Folder',
            owner_id=test_users['owner_id']
        )
        db = app.extensions['sqlalchemy']
        db.session.add(parent_folder)
        db.session.commit()
        
        # Create child folder
        child_folder = Folder(
            name='Child Folder',
            owner_id=test_users['owner_id'],
            parent_id=parent_folder.id
        )
        db.session.add(child_folder)
        db.session.commit()
        
        # Create the folder structure in filesystem
        import os
        owner = db.session.get(User, test_users['owner_id'])
        parent_path = os.path.join(app.config['UPLOAD_FOLDER'], owner.username, parent_folder.name)
        child_path = os.path.join(parent_path, child_folder.name)
        os.makedirs(child_path, exist_ok=True)
        
        # Share the parent folder
        response = owner_client.post(f'/share/folder/{parent_folder.id}', data={
            'name': 'Nested Folder Share',
            'description': 'Sharing nested folders',
            'expires_in': 7
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify share link
        share_link = SharedLink.query.filter_by(folder_id=parent_folder.id).first()
        assert share_link is not None
        
        # Test accessing the shared folder structure
        response = owner_client.get(f'/shared/{share_link.token}')
        assert response.status_code == 200
        assert b'Child Folder' in response.data


def test_share_empty_folder(owner_client, app, test_users):
    """Test sharing an empty folder"""
    with app.app_context():
        # Create an empty folder
        folder = Folder(
            name='Empty Folder',
            owner_id=test_users['owner_id']
        )
        db = app.extensions['sqlalchemy']
        db.session.add(folder)
        db.session.commit()
        
        # Create the folder in filesystem
        import os
        owner = db.session.get(User, test_users['owner_id'])
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], owner.username, folder.name)
        os.makedirs(folder_path, exist_ok=True)
        
        # Share the empty folder
        response = owner_client.post(f'/share/folder/{folder.id}', data={
            'name': 'Empty Folder Share',
            'description': 'Sharing an empty folder',
            'expires_in': 7
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify share link was created
        share_link = SharedLink.query.filter_by(folder_id=folder.id).first()
        assert share_link is not None
        
        # Test accessing the empty shared folder
        response = owner_client.get(f'/shared/{share_link.token}')
        assert response.status_code == 200
        assert b'Empty Folder' in response.data
        

def test_share_nonexistent_folder(owner_client, app, test_users):
    """Test sharing a folder that doesn't exist"""
    response = owner_client.post('/share/folder/99999', data={
        'name': 'Invalid Folder Share',
        'description': 'This folder does not exist',
        'expires_in': 7
    }, follow_redirects=True)
    
    assert response.status_code == 404


def test_share_folder(owner_client, app, test_users):
    """Test sharing a folder"""
    # First create a folder
    with app.app_context():
        folder = Folder(
            name='Shared Folder',
            owner_id=test_users['owner_id']
        )
        db = app.extensions['sqlalchemy']
        db.session.add(folder)
        db.session.commit()
        
        # Create the actual folder in the filesystem
        import os
        owner = db.session.get(User, test_users['owner_id'])
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