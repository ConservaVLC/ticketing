from flask import Blueprint

operator_bp = Blueprint(
    'operator_bp', __name__, 
    #template_folder='app/templates/operator',
    static_folder='static'
)
