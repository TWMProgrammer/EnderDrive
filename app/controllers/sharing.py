from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_file, session, current_app
from app import db
from app.models.file import File
from app.models.folder import Folder
from app.models.shared_link import SharedLink
from app.models.user import User
from app.utils.decorators import login_required
from datetime import datetime, timedelta
import os
import zipfile
import tempfile

sharing = Blueprint('sharing', __name__)

@sharing.route('/share/file/<file_id>', methods=['POST'])
@login_required
def share_file(file_id):
    try:
        file_id = int(file_id)
    except (ValueError, TypeError):
        return {'status': 'error', 'message': 'Invalid file ID'}, 400
        
    file = db.session.get(File, file_id)
    if not file or file.owner_id != session['user_id']:
        return {'status': 'error', 'message': 'File not found'}, 404
    
    # Get new share fields
    share_name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    password = request.form.get('password', '').strip()
    
    if not share_name:
        return {'status': 'error', 'message': 'Share name is required'}, 400
    
    if len(description) > 500:
        return {'status': 'error', 'message': 'Description must be less than 500 characters'}, 400
    
    # Create new share link
    expires_in_days = request.form.get('expires_in', 7, type=int)
    expires_at = datetime.now() + timedelta(days=expires_in_days)
    
    # Check if this is part of a bulk share
    bulk_share_id = request.form.get('bulk_share_id')
    if bulk_share_id:
        # This is a child share - create it with the provided bulk_share_id
        share_link = SharedLink(
            file_id=file_id,
            created_by=session['user_id'],
            expires_at=expires_at,
            bulk_share_id=bulk_share_id,
            is_bulk_parent=False,
            name=share_name,
            description=description,
            password=password
        )
    else:
        # This is a standalone share
        share_link = SharedLink(
            file_id=file_id,
            created_by=session['user_id'],
            expires_at=expires_at,
            name=share_name,
            description=description,
            password=password
        )
    
    try:
        db.session.add(share_link)
        db.session.commit()
        
        return {
            'status': 'success',
            'share_link': url_for('sharing.view_shared', token=share_link.token, _external=True),
            'bulk_share_id': bulk_share_id,
            'item_name': file.name,
            'item_type': 'file'
        }
    except Exception as e:
        db.session.rollback()
        return {'status': 'error', 'message': str(e)}, 500

@sharing.route('/share/folder/<folder_id>', methods=['POST'])
@login_required
def share_folder(folder_id):
    try:
        folder_id = int(folder_id)
    except (ValueError, TypeError):
        return {'status': 'error', 'message': 'Invalid folder ID'}, 400
        
    folder = db.session.get(Folder, folder_id)
    if not folder or folder.owner_id != session['user_id']:
        return {'status': 'error', 'message': 'Folder not found'}, 404
    
    # Get new share fields
    share_name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    password = request.form.get('password', '').strip()
    
    if not share_name:
        return {'status': 'error', 'message': 'Share name is required'}, 400
    
    if len(description) > 500:
        return {'status': 'error', 'message': 'Description must be less than 500 characters'}, 400
    
    # Create new share link
    expires_in_days = request.form.get('expires_in', 7, type=int)
    expires_at = datetime.now() + timedelta(days=expires_in_days)
    
    # Check if this is part of a bulk share
    bulk_share_id = request.form.get('bulk_share_id')
    if bulk_share_id:
        # This is a child share - create it with the provided bulk_share_id
        share_link = SharedLink(
            folder_id=folder_id,
            created_by=session['user_id'],
            expires_at=expires_at,
            bulk_share_id=bulk_share_id,
            is_bulk_parent=False,
            name=share_name,
            description=description,
            password=password
        )
    else:
        # This is a standalone share
        share_link = SharedLink(
            folder_id=folder_id,
            created_by=session['user_id'],
            expires_at=expires_at,
            name=share_name,
            description=description,
            password=password
        )
    
    try:
        db.session.add(share_link)
        db.session.commit()
        
        return {
            'status': 'success',
            'share_link': url_for('sharing.view_shared', token=share_link.token, _external=True),
            'bulk_share_id': bulk_share_id,
            'item_name': folder.name,
            'item_type': 'folder'
        }
    except Exception as e:
        db.session.rollback()
        return {'status': 'error', 'message': str(e)}, 500

