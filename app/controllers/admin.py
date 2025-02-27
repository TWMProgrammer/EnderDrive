from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from werkzeug.security import generate_password_hash
from app import db
from app.models.user import User
from app.models.role import Role
from app.models.file import File
from app.models.folder import Folder
from app.models.activity_log import ActivityLog
from app.utils.decorators import admin_required
from app.utils.filesystem import ensure_user_folder, delete_user_folder
import psutil
import os
from datetime import datetime, timedelta, UTC

admin = Blueprint('admin', __name__)

@admin.route('/admin')
@admin_required
def admin_dashboard():
    users = User.query.all()
    user_storage = {}
    total_storage = 0
    
    for user in users:
        user_files = File.query.filter_by(owner_id=user.id).all()
        storage = sum(file.size for file in user_files)
        user_storage[user.id] = storage
        total_storage += storage
    
    active_users = len(users)
    
    # System health metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Recent activity logs
    recent_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()
    
    # Active sessions in last 24 hours
    yesterday = datetime.now(UTC) - timedelta(days=1)
    active_sessions = ActivityLog.query.filter(
        ActivityLog.timestamp >= yesterday,
        ActivityLog.action == 'login'
    ).count()
    
    return render_template('admin_dashboard.html',
                         users=users,
                         user_storage=user_storage,
                         total_storage=total_storage,
                         active_users=active_users,
                         username=db.session.get(User, session['user_id']).username,
                         cpu_percent=cpu_percent,
                         memory_percent=memory.percent,
                         disk_percent=disk.percent,
                         recent_logs=recent_logs,
                         active_sessions=active_sessions)

@admin.route('/admin/add_user', methods=['POST'])
@admin_required
def add_user():
    username = request.form['username']
    password = request.form['password']
    role_name = request.form['role']
    unlimited_quota = request.form.get('unlimited_quota') == 'on'
    storage_quota = None if unlimited_quota else int(request.form.get('storage_quota', 5)) * 1024 * 1024 * 1024  # Convert GB to bytes
    
    if User.query.filter_by(username=username).first():
        flash('Username already exists')
        return redirect(url_for('admin.admin_dashboard'))
    
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        flash('Invalid role')
        return redirect(url_for('admin.admin_dashboard'))
    
    hashed_password = generate_password_hash(password, method='pbkdf2')
    new_user = User(username=username, password=hashed_password, role_id=role.id, storage_quota=storage_quota)
    db.session.add(new_user)
    
    # Log activity
    log = ActivityLog(
        user_id=session['user_id'],
        action='create_user',
        details=f'Created new user: {username}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    ensure_user_folder(current_app, username)
    flash('User added successfully')
    return redirect(url_for('admin.admin_dashboard'))

@admin.route('/admin/edit_user', methods=['POST'])
@admin_required
def edit_user():
    user_id = request.form['user_id']
    username = request.form['username']
    password = request.form['password']
    role_name = request.form['role']
    unlimited_quota = request.form.get('unlimited_quota') == 'on'
    storage_quota = request.form.get('storage_quota')
    
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found')
        return redirect(url_for('admin.admin_dashboard'))
    
    existing_user = User.query.filter_by(username=username).first()
    if existing_user and existing_user.id != int(user_id):
        flash('Username already exists')
        return redirect(url_for('admin.admin_dashboard'))
    
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        flash('Invalid role')
        return redirect(url_for('admin.admin_dashboard'))
    
    user.username = username
    if password:
        user.password = generate_password_hash(password, method='pbkdf2')
    user.role_id = role.id
    
    if unlimited_quota:
        user.storage_quota = None
    elif storage_quota:
        try:
            quota_gb = float(storage_quota)
            user.storage_quota = int(quota_gb * 1024 * 1024 * 1024)  # Convert GB to bytes
        except ValueError:
            flash('Invalid storage quota value')
    
    db.session.commit()
    flash('User updated successfully')
    return redirect(url_for('admin.admin_dashboard'))

@admin.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found')
        return redirect(url_for('admin.admin_dashboard'))
    
    if user.username == 'admin':
        flash('Cannot delete admin user')
        return redirect(url_for('admin.admin_dashboard'))
    
    delete_user_folder(current_app, user.username)
    
    File.query.filter_by(owner_id=user_id).delete()
    Folder.query.filter_by(owner_id=user_id).delete()
    
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully')
    return redirect(url_for('admin.admin_dashboard'))