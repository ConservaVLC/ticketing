from flask import Blueprint

client_bp = Blueprint(
    'client_bp', __name__, 
    template_folder='app/templates/client',
    static_folder='static'
)
from . import routes