@sharing.route('/bulk-share', methods=['POST'])
@login_required
def create_bulk_share():
    """Create a virtual folder share that contains multiple items."""
    expires_in_days = request.form.get('expires_in', 7, type=int)
    expires_at = datetime.now() + timedelta(days=expires_in_days)
    bulk_share_id = SharedLink.generate_bulk_share_id()
    
    # Get share details from form
    share_name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    password = request.form.get('password', '').strip()
    
    
    if not share_name:
        temp = "Shared Items"
    else:
        temp = share_name
    
    if len(description) > 500:
        return {'status': 'error', 'message': 'Description must be less than 500 characters'}, 400
    
    # Create the parent share that represents the virtual folder
    parent_share = SharedLink(
        created_by=session['user_id'],
        expires_at=expires_at,
        bulk_share_id=bulk_share_id,
        is_bulk_parent=True,
        name=temp,
        description=description,
        password=password
    )
    
    db.session.add(parent_share)
    db.session.commit()
    
    return {
        'status': 'success',
        'share_link': url_for('sharing.view_shared', token=parent_share.token, _external=True),
        'bulk_share_id': bulk_share_id,
        'item_type': 'virtual_folder'
    }

@sharing.route('/share/extend/<token>', methods=['POST'])
@login_required
def extend_share(token):
    share = SharedLink.query.filter_by(token=token).first()
    if not share or share.created_by != session['user_id']:
        abort(404)
    
    expires_in_days = request.form.get('expires_in', 7, type=int)
    share.expires_at = datetime.now() + timedelta(days=expires_in_days)
    db.session.commit()
    
    return {'status': 'success'}

@sharing.route('/share/delete/<token>', methods=['POST'])
@login_required
def delete_share(token):
    share = SharedLink.query.filter_by(token=token).first()
    if not share or share.created_by != session['user_id']:
        abort(404)
    
    # If this is a bulk share parent or has a bulk_share_id, delete all related shares
    if share.is_bulk_parent or share.bulk_share_id:
        bulk_id = share.bulk_share_id or share.token
        related_shares = SharedLink.query.filter_by(bulk_share_id=bulk_id).all()
        for related_share in related_shares:
            db.session.delete(related_share)
        
        # If this is the bulk parent itself, delete it too
        if share.is_bulk_parent:
            db.session.delete(share)
    else:
        # Regular single share deletion
        db.session.delete(share)
    
    db.session.commit()
    
    return {'status': 'success'}

@sharing.route('/share/verify-password', methods=['POST'])
def verify_share_password():
    token = request.form.get('token')
    password = request.form.get('password')
    
    share = SharedLink.query.filter_by(token=token).first()
    if not share or not share.is_valid:
        abort(404)
    
    if share.password and share.password != password:
        return {'status': 'error', 'message': 'Incorrect password'}
    
    # Store verification in session
    session[f'share_verified_{token}'] = True
    return {'status': 'success'}

