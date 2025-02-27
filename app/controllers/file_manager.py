import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file, current_app, jsonify
from werkzeug.utils import secure_filename
from app import db
from app.models.user import User
from app.models.file import File
from app.models.folder import Folder
from app.models.shared_link import SharedLink
from sqlalchemy import func
import zipfile
import tempfile
import json
from app.utils.filesystem import check_user_quota

file_manager = Blueprint('file_manager', __name__)

@file_manager.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('file_manager.browse', path=''))
    return render_template('index.html')

@file_manager.route('/browse/', defaults={'path': ''})
@file_manager.route('/browse/<path:path>')
def browse(path):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    
    full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user.username, path)
    
    if not os.path.exists(full_path):
        flash('Path not found')
        return redirect(url_for('file_manager.browse', path=''))
        
    items = []
    for item in os.listdir(full_path):
        item_path = os.path.join(full_path, item)
        is_file = os.path.isfile(item_path)
        
        item_size = os.path.getsize(item_path) if is_file else 0
        item_created = datetime.fromtimestamp(os.path.getctime(item_path))
        
        # Get database ID for file/folder
        db_item = None
        relative_path = os.path.join(path, item) if path else item
        if is_file:
            db_item = File.query.filter_by(name=relative_path, owner_id=user_id).first()
            if not db_item:
                # Create file record if it doesn't exist
                db_item = File(name=relative_path, size=item_size, owner_id=user_id)
                db.session.add(db_item)
                db.session.commit()  # Commit to get the ID
        else:
            db_item = Folder.query.filter_by(name=relative_path, owner_id=user_id).first()
            if not db_item:
                # Create folder record if it doesn't exist
                db_item = Folder(name=relative_path, owner_id=user_id)
                db.session.add(db_item)
                db.session.commit()  # Commit to get the ID
        
        items.append({
            'name': item,
            'is_file': is_file,
            'size': item_size,
            'created_at': item_created,
            'path': relative_path,
            'id': db_item.id if db_item else None,
            'folder_id': db_item.id if not is_file else None  # Add folder_id for folders
        })
    
    # Commit any pending changes
    if db.session.dirty:
        db.session.commit()
    
    items.sort(key=lambda x: (x['is_file'], x['name'].lower()))
    
    breadcrumbs = []
    if path:
        parts = path.split('/') if '/' in path else path.split('\\')
        current_path = ''
        for part in parts:
            current_path = os.path.join(current_path, part)
            breadcrumbs.append({
                'name': part,
                'path': current_path
            })
    
    is_admin = user.role_info.name == 'admin'
    
    # Get user's shared links
    shared_links = SharedLink.query.filter_by(created_by=user_id).order_by(SharedLink.created_at.desc()).all()
    
    return render_template('folder_view.html',
                         items=items,
                         breadcrumbs=breadcrumbs,
                         current_path=path,
                         username=user.username,
                         is_admin=is_admin,
                         shared_links=shared_links)

@file_manager.route('/browse/upload/', defaults={'path': ''}, methods=['GET', 'POST'])
@file_manager.route('/browse/upload/<path:path>', methods=['GET', 'POST'])
def upload(path):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    
    if 'file' in request.files:
        files = request.files.getlist('file')
        for file in files:
            if file.filename:
                # Check file size against quota
                file_size = len(file.read())
                file.seek(0)  # Reset file pointer after reading
                
                if not check_user_quota(user_id, file_size):
                    flash('Storage quota exceeded')
                    return redirect(url_for('file_manager.browse', path=path))
                relative_path = file.filename.replace('\\', '/')
                secure_path = '/'.join(secure_filename(part) for part in relative_path.split('/'))
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user.username, path, secure_path)
                
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)
                
                current_path = ''
                path_parts = os.path.dirname(secure_path).split('/')
                for part in path_parts:
                    if part:
                        current_path = os.path.join(current_path, part) if current_path else part
                        if not Folder.query.filter_by(name=current_path, owner_id=user_id).first():
                            new_folder = Folder(name=current_path, owner_id=user_id)
                            db.session.add(new_folder)
                
                file_size = os.path.getsize(file_path)
                new_file = File(name=secure_path, size=file_size, owner_id=user_id)
                db.session.add(new_file)
                
        db.session.commit()
    
    elif 'folder_name' in request.form:
        folder_name = request.form['folder_name']
        if folder_name:
            folder_name = secure_filename(folder_name)
            folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user.username, path, folder_name)
            
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                
                new_folder = Folder(name=folder_name, owner_id=user_id)
                db.session.add(new_folder)
                db.session.commit()
    
    return redirect(url_for('file_manager.browse', path=path))

