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

@sharing.route('/share/file/<int:file_id>', methods=['POST'])
@login_required
def share_file(file_id):
    file = db.session.get(File, file_id)
    if not file or file.owner_id != session['user_id']:
        abort(404)
    
    # Create new share link
    expires_in_days = request.form.get('expires_in', 7, type=int)
    expires_at = datetime.now() + timedelta(days=expires_in_days)
    
    share_link = SharedLink(
        file_id=file_id,
        created_by=session['user_id'],
        expires_at=expires_at
    )
    
    db.session.add(share_link)
    db.session.commit()
    
    return {
        'status': 'success',
        'share_link': url_for('sharing.view_shared', token=share_link.token, _external=True)
    }

@sharing.route('/share/folder/<int:folder_id>', methods=['POST'])
@login_required
def share_folder(folder_id):
    folder = db.session.get(Folder, folder_id)
    if not folder or folder.owner_id != session['user_id']:
        abort(404)
    
    # Create new share link
    expires_in_days = request.form.get('expires_in', 7, type=int)
    expires_at = datetime.now() + timedelta(days=expires_in_days)
    
    share_link = SharedLink(
        folder_id=folder_id,
        created_by=session['user_id'],
        expires_at=expires_at
    )
    
    db.session.add(share_link)
    db.session.commit()
    
    return {
        'status': 'success',
        'share_link': url_for('sharing.view_shared', token=share_link.token, _external=True)
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
            
            if is_file:
                file_record = File.query.filter_by(
                    name=os.path.join(folder_path, entry_path) if folder_path else entry_path,
                    owner_id=item.owner_id
                ).first()
                
                if file_record:
                    items.append({
                        'name': os.path.basename(entry_path),
                        'full_path': entry_path,
                        'size': entry.stat().st_size,
                        'created_at': datetime.fromtimestamp(entry.stat().st_ctime),
                        'is_file': True
                    })
            else:
                items.append({
                    'name': os.path.basename(entry_path),
                    'full_path': entry_path,
                    'size': 0,
                    'created_at': datetime.fromtimestamp(entry.stat().st_ctime),
                    'is_file': False
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