@sharing.route('/shared/<token>', defaults={'subpath': ''})
@sharing.route('/shared/<token>/<path:subpath>')
def view_shared(token, subpath=''):
    # URL decode and normalize path separators to forward slashes
    subpath = subpath.replace('%5C', '/').replace('%5c', '/').replace('\\', '/')
    share = SharedLink.query.filter_by(token=token).first()
    if not share or not share.is_valid:
        abort(404)
        
    if share.password and not session.get(f'share_verified_{token}'):
        # Instead of redirecting to password prompt page, render the view with a flag
        return render_template('shared_view.html', 
                             share=share,
                             needs_password=True,
                             token=token)
    
    # Handle bulk share virtual folder
    if share.is_bulk_parent:
        items = []
        for child_share in share.bulk_items:
            if child_share.file_id:
                file = child_share.file
                if file:
                    items.append({
                        'name': os.path.basename(file.name),
                        'full_path': file.name.replace('\\', '/'),
                        'size': file.size,
                        'created_at': file.created_at,
                        'is_file': True,
                        'share_token': child_share.token,  # Include the child's token for direct access
                        'id': file.id
                    })
            elif child_share.folder_id:
                folder = child_share.folder
                if folder:
                    # If we have a subpath and this is the folder we're looking into
                    if subpath and subpath.startswith(folder.name):
                        # Get the owner's username
                        owner = db.session.get(User, folder.owner_id)
                        if not owner:
                            continue
                            
                        # Get the base folder path using the owner's username
                        base_folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], owner.username)
                        
                        # Add the folder's path from the database
                        folder_path = os.path.dirname(folder.name) if '/' in folder.name else folder.name
                        base_folder_path = os.path.join(base_folder_path, folder_path)
                        
                        # Add subpath if provided
                        current_path = os.path.join(base_folder_path, os.path.relpath(subpath, folder.name))
                        
                        if os.path.exists(current_path) and current_path.startswith(os.path.join(current_app.config['UPLOAD_FOLDER'], owner.username)):
                            # List contents of current directory
                            for entry in os.scandir(current_path):
                                entry_path = os.path.join(subpath, entry.name)
                                is_file = entry.is_file()
                                
                                # Get the database record for the file/folder
                                if is_file:
                                    db_item = File.query.filter_by(
                                        name=os.path.join(folder_path, os.path.relpath(entry_path, folder.name)),
                                        owner_id=folder.owner_id
                                    ).first()
                                else:
                                    db_item = Folder.query.filter_by(
                                        name=os.path.join(folder_path, os.path.relpath(entry_path, folder.name)),
                                        owner_id=folder.owner_id
                                    ).first()
                                
                                items.append({
                                    'name': entry.name,
                                    'full_path': entry_path.replace('\\', '/'),
                                    'size': entry.stat().st_size if is_file else 0,
                                    'created_at': datetime.fromtimestamp(entry.stat().st_ctime),
                                    'is_file': is_file,
                                    'share_token': child_share.token,
                                    'id': db_item.id if db_item else None
                                })
                    else:
                        # Just add the folder itself
                        items.append({
                            'name': os.path.basename(folder.name),
                            'full_path': folder.name.replace('\\', '/'),
                            'size': 0,
                            'created_at': folder.created_at,
                            'is_file': False,
                            'share_token': child_share.token,  # Include the child's token for direct access
                            'id': folder.id
                        })
        
        # Generate breadcrumbs for subpath navigation
        breadcrumbs = []
        if subpath:
            parts = subpath.replace('\\', '/').split('/')
            current_path = ''
            for part in parts:
                if part:
                    current_path = (current_path + '/' + part) if current_path else part
                    breadcrumbs.append({
                        'name': part,
                        'path': current_path
                    })
        
        # Sort items - folders first, then files
        items.sort(key=lambda x: (x['is_file'], x['name'].lower()))
        
        return render_template(
            'shared_view.html',
            items=items,
            item_type='virtual_folder',
            current_folder=subpath.replace('\\', '/') if subpath else '',
            breadcrumbs=breadcrumbs,
            share=share,
            is_bulk_share=True,
            username=db.session.get(User, session.get('user_id')).username if 'user_id' in session else None
        )
    
    # Handle regular file/folder share
    if share.file_id:
        item = share.file
        item_type = 'file'
        items = []
        current_folder = None
    else:
        item = share.folder
        item_type = 'folder'
        
        # Get the owner's username
        owner = db.session.get(User, item.owner_id)
        if not owner:
            abort(404)
            
        # Get the base folder path using the owner's username
        base_folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 
                                      owner.username)
        
        # Add the folder's path from the database
        folder_path = os.path.dirname(item.name) if '/' in item.name else item.name
        base_folder_path = os.path.join(base_folder_path, folder_path)
        
        # Add subpath if provided
        current_path = os.path.join(base_folder_path, subpath) if subpath else base_folder_path
        
        if not os.path.exists(current_path) or not current_path.startswith(os.path.join(current_app.config['UPLOAD_FOLDER'], owner.username)):
            abort(404)
            
        items = []
        current_folder = subpath.replace('\\', '/') if subpath else ''
        
        # List contents of current directory
        for entry in os.scandir(current_path):
            entry_path = os.path.relpath(entry.path, base_folder_path)
            is_file = entry.is_file()
            
            # Get the database record for the file/folder
            if is_file:
                db_item = File.query.filter_by(
                    name=os.path.join(folder_path, entry_path) if folder_path else entry_path,
                    owner_id=item.owner_id
                ).first()
            else:
                db_item = Folder.query.filter_by(
                    name=os.path.join(folder_path, entry_path) if folder_path else entry_path,
                    owner_id=item.owner_id
                ).first()
            
            if is_file and db_item:
                items.append({
                    'name': os.path.basename(entry_path),
                    'full_path': entry_path.replace('\\', '/'),
                    'size': entry.stat().st_size,
                    'created_at': datetime.fromtimestamp(entry.stat().st_ctime),
                    'is_file': True,
                    'id': db_item.id
                })
            elif not is_file:
                items.append({
                    'name': os.path.basename(entry_path),
                    'full_path': entry_path.replace('\\', '/'),
                    'size': 0,
                    'created_at': datetime.fromtimestamp(entry.stat().st_ctime),
                    'is_file': False,
                    'id': db_item.id if db_item else None
                })
        
        # Sort items - folders first, then files
        items.sort(key=lambda x: (x['is_file'], x['name'].lower()))
    
    # Generate breadcrumbs
    breadcrumbs = []
    if current_folder:
        parts = current_folder.replace('\\', '/').split('/')
        current_path = ''
        for part in parts:
            if part:
                current_path = (current_path + '/' + part) if current_path else part
                breadcrumbs.append({
                    'name': part,
                    'path': current_path
                })
    
    return render_template(
        'shared_view.html',
        item=item,
        item_type=item_type,
        items=items,
        current_folder=current_folder,
        breadcrumbs=breadcrumbs,
        share=share,
        is_bulk_share=False,
        username=db.session.get(User, session.get('user_id')).username if 'user_id' in session else None
    )

