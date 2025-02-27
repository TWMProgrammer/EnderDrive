from datetime import datetime
from app import db

class Folder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    size = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now())
    parent_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    view_access = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    full_access = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)