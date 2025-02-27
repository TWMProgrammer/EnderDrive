from flask import Blueprint, send_from_directory, current_app
import os

favicon = Blueprint('favicon', __name__)

@favicon.route('/favicon.ico')
def serve_favicon():
    """Serve the favicon.ico file from the static folder"""
    return send_from_directory(
        os.path.join(current_app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )

@favicon.route('/favicon.png')
def serve_favicon_png():
    """Serve the favicon.png file from the static folder"""
    return send_from_directory(
        os.path.join(current_app.root_path, 'static'),
        'favicon.png',
        mimetype='image/png'
    )