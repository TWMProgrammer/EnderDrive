from flask import flash, redirect, url_for, render_template, session, request
from werkzeug.security import generate_password_hash
from app import db
from app.models.user import User
from app.models.role import Role
import os

def setup_required():
    """Check if first-time setup is required"""
    return not User.query.first()

def handle_setup(app):
    """Handle the setup wizard process"""
    # Check if setup is still required
    if not setup_required():
        # If setup is not required, redirect to login
        return redirect(url_for('auth.login'))
    
    # Always render the setup wizard template for GET requests
    if request.method == 'GET':
        return render_template('setup_wizard.html')
        
    if request.method == 'POST':
        try:
            # Create admin role
            admin_role = Role(name='admin', description='Administrator with full access')
            db.session.add(admin_role)
            db.session.flush()

            # Create user role
            user_role = Role(name='user', description='Regular user')
            db.session.add(user_role)
            db.session.flush()

            # Create admin user
            admin_username = request.form['admin_username']
            admin_password = request.form['admin_password']
            if not admin_username or not admin_password:
                flash('Admin username and password are required', 'error')
                return render_template('setup_wizard.html')

            if User.query.filter_by(username=admin_username).first():
                flash('Username already exists', 'error')
                return render_template('setup_wizard.html')

            hashed_password = generate_password_hash(admin_password)
            admin = User(username=admin_username,
                        password=hashed_password,
                        role_id=admin_role.id,
                        storage_quota=None)  # Unlimited storage for admin
            db.session.add(admin)

            # Create admin folder
            admin_folder = os.path.join(app.config['UPLOAD_FOLDER'], admin_username)
            if not os.path.exists(admin_folder):
                os.makedirs(admin_folder)

            db.session.commit()
            flash('Setup completed successfully! Please login with your new admin credentials.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error during setup: {str(e)}', 'error')
            return render_template('setup_wizard.html')

    return render_template('setup_wizard.html')