@file_manager.route('/browse/delete/<path:path>', methods=['POST'])
def delete_item(path):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user.username, path)
    if not os.path.exists(file_path):
        flash('Item not found')
        return redirect(url_for('file_manager.browse', path=os.path.dirname(path)))
    
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
            file_name = os.path.basename(path)
            File.query.filter_by(name=file_name, owner_id=user_id).delete()
        else:
            import shutil
            shutil.rmtree(file_path)
            folder_name = os.path.basename(path)
            Folder.query.filter_by(name=folder_name, owner_id=user_id).delete()
        
        db.session.commit()
        flash('Item deleted successfully')
    except Exception as e:
        flash('Error deleting item: ' + str(e))
    
    return redirect(url_for('file_manager.browse', path=os.path.dirname(path)))

@file_manager.route('/browse/download/<path:path>')
def download_file(path):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user.username, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        flash('File not found')
        return redirect(url_for('file_manager.browse', path=os.path.dirname(path)))

@file_manager.route('/browse/copy', methods=['POST'])
def copy_item():
    if 'user_id' not in session:
        return {'status': 'error', 'message': 'Not logged in'}, 401
        
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    
    source_path = request.form.get('source_path')
    destination_path = request.form.get('destination_path')
    is_file = request.form.get('is_file') == 'true'
    
    if not source_path or not destination_path:
        return {'status': 'error', 'message': 'Missing parameters'}, 400
    
    source_full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user.username, source_path)
    destination_full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user.username, destination_path.strip('/'), os.path.basename(source_path))
    
    try:
        if is_file:
            import shutil
            os.makedirs(os.path.dirname(destination_full_path), exist_ok=True)
            shutil.copy2(source_full_path, destination_full_path)
            
            # Create new file record
            file_size = os.path.getsize(destination_full_path)
            relative_path = os.path.join(destination_path.strip('/'), os.path.basename(source_path))
            new_file = File(name=relative_path, size=file_size, owner_id=user_id)
            db.session.add(new_file)
        else:
            import shutil
            shutil.copytree(source_full_path, destination_full_path)
            
            # Create new folder record
            relative_path = os.path.join(destination_path.strip('/'), os.path.basename(source_path))
            new_folder = Folder(name=relative_path, owner_id=user_id)
            db.session.add(new_folder)
            
            # Create records for all files in the folder
            for root, dirs, files in os.walk(destination_full_path):
                relative_root = os.path.relpath(root, os.path.join(current_app.config['UPLOAD_FOLDER'], user.username))
                
                for dir_name in dirs:
                    folder_path = os.path.join(relative_root, dir_name)
                    if not Folder.query.filter_by(name=folder_path, owner_id=user_id).first():
                        new_folder = Folder(name=folder_path, owner_id=user_id)
                        db.session.add(new_folder)
                
                for file_name in files:
                    file_path = os.path.join(relative_root, file_name)
                    if not File.query.filter_by(name=file_path, owner_id=user_id).first():
                        file_size = os.path.getsize(os.path.join(root, file_name))
                        new_file = File(name=file_path, size=file_size, owner_id=user_id)
                        db.session.add(new_file)
        
        db.session.commit()
        return {'status': 'success'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500

@file_manager.route('/browse/move', methods=['POST'])
def move_item():
    if 'user_id' not in session:
        return {'status': 'error', 'message': 'Not logged in'}, 401
        
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    
    source_path = request.form.get('source_path')
    destination_path = request.form.get('destination_path')
    is_file = request.form.get('is_file') == 'true'
    
    if not source_path or not destination_path:
        return {'status': 'error', 'message': 'Missing parameters'}, 400
    
    source_full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user.username, source_path)
    destination_full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user.username, destination_path.strip('/'), os.path.basename(source_path))
    
    try:
        import shutil
        os.makedirs(os.path.dirname(destination_full_path), exist_ok=True)
        shutil.move(source_full_path, destination_full_path)
        
        if is_file:
            # Update file record
            file = File.query.filter_by(name=source_path, owner_id=user_id).first()
            if file:
                file.name = os.path.join(destination_path.strip('/'), os.path.basename(source_path))
        else:
            # Update folder record and all contained files/folders
            folder = Folder.query.filter_by(name=source_path, owner_id=user_id).first()
            if folder:
                folder.name = os.path.join(destination_path.strip('/'), os.path.basename(source_path))
            
            # Update paths for all files and folders inside
            old_prefix = source_path + '/'
            new_prefix = os.path.join(destination_path.strip('/'), os.path.basename(source_path)) + '/'
            
            File.query.filter(
                File.owner_id == user_id,
                File.name.startswith(old_prefix)
            ).update(
                {File.name: func.concat(new_prefix, func.substr(File.name, len(old_prefix) + 1))},
                synchronize_session=False
            )
            
            Folder.query.filter(
                Folder.owner_id == user_id,
                Folder.name.startswith(old_prefix)
            ).update(
                {Folder.name: func.concat(new_prefix, func.substr(Folder.name, len(old_prefix) + 1))},
                synchronize_session=False
            )
        
        db.session.commit()
        return {'status': 'success'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500

@file_manager.route('/search')
def search_items():
    if 'user_id' not in session:
        return {'status': 'error', 'message': 'Not logged in'}, 401
        
    user_id = session['user_id']
    query = request.args.get('q', '').strip()
    
    if not query:
        return {'status': 'error', 'message': 'No search query provided'}, 400
    
    # Search in both files and folders using database queries
    files = File.query.filter(
        File.owner_id == user_id,
        File.name.ilike(f'%{query}%')
    ).all()
    
    folders = Folder.query.filter(
        Folder.owner_id == user_id,
        Folder.name.ilike(f'%{query}%')
    ).all()
    
    results = []
    
    # Process files
    for file in files:
        results.append({
            'name': os.path.basename(file.name),
            'path': file.name,
            'is_file': True,
            'size': file.size,
            'created_at': file.created_at.isoformat(),
            'id': file.id
        })
    
    # Process folders
    for folder in folders:
        results.append({
            'name': os.path.basename(folder.name),
            'path': folder.name,
            'is_file': False,
            'size': 0,
            'created_at': folder.created_at.isoformat(),
            'id': folder.id
        })
    
    # Sort results - folders first, then files
    results.sort(key=lambda x: (x['is_file'], x['name'].lower()))
    
    return {'status': 'success', 'results': results}

@file_manager.route('/browse/folders')
def get_folders():
    if 'user_id' not in session:
        return {'status': 'error', 'message': 'Not logged in'}, 401
        
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    
    folders = []
    root_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user.username)
    
    for root, dirs, _ in os.walk(root_path):
        relative_root = os.path.relpath(root, root_path)
        if relative_root == '.':
            continue
            
        folders.append({
            'path': relative_root
        })
    
    return {'status': 'success', 'folders': folders}

