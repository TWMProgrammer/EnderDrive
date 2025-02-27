from datetime import datetime
from app import db

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    size = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now())
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    view_access = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    full_access = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)