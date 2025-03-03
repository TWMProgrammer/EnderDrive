import pytest
from app.models.user import User
from app.models.role import Role
from app.utils.setup_wizard import setup_required
import os

def test_setup_required_initial_state(app):
    """Test that setup is required when no users exist"""
    with app.app_context():
        assert setup_required() is True

def test_root_redirects_to_setup(client):
    """Test that the root URL redirects to the setup wizard when no users exist"""
    # Check that the root URL redirects to the setup wizard
    response = client.get('/')
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/setup')

def test_setup_wizard_page_loads(client):
    """Test that setup wizard page loads correctly when accessed directly"""
    # Check that the setup page loads directly
    response = client.get('/setup')
    assert response.status_code == 200

def test_setup_wizard_successful(client, app):
    """Test successful completion of setup wizard"""
    response = client.post('/setup', data={
        'admin_username': 'testadmin',
        'admin_password': 'AdminPass123!'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Setup completed successfully' in response.data

    with app.app_context():
        # Verify admin role was created
        admin_role = Role.query.filter_by(name='admin').first()
        assert admin_role is not None
        assert admin_role.description == 'Administrator with full access'

        # Verify user role was created
        user_role = Role.query.filter_by(name='user').first()
        assert user_role is not None
        assert user_role.description == 'Regular user'

        # Verify admin user was created
        admin_user = User.query.filter_by(username='testadmin').first()
        assert admin_user is not None
        assert admin_user.role_id == admin_role.id
        assert admin_user.storage_quota is None  # Admin should have unlimited quota

        # Verify admin folder was created
        admin_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'testadmin')
        assert os.path.exists(admin_folder)

def test_setup_wizard_missing_credentials(client):
    """Test setup wizard with missing credentials"""
    response = client.post('/setup', data={
        'admin_username': '',
        'admin_password': ''
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Admin username and password are required' in response.data

def test_setup_wizard_existing_user(client, app):
    """Test setup wizard when users already exist"""
    # First complete a successful setup
    client.post('/setup', data={
        'admin_username': 'testadmin',
        'admin_password': 'AdminPass123!'
    })

    # Create a user to simulate that setup is already done
    with app.app_context():
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin', description='Administrator with full access')
            db.session.add(admin_role)
            db.session.commit()
        
        # This should make setup_required() return False
        from werkzeug.security import generate_password_hash
        user = User(username='existinguser', 
                   password=generate_password_hash('password'),
                   role_id=admin_role.id)
        from app import db
        db.session.add(user)
        db.session.commit()
    
    # Try to access setup wizard again - it should redirect to login
    response = client.get('/setup', follow_redirects=True)
    assert b'Login' in response.data

def test_setup_wizard_filesystem_creation(client, app):
    """Test that setup wizard properly creates filesystem structure"""
    response = client.post('/setup', data={
        'admin_username': 'testadmin',
        'admin_password': 'AdminPass123!'
    }, follow_redirects=True)

    assert response.status_code == 200

    # Verify upload folder structure
    upload_folder = app.config['UPLOAD_FOLDER']
    assert os.path.exists(upload_folder)
    admin_folder = os.path.join(upload_folder, 'testadmin')
    assert os.path.exists(admin_folder)