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
def view_shared(token):
    share = SharedLink.query.filter_by(token=token).first()
    if not share or not share.is_valid:
        abort(404)
    
    if share.file_id:
        item = share.file
        item_type = 'file'
    else:
        item = share.folder
        item_type = 'folder'
    
    if not item:
        abort(404)
    
    return render_template(
        'shared_view.html',
        item=item,
        item_type=item_type,
        share=share,
        username=db.session.get(User, session.get('user_id')).username if 'user_id' in session else None
    )

@sharing.route('/shared/<token>/download')
def download_shared(token):
    share = SharedLink.query.filter_by(token=token).first()
    if not share or not share.is_valid or not share.file_id:
        abort(404)
    
    file = share.file
    if not file:
        abort(404)
    
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], str(file.owner_id), file.name)
    return send_file(file_path, as_attachment=True) 