@file_manager.route('/bulk-download', methods=['POST'])
def bulk_download():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
        
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    
    # Get the list of items to download
    items = request.json.get('items', [])
    if not items:
        return jsonify({'status': 'error', 'message': 'No items selected'}), 400
    
    # Create a temporary zip file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
        with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for item in items:
                item_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user.username, item['path'])
                
                if item['type'] == 'file':
                    # Handle single file
                    if os.path.exists(item_path) and os.path.isfile(item_path):
                        # Add file to zip with its relative path
                        zipf.write(item_path, item['path'])
                else:
                    # Handle folder and its contents
                    if os.path.exists(item_path) and os.path.isdir(item_path):
                        for root, dirs, files in os.walk(item_path):
                            # Calculate the relative path within the user's directory
                            rel_start = os.path.join(current_app.config['UPLOAD_FOLDER'], user.username)
                            rel_path = os.path.relpath(root, rel_start)
                            
                            # Add all files in this directory to the zip
                            for file in files:
                                file_path = os.path.join(root, file)
                                # The arcname will preserve the directory structure
                                arc_name = os.path.join(rel_path, file)
                                zipf.write(file_path, arc_name)
                            
                            # Add empty directories
                            for dir in dirs:
                                dir_path = os.path.join(root, dir)
                                # Create an empty directory in the zip
                                dir_rel_path = os.path.relpath(dir_path, rel_start)
                                # Ensure the directory ends with a slash
                                if not dir_rel_path.endswith('/'):
                                    dir_rel_path += '/'
                                zipinfo = zipfile.ZipInfo(dir_rel_path)
                                zipf.writestr(zipinfo, '')
                
    # Return the path to the zip file
    zip_filename = f'bulk_download_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
    return send_file(
        temp_file.name,
        as_attachment=True,
        download_name=zip_filename,
        mimetype='application/zip'
    )