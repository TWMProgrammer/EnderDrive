from datetime import datetime, timedelta
import secrets
from app import db

class SharedLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=True)
    folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    file = db.relationship('File', backref='shared_links', lazy=True)
    folder = db.relationship('Folder', backref='shared_links', lazy=True)
    creator = db.relationship('User', backref='created_shares', lazy=True)
    
    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)
    
    def __init__(self, **kwargs):
        super(SharedLink, self).__init__(**kwargs)
        if not self.token:
            self.token = self.generate_token()
        if not self.expires_at:
            # Default expiration is 7 days
            self.expires_at = datetime.now() + timedelta(days=7)
    
    @property
    def is_expired(self):
        return self.expires_at and datetime.now() > self.expires_at
    
    @property
    def is_valid(self):
        return self.is_active and not self.is_expired 