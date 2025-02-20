from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models.user import User
from app.models.role import Role
from app.utils.filesystem import ensure_user_folder

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('file_manager.browse', path=''))
        flash('Invalid credentials', 'error')
        return redirect(url_for('auth.login'))
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(
            password=request.form['password'],
            method='pbkdf2'
        )
        user_role = Role.query.filter_by(name='user').first()
        new_user = User(username=username, password=password, role_id=user_role.id)
        db.session.add(new_user)
        db.session.commit()

        ensure_user_folder(current_app, username)
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('file_manager.index')) 