@sharing.route('/shared/<token>/download')
@sharing.route('/shared/<token>/download/<path:path>')
def download_shared(token, path=''):
    share = SharedLink.query.filter_by(token=token).first()
    if not share or not share.is_valid:
        abort(404)
    
    if share.is_bulk_parent:
        # For bulk shares, find the child share that matches the requested file
        child_share = SharedLink.query.filter_by(
            bulk_share_id=share.bulk_share_id,
            name=path
        ).first()
        if not child_share:
            abort(404)
        share = child_share
    
    if share.file_id:
        file = share.file
        if not file:
            abort(404)
            
        owner = db.session.get(User, file.owner_id)
        if not owner:
            abort(404)
            
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], owner.username, file.name)
    else:
        folder = share.folder
        if not folder:
            abort(404)
            
        if not path:
            abort(404)
            
        owner = db.session.get(User, folder.owner_id)
        if not owner:
            abort(404)
            
        # Normalize the base folder path and requested path
        folder_path = os.path.dirname(folder.name) if '/' in folder.name else folder.name
        base_folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], owner.username, folder_path)
        requested_path = path.replace('\\', '/').lstrip('/')
        file_path = os.path.join(base_folder_path, requested_path)
        
        # Security check - make sure the file is within the shared folder
        real_base = os.path.realpath(base_folder_path)
        real_file = os.path.realpath(file_path)
        if not os.path.exists(real_file) or not real_file.startswith(real_base):
            abort(404)
    
    if not os.path.exists(file_path):
        abort(404)
        
    return send_file(file_path, as_attachment=True)

