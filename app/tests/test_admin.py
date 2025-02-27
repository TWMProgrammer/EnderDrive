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