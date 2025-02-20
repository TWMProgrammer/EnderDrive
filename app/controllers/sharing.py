from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_file, session, current_app
from app import db
from app.models.file import File
from app.models.folder import Folder
from app.models.shared_link import SharedLink
from app.models.user import User
from app.utils.decorators import login_required
from datetime import datetime, timedelta
import os

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
            is_bulk_parent=False
        )
    else:
        # This is a standalone share
        share_link = SharedLink(
            file_id=file_id,
            created_by=session['user_id'],
            expires_at=expires_at
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
            is_bulk_parent=False
        )
    else:
        # This is a standalone share
        share_link = SharedLink(
            folder_id=folder_id,
            created_by=session['user_id'],
            expires_at=expires_at
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
    
    # Create the parent share that represents the virtual folder
    parent_share = SharedLink(
        created_by=session['user_id'],
        expires_at=expires_at,
        bulk_share_id=bulk_share_id,
        is_bulk_parent=True,
        name='Shared Items'  # Add a name for the virtual folder
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
    
    db.session.delete(share)
    db.session.commit()
    
    return {'status': 'success'}

@sharing.route('/shared/<token>')
@sharing.route('/shared/<token>/<path:subpath>')
def view_shared(token, subpath=''):
    share = SharedLink.query.filter_by(token=token).first()
    if not share or not share.is_valid:
        abort(404)
    
    # Handle bulk share virtual folder
    if share.is_bulk_parent:
        items = []
        for child_share in share.bulk_items:
            if child_share.file_id:
                file = child_share.file
                if file:
                    items.append({
                        'name': os.path.basename(file.name),
                        'full_path': file.name,
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
                                    'full_path': entry_path,
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
                            'full_path': folder.name,
                            'size': 0,
                            'created_at': folder.created_at,
                            'is_file': False,
                            'share_token': child_share.token,  # Include the child's token for direct access
                            'id': folder.id
                        })
        
        # Generate breadcrumbs for subpath navigation
        breadcrumbs = []
        if subpath:
            parts = subpath.split(os.sep)
            current_path = ''
            for part in parts:
                if part:
                    current_path = os.path.join(current_path, part)
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
            current_folder=subpath if subpath else '',
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
        current_folder = subpath if subpath else ''
        
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
                    'full_path': entry_path,
                    'size': entry.stat().st_size,
                    'created_at': datetime.fromtimestamp(entry.stat().st_ctime),
                    'is_file': True,
                    'id': db_item.id
                })
            elif not is_file:
                items.append({
                    'name': os.path.basename(entry_path),
                    'full_path': entry_path,
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
        parts = current_folder.split(os.sep)
        current_path = ''
        for part in parts:
            if part:
                current_path = os.path.join(current_path, part)
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
            
        folder_path = os.path.dirname(folder.name) if '/' in folder.name else folder.name
        base_folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], owner.username, folder_path)
        file_path = os.path.join(base_folder_path, path)
        
        # Security check - make sure the file is within the shared folder
        if not os.path.exists(file_path) or not file_path.startswith(os.path.join(current_app.config['UPLOAD_FOLDER'], owner.username)):
            abort(404)
    
    if not os.path.exists(file_path):
        abort(404)
        
    return send_file(file_path, as_attachment=True) 