import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.config import Config
import logging

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    from app.controllers.auth import auth
    from app.controllers.admin import admin
    from app.controllers.file_manager import file_manager
    from app.controllers.sharing import sharing

    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(file_manager)
    app.register_blueprint(sharing)

    # Create uploads folder if it doesn't exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    with app.app_context():
        # Create all database tables
        db.create_all()

        # Initialize roles and users only if they don't exist
        with app.app_context():
            initialize_roles_and_users(app)

        # Synchronize database with filesystem
        from app.utils.filesystem import synchronize_database_with_filesystem
        synchronize_database_with_filesystem(app)

    return app

def initialize_roles_and_users(app):
    """Initializes roles and default users (admin, Louis) if they don't exist."""
    from app.models.role import Role
    from app.models.user import User
    from werkzeug.security import generate_password_hash

    try:
        # Initialize roles
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin', description='Administrator with full access')
            db.session.add(admin_role)
            db.session.flush()  # Flush to get the ID for the role
            logging.info("Admin role created")
        else:
            logging.info("Admin role already exists")

        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular user')
            db.session.add(user_role)
            db.session.flush() # Flush to get the ID for the role
            logging.info("User role created")
        else:
            logging.info("User role already exists")

        db.session.commit()

        # Initialize admin user
        if not User.query.filter_by(username='admin').first():
            password = 'twm420'
            hashed_password = generate_password_hash(password)
            admin = User(username='admin', password=hashed_password, role_id=admin_role.id, storage_quota=None)  # Unlimited storage for admin
            db.session.add(admin)
            db.session.commit()
            logging.info("Admin user created")

            # Create admin folder
            admin_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'admin')
            if not os.path.exists(admin_folder):
                os.makedirs(admin_folder)
                logging.info(f"Admin folder created at: {admin_folder}")
            else:
                logging.info(f"Admin folder already exists at: {admin_folder}")
        else:
            logging.info("Admin user already exists")

        # Initialize Louis user
        if not User.query.filter_by(username='Louis').first():
            password = '123'
            hashed_password = generate_password_hash(password)
            louis = User(username='Louis', password=hashed_password, role_id=user_role.id, storage_quota=5 * 1024 * 1024 * 1024)  # 5GB storage quota
            db.session.add(louis)
            db.session.commit()
            logging.info("Louis user created")

            # Create user folder
            louis_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'Louis')
            if not os.path.exists(louis_folder):
                os.makedirs(louis_folder)
                logging.info(f"Louis folder created at: {louis_folder}")
            else:
                logging.info(f"Louis folder already exists at: {louis_folder}")
        else:
            logging.info("Louis user already exists")
    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        logging.error(f"Error during role/user initialization: {e}")
        raise
