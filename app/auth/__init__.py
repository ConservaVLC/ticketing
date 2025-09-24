# app/auth/__init__.py
from flask import Blueprint

auth_bp = Blueprint('auth', __name__, template_folder='templates') # Ojo con la ruta del template si no está directa

