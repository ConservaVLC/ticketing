# app/__init__.py

from flask import Flask, render_template, current_app
from flask_login import LoginManager
from flask_mail import Mail
from flask_pymongo import PyMongo
from flask_wtf.csrf import CSRFProtect
from pymongo.errors import ConnectionFailure, ConfigurationError
import logging
from logging.handlers import RotatingFileHandler
from config import DevelopmentConfig, ProductionConfig, TestingConfig
import os
import sys

# --- Instancias de Extensiones ---
login_manager = LoginManager()
mail = Mail()
mongo = PyMongo()
csrf = CSRFProtect()


# --- Funciones Auxiliares para Modularizar la Configuración ---

def init_app_extensions(app):
    """
    Inicializa las extensiones de Flask y configura la conexión a la BD.
    """
    mail.init_app(app)
    csrf.init_app(app)

    mongo_uri = app.config.get("MONGO_URI")
    if not mongo_uri:
        raise RuntimeError("FATAL: La variable de entorno MONGO_URI no está configurada.")

    app.logger.info("Intentando conectar a MongoDB...")

    try:
        mongo.init_app(app)
        mongo.cx.server_info() # Fuerza la conexión para verificarla
        app.logger.info("Conexión a MongoDB establecida exitosamente.")
    except (ConnectionFailure, ConfigurationError) as e:
        app.logger.error(f"Error al conectar o configurar MongoDB: {e}")
        raise RuntimeError(f"No se pudo conectar a la base de datos: {e}")

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Por favor, inicia sesión para acceder a esta página."
    login_manager.login_message_category = "warning"

    from app.auth.models import Persona
    from bson.objectid import ObjectId

    @login_manager.user_loader
    def load_user(user_id):
        try:
            user_data = mongo.db.personas.find_one({"_id": ObjectId(user_id)})
            if user_data:
                return Persona(**user_data)
        except Exception as e:
            app.logger.error(f"Error en load_user para user_id {user_id}: {e}")
        return None

def register_app_blueprints(app):
    """
    Registra todos los Blueprints de la aplicación.
    """
    from app.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import main_bp
    app.register_blueprint(main_bp)

    from app.client import client_bp
    app.register_blueprint(client_bp)

    from app.operator import operator_bp
    app.register_blueprint(operator_bp)

    from app.admin import admin_bp
    app.register_blueprint(admin_bp)

    from app.supervisor import supervisor_bp
    app.register_blueprint(supervisor_bp)

def configure_app_logging(app):
    """
    Configura el sistema de logging de la aplicación.
    """
    if not os.path.exists("logs"):
        os.mkdir("logs")

    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)

    file_handler = RotatingFileHandler("logs/app.log", maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))

    if not app.debug and not app.testing:
        file_handler.setLevel(logging.INFO)
        stream_handler.setLevel(logging.INFO)
        app.logger.setLevel(logging.INFO)
    else:
        file_handler.setLevel(logging.DEBUG)
        stream_handler.setLevel(logging.DEBUG)
        app.logger.setLevel(logging.DEBUG)

    app.logger.addHandler(file_handler)
    app.logger.addHandler(stream_handler)
    app.logger.info("Logging inicializado")

def register_app_error_handlers(app):
    """
    Registra los manejadores de errores HTTP globales.
    """
    @app.errorhandler(400)
    def bad_request_error(error):
        return render_template("errors/400.html"), 400

    @app.errorhandler(403)
    def forbidden_access(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def page_not_found_error(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        current_app.logger.error(f"Internal Server Error: {error}", exc_info=True)
        return render_template("errors/500.html"), 500

# --- Función de Fábrica de Aplicación (create_app) ---
def create_app(config_class="development"):
    """
    Función de fábrica para crear y configurar la instancia de la aplicación Flask.
    """
    app = Flask(__name__)

    config_map = {
        'testing': TestingConfig,
        'production': ProductionConfig,
        'development': DevelopmentConfig
    }
    app.config.from_object(config_map.get(config_class, DevelopmentConfig))

    configure_app_logging(app)
    init_app_extensions(app)
    register_app_blueprints(app)
    register_app_error_handlers(app)

    from app import commands as commands
    app.cli.add_command(commands.init_db_data_command)

    return app
