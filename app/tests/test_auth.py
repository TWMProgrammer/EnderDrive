import pytest
from flask import session
from app.models.user import User
from werkzeug.security import check_password_hash
from app.models.role import Role


def test_register(client, _db):
    """Test user registration functionality"""
    # Test registration page loads
    response = client.get('/register')
    assert response.status_code == 200
    assert b'Register' in response.data
    
    # Test successful registration
    response = client.post('/register', data={
        'username': 'testuser',
        'password': 'Password123!',
        'confirm_password': 'Password123!'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Login' in response.data  # Should redirect to login
    
    # Verify user was created in database
    user = User.query.filter_by(username='testuser').first()
    assert user is not None


def test_login_logout(client, app):
    """Test login and logout functionality"""
    # Create a test user
    with app.app_context():
        from werkzeug.security import generate_password_hash
        # Get user role
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular User')
            db = app.extensions['sqlalchemy']
            db.session.add(user_role)
            db.session.commit()
            
        password = generate_password_hash('Password123!', method='pbkdf2')
        user = User(username='testuser', password=password, role_id=user_role.id)
        db = app.extensions['sqlalchemy']
        db.session.add(user)
        db.session.commit()
    
    # Test login page loads
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Login' in response.data
    
    # Test successful login - don't follow redirects to avoid loop
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'Password123!'
    })
    
    # Should redirect to browse page
    assert response.status_code == 302
    
    # Test user is in session
    with client.session_transaction() as sess:
        assert 'user_id' in sess
    
    # Test logout
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data or b'Welcome' in response.data
    
    # Test user is removed from session
    with client.session_transaction() as sess:
        assert 'user_id' not in sess


def test_login_invalid_credentials(client, app):
    """Test login with invalid credentials"""
    # Create a test user
    with app.app_context():
        from werkzeug.security import generate_password_hash
        # Get user role
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular User')
            db = app.extensions['sqlalchemy']
            db.session.add(user_role)
            db.session.commit()
            
        password = generate_password_hash('Password123!', method='pbkdf2')
        user = User(username='testuser', password=password, role_id=user_role.id)
        db = app.extensions['sqlalchemy']
        db.session.add(user)
        db.session.commit()
    
    # Test login with wrong password
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'WrongPassword'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Invalid credentials' in response.data
    
    # Test login with non-existent user
    response = client.post('/login', data={
        'username': 'nonexistentuser',
        'password': 'Password123!'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Invalid credentials' in response.data


def test_profile_view(client, app):
    """Test profile view functionality"""
    # Create a test user with storage quota
    with app.app_context():
        from werkzeug.security import generate_password_hash
        # Get user role
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular User')
            db = app.extensions['sqlalchemy']
            db.session.add(user_role)
            db.session.commit()
            
        password = generate_password_hash('Password123!', method='pbkdf2')
        user = User(username='testuser', password=password, role_id=user_role.id, storage_quota=1073741824)  # 1GB
        db = app.extensions['sqlalchemy']
        db.session.add(user)
        db.session.commit()
        
        # Login the user
        client.post('/login', data={
            'username': 'testuser',
            'password': 'Password123!'
        })
        
        # Test profile page access when logged in
        response = client.get('/profile')
        assert response.status_code == 200
        assert b'Profile' in response.data
        assert b'testuser' in response.data
        
        # Test storage information is displayed
        assert b'Storage Usage' in response.data
        
        # Logout and test redirect when not logged in
        client.get('/logout')
        response = client.get('/profile', follow_redirects=True)
        assert response.status_code == 200
        assert b'Login' in response.data


def test_update_profile(client, app):
    """Test profile update functionality"""
    # Create a test user
    with app.app_context():
        from werkzeug.security import generate_password_hash
        # Get user role
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular User')
            db = app.extensions['sqlalchemy']
            db.session.add(user_role)
            db.session.commit()
            
        password = generate_password_hash('Password123!', method='pbkdf2')
        user = User(username='testuser', password=password, role_id=user_role.id)
        db = app.extensions['sqlalchemy']
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        
        # Create another user to test username conflict
        other_user = User(username='otheruser', password=password, role_id=user_role.id)
        db.session.add(other_user)
        db.session.commit()
        
        # Login the user
        client.post('/login', data={
            'username': 'testuser',
            'password': 'Password123!'
        })
        
        # Test updating profile with incorrect current password
        response = client.post('/update_profile', data={
            'username': 'testuser',
            'current_password': 'WrongPassword',
            'new_password': 'NewPassword123!'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Current password is incorrect' in response.data
        
        # Test updating profile with existing username
        response = client.post('/update_profile', data={
            'username': 'otheruser',
            'current_password': 'Password123!',
            'new_password': ''
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Username already exists' in response.data
        
        # Test successful username update
        response = client.post('/update_profile', data={
            'username': 'updateduser',
            'current_password': 'Password123!',
            'new_password': ''
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Profile updated successfully' in response.data
        
        # Verify username was updated in database
        user = db.session.get(User, user_id)
        assert user.username == 'updateduser'
        
        # Test successful password update
        response = client.post('/update_profile', data={
            'username': 'updateduser',
            'current_password': 'Password123!',
            'new_password': 'NewPassword123!'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Profile updated successfully' in response.data
        
        # Verify password was updated in database
        user = db.session.get(User, user_id)
        assert check_password_hash(user.password, 'NewPassword123!')