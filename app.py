import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
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
class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    users = db.relationship('User', backref='role_info', lazy=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
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
        if not user or user.role_info.name != 'admin':
            flash('Admin access required')
            return redirect(url_for('browse', path=''))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('browse', path=''))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            # Always redirect to browse view, admin dashboard will be accessible via button
            return redirect(url_for('browse', path=''))
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
        # Get the default user role
        user_role = Role.query.filter_by(name='user').first()
        new_user = User(username=username, password=password, role_id=user_role.id)
        db.session.add(new_user)
        db.session.commit()

        # Create user-specific folder
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)

        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/browse/', defaults={'path': ''})
@app.route('/browse/<path:path>')
def browse(path):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Construct the full path
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], user.username, path)
    
    if not os.path.exists(full_path):
        flash('Path not found')
        return redirect(url_for('browse', path=''))
        
    # Get current directory contents
    items = []
    for item in os.listdir(full_path):
        item_path = os.path.join(full_path, item)
        is_file = os.path.isfile(item_path)
        
        # Get item details
        item_size = os.path.getsize(item_path) if is_file else 0
        item_created = datetime.fromtimestamp(os.path.getctime(item_path))
        
        items.append({
            'name': item,
            'is_file': is_file,
            'size': item_size,
            'created_at': item_created,
            'path': os.path.join(path, item) if path else item
        })
    
    # Sort items: folders first, then files, both alphabetically
    items.sort(key=lambda x: (x['is_file'], x['name'].lower()))
    
     # Create breadcrumb navigation
    breadcrumbs = []
    if path:
        parts = path.split('/') if '/' in path else path.split('\\') # Changed this line to handle both '/' and '\' based paths
        current_path = ''
        for part in parts:
            current_path = os.path.join(current_path, part)
            breadcrumbs.append({
                 'name': part,
                 'path': current_path
             })
    
    # Explicitly check if user is admin
    is_admin = user.role_info.name == 'admin'
    
    return render_template('folder_view.html',
                         items=items,
                         breadcrumbs=breadcrumbs,
                         current_path=path,
                         username=user.username,
                         is_admin=is_admin)

@app.route('/browse/upload/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/browse/upload/<path:path>', methods=['GET', 'POST'])
def upload(path):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Handle file upload
    if 'file' in request.files:
        files = request.files.getlist('file')
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], user.username, path, filename)
                
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
    
    # Handle folder creation
    elif 'folder_name' in request.form:
        folder_name = request.form['folder_name']
        if folder_name:
            folder_name = secure_filename(folder_name)
            folder_path = os.path.join(app.config['UPLOAD_FOLDER'], user.username, path, folder_name)
            
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                
                # Create folder record in database
                new_folder = Folder(
                    name=folder_name,
                    owner_id=user_id
                )
                db.session.add(new_folder)
                db.session.commit()
    
    return redirect(url_for('browse', path=path))

@app.route('/browse/delete/<path:path>', methods=['POST'])
def delete_item(path):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Construct the full path
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], user.username, path)
    
    if not os.path.exists(full_path):
        flash('Item not found')
        return redirect(url_for('browse', path=os.path.dirname(path)))
    
    try:
        if os.path.isfile(full_path):
            # Delete file from filesystem
            os.remove(full_path)
            # Delete file record from database
            file_name = os.path.basename(path)
            File.query.filter_by(name=file_name, owner_id=user_id).delete()
        else:
            # Delete folder and its contents from filesystem
            import shutil
            shutil.rmtree(full_path)
            # Delete folder record from database
            folder_name = os.path.basename(path)
            Folder.query.filter_by(name=folder_name, owner_id=user_id).delete()
        
        db.session.commit()
        flash('Item deleted successfully')
    except Exception as e:
        flash('Error deleting item: ' + str(e))
    
    return redirect(url_for('browse', path=os.path.dirname(path)))

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
    role_name = request.form['role']
    
    if User.query.filter_by(username=username).first():
        flash('Username already exists')
        return redirect(url_for('admin_dashboard'))
    
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        flash('Invalid role')
        return redirect(url_for('admin_dashboard'))
    
    hashed_password = generate_password_hash(password, method='pbkdf2')
    new_user = User(username=username, password=hashed_password, role_id=role.id)
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
    role_name = request.form['role']
    
    user = User.query.get(user_id)
    if not user:
        flash('User not found')
        return redirect(url_for('admin_dashboard'))
    
    # Check if username is taken by another user
    existing_user = User.query.filter_by(username=username).first()
    if existing_user and existing_user.id != int(user_id):
        flash('Username already exists')
        return redirect(url_for('admin_dashboard'))
    
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        flash('Invalid role')
        return redirect(url_for('admin_dashboard'))
    
    user.username = username
    if password:  # Only update password if provided
        user.password = generate_password_hash(password, method='pbkdf2')
    user.role_id = role.id
    
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

@app.route('/browse/download/<path:path>')
def download_file(path):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], user.username, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        flash('File not found')
        return redirect(url_for('browse', path=os.path.dirname(path)))

if __name__ == '__main__':
    with app.app_context():
        # Create all database tables if they don't exist already
        db.create_all()
        
        # Create default roles if they don't exist
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin', description='Administrator with full access')
            db.session.add(admin_role)
            
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular user')
            db.session.add(user_role)
            
        db.session.commit()
        
        # Check for admin user, create one if necessary
        if not User.query.filter_by(username='admin').first():
            password = 'twm420'
            hashed_password = generate_password_hash(password)
            
            admin = User(username='admin', password=hashed_password, role_id=admin_role.id)
            db.session.add(admin)
            db.session.commit()

            # Create admin-specific folder
            admin_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'admin')
            if not os.path.exists(admin_folder):
                os.makedirs(admin_folder)

        # Check for louis user, create one if necessary just for testing 
        if not User.query.filter_by(username='Louis').first():
            password = '123'
            hashed_password = generate_password_hash(password)
            
            louis = User(username='Louis', password=hashed_password, role_id=user_role.id)
            db.session.add(louis)
            db.session.commit()

            # Create louis-specific folder
            louis_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'Louis')
            if not os.path.exists(louis_folder):
                os.makedirs(louis_folder)

        # Create uploads folder if it doesn't exist
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

    app.run(debug=True)
