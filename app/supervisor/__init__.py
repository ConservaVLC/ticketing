from flask import Blueprint

supervisor_bp = Blueprint(
    'supervisor_bp', __name__, 
    template_folder='app/templates/supervisor',
    static_folder='static'
)
from . import routes