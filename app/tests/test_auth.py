import pytest
from flask import session
from app.models.user import User
from werkzeug.security import check_password_hash
from app.models.role import Role


def test_register_page_loads(client):
    """Test registration page loads successfully."""
    response = client.get('/register')
    assert response.status_code == 200
    assert b'Register' in response.data


def test_register_successful(client, _db):
    """Test successful user registration."""
    response = client.post('/register', data={
        'username': 'testuser',
        'password': 'Password123!',
        'confirm_password': 'Password123!'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Login' in response.data  # Should redirect to login

    user = User.query.filter_by(username='testuser').first()
    assert user is not None


def test_register_mismatched_passwords(client):
    """Test registration with mismatched passwords."""
    response = client.post('/register', data={
        'username': 'testuser2',
        'password': 'Password123!',
        'confirm_password': 'DifferentPassword123!'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Passwords do not match' in response.data


def test_register_short_password(client):
    """Test registration with a password that is too short."""
    response = client.post('/register', data={
        'username': 'testuser3',
        'password': 'short',
        'confirm_password': 'short'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Password must be at least' in response.data


def test_register_invalid_username(client):
    """Test registration with an invalid username (special characters)."""
    response = client.post('/register', data={
        'username': 'test@user#$',
        'password': 'Password123!',
        'confirm_password': 'Password123!'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Username can only contain' in response.data


def test_register_existing_username(client, app):
    """Test registration with an existing username."""
    with app.app_context():
        from werkzeug.security import generate_password_hash
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular User')
            db = app.extensions['sqlalchemy']
            db.session.add(user_role)
            db.session.commit()
        password = generate_password_hash('Password123!', method='pbkdf2')
        user = User(username='testuser4', password=password, role_id=user_role.id)
        db = app.extensions['sqlalchemy']
        db.session.add(user)
        db.session.commit()

    response = client.post('/register', data={
        'username': 'testuser4',
        'password': 'Password123!',
        'confirm_password': 'Password123!'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Username already exists' in response.data


def test_login_page_loads(client):
    """Test login page loads successfully."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Login' in response.data


def test_login_successful(client, app):
    """Test successful user login."""
    with app.app_context():
        from werkzeug.security import generate_password_hash
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular User')
            db = app.extensions['sqlalchemy']
            db.session.add(user_role)
            db.session.commit()
        password = generate_password_hash('Password123!', method='pbkdf2')
        user = User(username='testuser5', password=password, role_id=user_role.id)
        db = app.extensions['sqlalchemy']
        db.session.add(user)
        db.session.commit()

    response = client.post('/login', data={
        'username': 'testuser5',
        'password': 'Password123!'
    })

    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert 'user_id' in sess


def test_logout(client, app):
    """Test successful user logout."""
    with app.app_context():
        from werkzeug.security import generate_password_hash
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular User')
            db = app.extensions['sqlalchemy']
            db.session.add(user_role)
            db.session.commit()
        password = generate_password_hash('Password123!', method='pbkdf2')
        user = User(username='testuser6', password=password, role_id=user_role.id)
        db = app.extensions['sqlalchemy']
        db.session.add(user)
        db.session.commit()
        client.post('/login', data={'username': 'testuser6', 'password': 'Password123!'})
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data or b'Welcome' in response.data
    with client.session_transaction() as sess:
        assert 'user_id' not in sess


def test_login_invalid_credentials(client, app):
    """Test login with invalid credentials."""
    with app.app_context():
        from werkzeug.security import generate_password_hash
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular User')
            db = app.extensions['sqlalchemy']
            db.session.add(user_role)
            db.session.commit()
        password = generate_password_hash('Password123!', method='pbkdf2')
        user = User(username='testuser7', password=password, role_id=user_role.id)
        db = app.extensions['sqlalchemy']
        db.session.add(user)
        db.session.commit()

    response = client.post('/login', data={
        'username': 'testuser7',
        'password': 'WrongPassword'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Invalid credentials' in response.data


def test_login_nonexistent_user(client):
    """Test login with a non-existent username."""
    response = client.post('/login', data={
        'username': 'nonexistentuser',
        'password': 'Password123!'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Invalid credentials' in response.data


def test_profile_view_logged_in(client, app):
    """Test profile view access when logged in."""
    with app.app_context():
        from werkzeug.security import generate_password_hash
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular User')
            db = app.extensions['sqlalchemy']
            db.session.add(user_role)
            db.session.commit()
        password = generate_password_hash('Password123!', method='pbkdf2')
        user = User(username='testuser8', password=password, role_id=user_role.id, storage_quota=1073741824)
        db = app.extensions['sqlalchemy']
        db.session.add(user)
        db.session.commit()
        client.post('/login', data={'username': 'testuser8', 'password': 'Password123!'})

    response = client.get('/profile')
    assert response.status_code == 200
    assert b'Profile' in response.data
    assert b'testuser8' in response.data
    assert b'Storage Usage' in response.data


def test_profile_view_logged_out(client):
    """Test profile view redirect when not logged in."""
    response = client.get('/profile', follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data


def test_update_profile_incorrect_password(client, app):
    """Test profile update with incorrect current password."""
    with app.app_context():
        from werkzeug.security import generate_password_hash
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular User')
            db = app.extensions['sqlalchemy']
            db.session.add(user_role)
            db.session.commit()
        password = generate_password_hash('Password123!', method='pbkdf2')
        user = User(username='testuser9', password=password, role_id=user_role.id)
        db = app.extensions['sqlalchemy']
        db.session.add(user)
        db.session.commit()
        client.post('/login', data={'username': 'testuser9', 'password': 'Password123!'})

    response = client.post('/update_profile', data={
        'username': 'testuser9',
        'current_password': 'WrongPassword',
        'new_password': 'NewPassword123!'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Current password is incorrect' in response.data


def test_update_profile_existing_username(client, app):
    """Test profile update with existing username."""
    with app.app_context():
        from werkzeug.security import generate_password_hash
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular User')
            db = app.extensions['sqlalchemy']
            db.session.add(user_role)
            db.session.commit()
        password = generate_password_hash('Password123!', method='pbkdf2')
        user = User(username='testuser10', password=password, role_id=user_role.id)
        other_user = User(username='otheruser10', password=password, role_id=user_role.id)
        db = app.extensions['sqlalchemy']
        db.session.add(user)
        db.session.add(other_user)
        db.session.commit()
        client.post('/login', data={'username': 'testuser10', 'password': 'Password123!'})

    response = client.post('/update_profile', data={
        'username': 'otheruser10',
        'current_password': 'Password123!',
        'new_password': ''
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Username already exists' in response.data


def test_update_profile_successful_username(client, app):
    """Test successful profile username update."""
    with app.app_context():
        from werkzeug.security import generate_password_hash
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular User')
            db = app.extensions['sqlalchemy']
            db.session.add(user_role)
            db.session.commit()
        password = generate_password_hash('Password123!', method='pbkdf2')
        user = User(username='testuser11', password=password, role_id=user_role.id)
        db = app.extensions['sqlalchemy']
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        client.post('/login', data={'username': 'testuser11', 'password': 'Password123!'})

    response = client.post('/update_profile', data={
        'username': 'updateduser11',
        'current_password': 'Password123!',
        'new_password': ''
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Profile updated successfully' in response.data
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.username == 'updateduser11'


def test_update_profile_successful_password(client, app):
    """Test successful profile password update."""
    with app.app_context():
        from werkzeug.security import generate_password_hash
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular User')
            db = app.extensions['sqlalchemy']
            db.session.add(user_role)
            db.session.commit()
        password = generate_password_hash('Password123!', method='pbkdf2')
        user = User(username='testuser12', password=password, role_id=user_role.id)
        db = app.extensions['sqlalchemy']
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        client.post('/login', data={'username': 'testuser12', 'password': 'Password123!'})

    response = client.post('/update_profile', data={
        'username': 'testuser12',
        'current_password': 'Password123!',
        'new_password': 'NewPassword123!'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Profile updated successfully' in response.data
    with app.app_context():
        user = db.session.get(User, user_id)
        assert check_password_hash(user.password, 'NewPassword123!')

