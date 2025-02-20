from functools import wraps
from flask import session, redirect, url_for, flash
from app import db
from app.models.user import User

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        user = db.session.get(User, session['user_id'])
        if not user or user.role_info.name != 'admin':
            flash('Admin access required')
            return redirect(url_for('file_manager.browse', path=''))
        return f(*args, **kwargs)
    return decorated_function 