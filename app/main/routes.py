# app/main/routes.py
from flask import render_template, redirect, url_for
from flask_login import current_user
from app.main import main_bp # Importa el Blueprint que acabas de crear

@main_bp.route('/')
@main_bp.route('/index')
def home():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
        
    user=current_user
    return render_template('welcome.html', title='Inicio', user=user)