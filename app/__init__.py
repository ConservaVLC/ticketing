# app/__init__.py

from flask import Flask, render_template, current_app, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
import logging
from logging.handlers import RotatingFileHandler
from config import DevelopmentConfig, ProductionConfig, TestingConfig
import os

# Importa las clases de configuración de la aplicación
from config import DevelopmentConfig, ProductionConfig

# --- Instancias de Extensiones ---
# Se inicializan aquí para que puedan ser importadas y usadas en otros módulos
# (ej. 'db' en los modelos, 'login_manager' para el user_loader).
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()


# --- Funciones Auxiliares para Modularizar la Configuración ---

def init_app_extensions(app):
    """
    Inicializa las extensiones de Flask (Mail, SQLAlchemy, Migrate, LoginManager)
    con la instancia de la aplicación.
    También configura el user_loader para Flask-Login.
    """
    mail.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página.'
    login_manager.login_message_category = 'warning'

    # Flask-Login: user_loader para cargar el usuario desde la base de datos
    # Se importa aquí para evitar posibles importaciones circulares.
    from app.auth.models import Persona
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Persona, int(user_id))
    
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
    Configura el sistema de logging de la aplicación,
    incluyendo la escritura de logs a un archivo en entornos de producción y desarrollo.
    """
    # Asegúrate de que el directorio de logs exista
    if not os.path.exists('logs'):
        os.mkdir('logs')

    # Elimina cualquier handler existente para evitar duplicados si la función se llama varias veces
    # Esto es una buena práctica, especialmente en testing
    for handler in app.logger.handlers:
        app.logger.removeHandler(handler)

    # Configura el manejador de archivo rotatorio
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=1024 * 1024 * 5, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Determina el nivel de log para el manejador de archivo y el logger de la aplicación
    if not app.debug and not app.testing:
        # Modo Producción: logs INFO y superiores al archivo
        file_handler.setLevel(logging.INFO)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Aplicación iniciada en modo producción (logs a archivo).')
    else:
        # Modo Desarrollo / Testing: logs DEBUG y superiores al archivo
        file_handler.setLevel(logging.DEBUG)
        app.logger.setLevel(logging.DEBUG)
        app.logger.debug('Aplicación iniciada en modo desarrollo (logs a archivo).')

    # Añade el manejador de archivo al logger de la aplicación
    app.logger.addHandler(file_handler)



def register_app_error_handlers(app):
    """
    Registra los manejadores de errores HTTP globales de la aplicación
    para proporcionar páginas de error personalizadas.
    """
    @app.errorhandler(400)
    def bad_request_error(error):
        return render_template('errors/400.html'), 400

    @app.errorhandler(403)
    def forbidden_access(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        # Asegura un rollback de la sesión de base de datos en caso de error 500
        db.session.rollback() 
        current_app.logger.error(f"Internal Server Error: {error}")
        return render_template('errors/500.html'), 500


# --- Función de Fábrica de Aplicación (create_app) ---

def create_app(config_class='development'):
    """
    Función de fábrica para crear y configurar la instancia de la aplicación Flask.
    Usa el patrón de fábrica para permitir múltiples instancias de la aplicación
    (ej. para testing o diferentes entornos).
    """
    app = Flask(__name__)
    
    # Cargar la configuración según el entorno
    if config_class == 'testing':
        app.config.from_object(TestingConfig)
    elif config_class == 'production':
        app.config.from_object(ProductionConfig)
    else: # Default a 'development'
        app.config.from_object(DevelopmentConfig)

    # Llama a las funciones auxiliares para inicializar y configurar la aplicación
    init_app_extensions(app)
    register_app_blueprints(app)
    configure_app_logging(app)
    register_app_error_handlers(app)
    
    from app import commands as commands
    app.cli.add_command(commands.init_db_data_command)

    return app