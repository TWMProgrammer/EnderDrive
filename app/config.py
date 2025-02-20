import os
import secrets

class Config:
    SECRET_KEY = secrets.token_hex(16)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
    UPLOAD_FOLDER = os.path.abspath('uploads')
    SQLALCHEMY_TRACK_MODIFICATIONS = False 