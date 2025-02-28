import pytest
from app.models.user import User
from app.models.role import Role
from werkzeug.security import generate_password_hash


@pytest.fixture
def admin_user(app):
    """Create an admin user for testing admin functionality"""
    with app.app_context():
        # First ensure admin role exists
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin', description='Administrator')
            db = app.extensions['sqlalchemy']
            db.session.add(admin_role)
            db.session.commit()
        
        # Create admin user
        password = generate_password_hash('AdminPass123!', method='pbkdf2')
        admin = User(username='adminuser', password=password, role_id=admin_role.id)
        db = app.extensions['sqlalchemy']
        db.session.add(admin)
        db.session.commit()
        return admin


@pytest.fixture
def admin_client(client, admin_user):
    """A test client authenticated as an admin user"""
    client.post('/login', data={
        'username': 'adminuser',
        'password': 'AdminPass123!'
    })
    return client


def test_admin_dashboard_access(admin_client):
    """Test that admin can access the admin dashboard"""
    response = admin_client.get('/admin')
    assert response.status_code == 200
    assert b'Admin Dashboard' in response.data


def test_regular_user_cannot_access_admin(client, app):
    """Test that regular users cannot access admin pages"""
    # Create a regular user
    with app.app_context():
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular User')
            db = app.extensions['sqlalchemy'].db
            db.session.add(user_role)
            db.session.commit()
            
        password = generate_password_hash('UserPass123!', method='pbkdf2')
        user = User(username='regularuser', password=password, role_id=user_role.id)
        db = app.extensions['sqlalchemy']
        db.session.add(user)
        db.session.commit()
    
    # Login as regular user
    client.post('/login', data={
        'username': 'regularuser',
        'password': 'UserPass123!'
    })
    
    # Try to access admin dashboard - don't follow redirects to avoid loop
    response = client.get('/admin')
    
    # Should be redirected (302 status code)
    assert response.status_code == 302


def test_user_management(admin_client, app):
    """Test user management functionality"""
    # Create a test user to manage
    with app.app_context():
        user_role = Role.query.filter_by(name='user').first()
        password = generate_password_hash('ManagedPass123!', method='pbkdf2')
        test_user = User(username='testmanaged', password=password, role_id=user_role.id)
        db = app.extensions['sqlalchemy']
        db.session.add(test_user)
        db.session.commit()
        user_id = test_user.id
    
    # Test viewing user list - this is part of the admin dashboard
    response = admin_client.get('/admin')
    assert response.status_code == 200
    assert b'testmanaged' in response.data
    
    # Since there's no specific user details view in the controller,
    # we'll test the admin dashboard which should contain user information
    response = admin_client.get('/admin')
    assert response.status_code == 200
    assert b'testmanaged' in response.data


def test_add_user(admin_client, app):
    """Test adding a new user as admin"""
    # Test adding a new user
    response = admin_client.post('/admin/add_user', data={
        'username': 'newuser',
        'password': 'NewUserPass123!',
        'role': 'user',
        'storage_quota': '5'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    # Instead of checking for flash message, verify the user was created in database
    
    # Verify user was created in database
    with app.app_context():
        user = User.query.filter_by(username='newuser').first()
        assert user is not None
        assert user.role_info.name == 'user'
        # 5GB in bytes
        assert user.storage_quota == 5 * 1024 * 1024 * 1024


def test_edit_user(admin_client, app):
    """Test editing a user as admin"""
    # First create a user to edit
    with app.app_context():
        user_role = Role.query.filter_by(name='user').first()
        password = generate_password_hash('EditUserPass123!', method='pbkdf2')
        test_user = User(username='edituser', password=password, role_id=user_role.id, storage_quota=1024*1024*1024)
        db = app.extensions['sqlalchemy']
        db.session.add(test_user)
        db.session.commit()
        user_id = test_user.id
    
    # Test editing the user
    response = admin_client.post('/admin/edit_user', data={
        'user_id': user_id,
        'username': 'editeduser',
        'password': 'NewEditPass123!',
        'role': 'user',
        'storage_quota': '10'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    # Instead of checking for flash message, verify the user was updated in database
    
    # Verify user was updated in database
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.username == 'editeduser'
        # 10GB in bytes
        assert user.storage_quota == 10 * 1024 * 1024 * 1024


def test_delete_user(admin_client, app):
    """Test deleting a user as admin"""
    # First create a user to delete
    with app.app_context():
        user_role = Role.query.filter_by(name='user').first()
        password = generate_password_hash('DeleteUserPass123!', method='pbkdf2')
        test_user = User(username='deleteuser', password=password, role_id=user_role.id)
        db = app.extensions['sqlalchemy']
        db.session.add(test_user)
        db.session.commit()
        user_id = test_user.id
    
    # Test deleting the user
    response = admin_client.post(f'/admin/delete_user/{user_id}', follow_redirects=True)
    
    assert response.status_code == 200
    # Instead of checking for flash message, verify the user was deleted from database
    
    # Verify user was deleted from database
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user is None