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