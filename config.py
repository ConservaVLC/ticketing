# config.py

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ¡IMPORTANTE! En producción, asegúrate de que SECRET_KEY se cargue desde una variable de entorno segura.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess' # For development only. MUST be set in production!
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}

    # La URL de la base de datos, optimizada para Cloud Run
    # Cloud Run usa un proxy de conexión, por lo que necesita el nombre de conexión de la instancia
    DB_HOST_CLOUDRUN = os.environ.get('DB_HOST_CLOUDRUN')
    
    if DB_HOST_CLOUDRUN:
        SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://{}:{}@localhost/{}?unix_socket=/cloudsql/{}'.format(
            os.environ.get('MYSQL_USER'),
            os.environ.get('MYSQL_PASSWORD'),
            os.environ.get('MYSQL_DATABASE'),
            DB_HOST_CLOUDRUN
        )
    else:
        # Configuración para desarrollo local con Docker Compose
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
            'mysql+pymysql://{}:{}@{}/{}'.format(
                os.environ.get('MYSQL_USER'),
                os.environ.get('MYSQL_PASSWORD'),
                os.environ.get('MYSQL_HOST'),
                os.environ.get('MYSQL_DATABASE')
            )
    
    # El archivo de la base de datos 'app.db' se creará en la raíz de tu proyecto
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Desactiva el seguimiento de modificaciones de objetos de SQLAlchemy

    # --- Configuración de Correo Electrónico para Flask-Mail ---
    MAIL_SERVER = os.environ.get('MAIL_SERVER') # ej. 'smtp.googlemail.com' para Gmail
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587) # 587 para TLS, 465 para SSL
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None # True para la mayoría de servidores
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') # Tu dirección de correo
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') # Tu contraseña de correo o contraseña de aplicación
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    ADMINS = os.environ.get('ADMINS', '').split(',') # Para errores o notificaciones

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    # Podrías añadir configuraciones específicas de producción aquí

class TestingConfig(Config):
    TESTING = True # Esto es clave para Flask
    SERVER_NAME = 'test.com' # Necesario para url_for en tests que requieren contexto de aplicación
    # Usa una base de datos en memoria para los tests para que sean rápidos y no interfieran
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' 
    WTF_CSRF_ENABLED = False # Deshabilita CSRF para tests, ya que es complicado simularlo
    DEBUG = True # Puede ser útil para depurar tests
