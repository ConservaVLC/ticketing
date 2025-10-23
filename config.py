# config.py

import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()


class Config:
    """
    Clase de configuración base.
    Las variables críticas no tienen valor por defecto para forzar su definición
    en los entornos, lo cual es una práctica de seguridad recomendada.
    """
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # Duración de la cookie "Recuérdame"
    REMEMBER_COOKIE_DURATION = timedelta(hours=8)

    # Configuración de Correo Electrónico para Flask-Mail
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 587)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True") == "True"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")
    ADMINS = os.environ.get("ADMIN_EMAILS", "").split(",")

    # Configuración de MongoDB
    # Flask-PyMongo espera la URI en la variable 'MONGO_URI'
    MONGO_URI = os.environ.get("MONGO_URI")


class DevelopmentConfig(Config):
    """Configuración para el entorno de desarrollo."""
    DEBUG = True
    # En desarrollo, si MONGO_URI no está definida, usamos una por defecto
    # que apunta al contenedor de Docker.
    MONGO_URI = (
        os.environ.get("MONGO_URI") or "mongodb://user:password_secret@mongo:27017/ticketing_db?authSource=admin"
    )


class ProductionConfig(Config):
    """Configuración para el entorno de producción."""
    DEBUG = False
    # En producción, MONGO_URI DEBE ser definida como una variable de entorno.


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key"
    WTF_CSRF_ENABLED = False
    MONGO_URI = (
        os.environ.get("TEST_MONGO_URI")
        or "mongodb://localhost:27017/registro_horas_test"
    )