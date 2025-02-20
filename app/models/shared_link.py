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
    bulk_share_id = db.Column(db.String(64), nullable=True)  # Used to group bulk shares together
    is_bulk_parent = db.Column(db.Boolean, default=False)  # Indicates if this is the main share for a bulk share
    name = db.Column(db.String(255), nullable=True)  # Name for virtual folders in bulk shares
    
    # Relationships
    file = db.relationship('File', backref='shared_links', lazy=True)
    folder = db.relationship('Folder', backref='shared_links', lazy=True)
    creator = db.relationship('User', backref='created_shares', lazy=True)
    
    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def generate_bulk_share_id():
        return secrets.token_urlsafe(16)
    
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
    
    @property
    def bulk_items(self):
        """Get all items in this bulk share if this is a bulk parent."""
        if not self.is_bulk_parent:
            return []
        return SharedLink.query.filter_by(bulk_share_id=self.bulk_share_id).filter(SharedLink.id != self.id).all()
    
    @property
    def display_name(self):
        """Get the display name for this share."""
        if self.is_bulk_parent:
            return self.name or 'Shared Items'
        elif self.file_id:
            return self.file.name if self.file else 'Unknown File'
        elif self.folder_id:
            return self.folder.name if self.folder else 'Unknown Folder'
        return 'Unknown Item'