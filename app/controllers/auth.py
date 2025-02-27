from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models.user import User
from app.models.role import Role
from app.models.file import File
from app.utils.filesystem import ensure_user_folder

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('file_manager.browse', path=''))
        flash('Invalid credentials', 'error')
        return redirect(url_for('auth.login'))
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(
            password=request.form['password'],
            method='pbkdf2'
        )
        user_role = Role.query.filter_by(name='user').first()
        new_user = User(username=username, password=password, role_id=user_role.id)
        db.session.add(new_user)
        db.session.commit()

        ensure_user_folder(current_app, username)
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('file_manager.index'))

@auth.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    current_user = db.session.get(User, user_id)
    
    # Calculate storage usage
    user_files = File.query.filter_by(owner_id=user_id).all()
    storage_used = sum(file.size for file in user_files)
    
    # Calculate percentage for progress bar
    storage_percent = 0
    if current_user.storage_quota and storage_used > 0:
        storage_percent = min(100, (storage_used / current_user.storage_quota) * 100)
    elif storage_used > 0:
        storage_percent = 50  # Default for unlimited storage
    
    return render_template('profile.html', 
                          current_user=current_user,
                          username=current_user.username,
                          storage_used=storage_used,
                          storage_percent=storage_percent)

@auth.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    
    username = request.form['username']
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    
    # Verify current password
    if not check_password_hash(user.password, current_password):
        flash('Current password is incorrect', 'danger')
        return redirect(url_for('auth.profile'))
    
    # Check if username already exists (if changed)
    if username != user.username:
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists', 'danger')
            return redirect(url_for('auth.profile'))
        user.username = username
    
    # Update password if provided
    if new_password:
        user.password = generate_password_hash(new_password, method='pbkdf2')
    
    db.session.commit()
    flash('Profile updated successfully', 'success')
    return redirect(url_for('auth.profile'))