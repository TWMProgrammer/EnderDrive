import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.config import Config

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
        
        # Initialize roles
        from app.models.role import Role
        from app.models.user import User
        from werkzeug.security import generate_password_hash
        
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin', description='Administrator with full access')
            db.session.add(admin_role)
            
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular user')
            db.session.add(user_role)
            
        db.session.commit()
        
        # Create admin user if it doesn't exist
        if not User.query.filter_by(username='admin').first():
            password = 'twm420'
            hashed_password = generate_password_hash(password)
            
            admin = User(username='admin', password=hashed_password, role_id=admin_role.id)
            db.session.add(admin)
            db.session.commit()

            # Create admin folder
            admin_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'admin')
            if not os.path.exists(admin_folder):
                os.makedirs(admin_folder)

        # Create test user if it doesn't exist
        if not User.query.filter_by(username='Louis').first():
            password = '123'
            hashed_password = generate_password_hash(password)
            
            louis = User(username='Louis', password=hashed_password, role_id=user_role.id)
            db.session.add(louis)
            db.session.commit()

            # Create user folder
            louis_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'Louis')
            if not os.path.exists(louis_folder):
                os.makedirs(louis_folder)

        # Synchronize database with filesystem
        from app.utils.filesystem import synchronize_database_with_filesystem
        synchronize_database_with_filesystem(app)

    return app 