# app/main/routes.py
from flask import render_template, redirect, url_for
from flask_login import current_user
from app.main import main_bp # Importa el Blueprint que acabas de crear

@main_bp.route('/')
@main_bp.route('/index')
def home():
    return "<h1>Welcome to the Ticketing App!</h1>"