@sharing.route('/api/shares/<token>', methods=['GET'])
@login_required
def get_share(token):
    share = SharedLink.query.filter_by(token=token).first()
    if not share or share.created_by != session['user_id']:
        return {'success': False, 'message': 'Share not found'}, 404
    
    return {
        'success': True,
        'token': share.token,
        'name': share.name,
        'description': share.description,
        'expires_at': share.expires_at.isoformat()
    }

@sharing.route('/api/shares/<token>', methods=['PUT'])
@login_required
def update_share(token):
    share = SharedLink.query.filter_by(token=token).first()
    if not share or share.created_by != session['user_id']:
        return {'success': False, 'message': 'Share not found'}, 404
    
    data = request.get_json()
    
    # Update fields
    if 'name' in data:
        share.name = data['name'].strip()
    if 'description' in data:
        description = data['description'].strip()
        if len(description) > 500:
            return {'success': False, 'message': 'Description must be less than 500 characters'}, 400
        share.description = description
    if 'expires_at' in data:
        try:
            share.expires_at = datetime.fromisoformat(data['expires_at'])
        except ValueError:
            return {'success': False, 'message': 'Invalid expiry date format'}, 400
    if 'password' in data and data['password'].strip():
        share.password = data['password'].strip()
    
    try:
        db.session.commit()
        return {'success': True}
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'message': str(e)}, 500

@sharing.route('/bulk_download', methods=['POST'])
def bulk_download():
    token = request.form.get('token')
    current_folder = request.form.get('current_folder', '')
    share = SharedLink.query.filter_by(token=token).first()
    if not share or not share.is_valid:
        abort(404)
    
    if share.is_bulk_parent:
        # For bulk shares, find the child shares that match the requested files
        child_shares = SharedLink.query.filter_by(
            bulk_share_id=share.bulk_share_id
        ).all()
    else:
        child_shares = [share]
    
    # Create a temporary directory to store the files
    temp_dir = tempfile.mkdtemp()
    
    # Create a zip file
    zip_path = os.path.join(temp_dir, 'bulk_download.zip')
    with zipfile.ZipFile(zip_path, 'w') as zip_file:
        for child_share in child_shares:
            if child_share.file_id:
                file = child_share.file
                if file:
                    owner = db.session.get(User, file.owner_id)
                    if owner:
                        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], owner.username, file.name)
                        # Only include files in the current folder for bulk shares
                        if share.is_bulk_parent:
                            file_relative_path = file.name.replace('\\', '/')
                            if current_folder and not file_relative_path.startswith(current_folder):
                                continue
                            zip_name = os.path.basename(file.name)
                        else:
                            zip_name = os.path.basename(file.name)
                        zip_file.write(file_path, zip_name)
            elif child_share.folder_id:
                folder = child_share.folder
                if folder:
                    owner = db.session.get(User, folder.owner_id)
                    if owner:
                        folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], owner.username, folder.name)
                        # If current_folder is specified, adjust the base path
                        if current_folder:
                            current_path = os.path.join(folder_path, current_folder)
                            if os.path.exists(current_path) and current_path.startswith(folder_path):
                                folder_path = current_path
                        
                        for root, dirs, files in os.walk(folder_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                # Create relative path for the zip file
                                zip_name = os.path.relpath(file_path, folder_path)
                                zip_file.write(file_path, zip_name)
    
    # Return the zip file
    return send_file(zip_path, as_attachment=True)