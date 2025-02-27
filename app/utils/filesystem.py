import os
import shutil
from app import db
from app.models.user import User
from app.models.file import File
from app.models.folder import Folder
from flask import flash
from sqlalchemy import func

def get_user_storage_usage(user_id):
    """Calculate total storage usage for a user"""
    return db.session.query(func.sum(File.size)).filter_by(owner_id=user_id).scalar() or 0

def check_user_quota(user_id, required_space=0):
    """Check if user has enough quota for required space"""
    user = db.session.get(User, user_id)
    if not user:
        return False
    
    # If user has unlimited quota (storage_quota is None), always return True
    if user.storage_quota is None:
        return True
    
    current_usage = get_user_storage_usage(user_id)
    return (current_usage + required_space) <= user.storage_quota

def synchronize_database_with_filesystem(app):
    users = db.session.query(User).all()
    
    for user in users:
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], user.username)
        
        if not os.path.exists(user_folder):
            continue
            
        for root, dirs, files in os.walk(user_folder):
            relative_path = os.path.relpath(root, user_folder)
            
            if not File.query.filter_by(name=relative_path).first():
                new_file = File(name=relative_path, owner_id=user.id)
                db.session.add(new_file)
                
            for file in files:
                if not File.query.filter_by(name=os.path.join(relative_path, file)).first():
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    new_file = File(name=os.path.join(relative_path, file), size=file_size, owner_id=user.id)
                    db.session.add(new_file)
        
        for file in File.query.filter_by(owner_id=user.id).all():
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], user.username, file.name)
            if not os.path.exists(file_path):
                File.query.filter_by(id=file.id).delete()
        
        for folder in Folder.query.filter_by(owner_id=user.id).all():
            folder_path = os.path.join(app.config['UPLOAD_FOLDER'], user.username, folder.name)
            if not os.path.exists(folder_path):
                Folder.query.filter_by(id=folder.id).delete()
                
    db.session.commit()

def ensure_user_folder(app, username):
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    return user_folder

def delete_user_folder(app, username):
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
    if os.path.exists(user_folder):
        shutil.rmtree(user_folder)