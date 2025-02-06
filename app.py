import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import secrets
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'uploads'

db = SQLAlchemy(app)

# Database models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())

class Folder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    size = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now())
    parent_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    view_access = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    full_access = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    size = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now())
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    view_access = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    full_access = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            flash('Admin access required')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'error')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(
            password=request.form['password'],
            method='pbkdf2'
        )
        new_user = User(username=username, password=password, role='user')
        db.session.add(new_user)
        db.session.commit()

        # Create user-specific folder
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)

        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    user = User.query.get(user_id)
    folders = Folder.query.filter_by(owner_id=user_id).all()
    files = File.query.filter_by(owner_id=user_id).all()
    
    def process_file_upload(files):
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], user.username, filename)
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                file.save(file_path)
                
                # Create file record in database
                file_size = os.path.getsize(file_path)
                new_file = File(
                    name=filename,
                    size=file_size,
                    owner_id=user_id
                )
                db.session.add(new_file)
                db.session.commit()

    def process_folder_upload(files):
        for file in files:
            if file.filename:
                # Get the relative path within the uploaded folder
                relative_path = file.filename.replace('\\', '/')
                
                # Extract folder name (first directory in path)
                folder_name = relative_path.split('/')[0]
                
                # Create folder in database if it doesn't exist
                folder = Folder.query.filter_by(
                    name=folder_name,
                    owner_id=user_id
                ).first()
                
                if not folder:
                    folder = Folder(
                        name=folder_name,
                        owner_id=user_id
                    )
                    db.session.add(folder)
                    db.session.commit()
                
                # Save the file
                filename = secure_filename(relative_path)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], user.username, filename)
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                file.save(file_path)
                
                # Create file record in database
                file_size = os.path.getsize(file_path)
                new_file = File(
                    name=filename,
                    size=file_size,
                    owner_id=user_id
                )
                db.session.add(new_file)
                db.session.commit()

    def create_folder(folder_name):
        # Create folder in filesystem
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], user.username, folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            
        # Create folder record in database
        new_folder = Folder(
            name=folder_name,
            owner_id=user_id
        )
        db.session.add(new_folder)
        db.session.commit()

    if request.method == 'POST':
        if 'file' in request.files:
            uploaded_files = request.files.getlist('file')
            process_file_upload(uploaded_files)
            return redirect(url_for('dashboard'))
        elif 'folder[]' in request.files:
            uploaded_files = request.files.getlist('folder[]')
            process_folder_upload(uploaded_files)
            return redirect(url_for('dashboard'))
        elif 'folder_name' in request.form:
            folder_name = request.form['folder_name']
            if folder_name:
                create_folder(folder_name)
                return redirect(url_for('dashboard'))
    
    return render_template('dashboard.html', 
                         folders=folders, 
                         files=files, 
                         username=user.username,
                         is_admin=user.role == 'admin')

@app.route('/admin')
@admin_required
def admin_dashboard():
    users = User.query.all()
    
    # Calculate storage used by each user
    user_storage = {}
    total_storage = 0
    for user in users:
        user_files = File.query.filter_by(owner_id=user.id).all()
        storage = sum(file.size for file in user_files)
        user_storage[user.id] = storage
        total_storage += storage
    
    # Count active users (simplified - just showing total users for now)
    active_users = len(users)
    
    return render_template('admin_dashboard.html',
                         users=users,
                         user_storage=user_storage,
                         total_storage=total_storage,
                         active_users=active_users,
                         username=User.query.get(session['user_id']).username)

@app.route('/admin/add_user', methods=['POST'])
@admin_required
def add_user():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']
    
    if User.query.filter_by(username=username).first():
        flash('Username already exists')
        return redirect(url_for('admin_dashboard'))
    
    hashed_password = generate_password_hash(password, method='pbkdf2')
    new_user = User(username=username, password=hashed_password, role=role)
    db.session.add(new_user)
    db.session.commit()
    
    # Create user-specific folder
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    
    flash('User added successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit_user', methods=['POST'])
@admin_required
def edit_user():
    user_id = request.form['user_id']
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']
    
    user = User.query.get(user_id)
    if not user:
        flash('User not found')
        return redirect(url_for('admin_dashboard'))
    
    # Check if username is taken by another user
    existing_user = User.query.filter_by(username=username).first()
    if existing_user and existing_user.id != int(user_id):
        flash('Username already exists')
        return redirect(url_for('admin_dashboard'))
    
    user.username = username
    if password:  # Only update password if provided
        user.password = generate_password_hash(password, method='pbkdf2')
    user.role = role
    
    db.session.commit()
    flash('User updated successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found')
        return redirect(url_for('admin_dashboard'))
    
    if user.username == 'admin':
        flash('Cannot delete admin user')
        return redirect(url_for('admin_dashboard'))
    
    # Delete user's files and folders from filesystem
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], user.username)
    if os.path.exists(user_folder):
        import shutil
        shutil.rmtree(user_folder)
    
    # Delete user's files and folders from database
    File.query.filter_by(owner_id=user_id).delete()
    Folder.query.filter_by(owner_id=user_id).delete()
    
    # Delete the user
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        # Create all database tables if they don't exist already
        db.create_all()
        
        # Check for admin user, create one if necessary
        if not User.query.filter_by(username='admin').first():
            password = 'twm420'
            hashed_password = generate_password_hash(password)
            
            admin = User(username='admin', password=hashed_password, role='admin')
            db.session.add(admin)
            db.session.commit()

        # Create uploads folder if it doesn't exist
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

    app.run(debug=True)
