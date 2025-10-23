import pytest
from app import create_app, mongo
from app.auth.models import Persona
from flask import url_for
from werkzeug.security import generate_password_hash
from unittest.mock import patch
import logging
from datetime import datetime
import mongomock

# Desactivar la propagación de logs para evitar duplicados en la consola de pytest
logging.getLogger("werkzeug").setLevel(logging.ERROR)
logging.getLogger("flask_limiter").setLevel(logging.ERROR)


@pytest.fixture(scope="function")
def app():
    """Crea y configura una instancia de la aplicación Flask para cada test."""
    with patch('pymongo.MongoClient', mongomock.MongoClient):
        app = create_app('testing')
        app.config['SERVER_NAME'] = 'test.com'
        yield app


@pytest.fixture(scope="function")
def client(app):
    """Cliente de prueba simple para la aplicación Flask."""
    return app.test_client()


@pytest.fixture
def logged_in_client(client, db, seed_test_user):
    """
    Cliente de prueba que ya ha iniciado sesión con el usuario de prueba (rol: cliente),
    completando el flujo 2FA.
    """
    user_data, _ = seed_test_user
    login(client, db, user_data)
    return client


@pytest.fixture
def logged_in_operator_client(client, db, seed_test_operator):
    """
    Cliente de prueba que ya ha iniciado sesión con un usuario operador,
    completando el flujo 2FA.
    """
    operator_data, _ = seed_test_operator
    login(client, db, operator_data)
    return client


@pytest.fixture
def authenticated_admin_client(client, db, seed_test_admin):
    """
    Cliente de prueba que ya ha iniciado sesión con el usuario administrador,
    completando el flujo 2FA.
    """
    admin_data, _ = seed_test_admin
    login(client, db, admin_data)
    return client


@pytest.fixture(scope="function")
def db(app):
    """Fixture que proporciona acceso a la BD y la limpia antes de cada test."""
    with app.app_context():
        mongo.db.client.drop_database(mongo.db.name)
        yield mongo


@pytest.fixture(scope="function")
def seed_test_user(db):
    """Crea un usuario de prueba (rol: cliente) en la base de datos para los tests."""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "name": "Test",
        "firstSurname": "User",
        "role": "cliente",
        "password_hash": generate_password_hash("ThisIsA-Valid-Password123!"),
        "password_changed_at": datetime.utcnow(),
    }
    result = db.db.personas.insert_one(user_data)
    user_data["_id"] = result.inserted_id
    user_obj = Persona(**user_data)
    yield user_data, user_obj


@pytest.fixture(scope="function")
def seed_test_operator(db):
    """Crea un usuario de prueba (rol: operador) en la base de datos para los tests."""
    operator_data = {
        "username": "operatoruser",
        "email": "operator@example.com",
        "name": "Operator",
        "firstSurname": "User",
        "role": "operador",
        "password_hash": generate_password_hash("ThisIsA-Valid-Password123!"),
        "password_changed_at": datetime.utcnow(),
    }
    result = db.db.personas.insert_one(operator_data)
    operator_data["_id"] = result.inserted_id
    operator_obj = Persona(**operator_data)
    yield operator_data, operator_obj


@pytest.fixture(scope="function")
def seed_test_admin(db):
    """Crea un usuario administrador de prueba."""
    admin_data = {
        "username": "admin",
        "email": "admin@example.com",
        "name": "Admin",
        "firstSurname": "User",
        "role": "admin",
        "password_changed_at": datetime.utcnow(),
        "password_hash": generate_password_hash("ThisIsA-Valid-Password123!"),
    }
    result = db.db.personas.insert_one(admin_data)
    admin_data["_id"] = result.inserted_id
    admin_obj = Persona(**admin_data)
    yield admin_data, admin_obj


def login(client, db, user_data):
    """Función de ayuda para iniciar sesión con un usuario en los tests, completando el flujo 2FA."""
    with patch("app.auth.routes.send_2fa_code_email"):
        # Paso 1: Iniciar sesión para generar el código 2FA
        client.post(
            url_for("auth.login"),
            data={
                "username": user_data["username"],
                "password": "ThisIsA-Valid-Password123!",
            },
            follow_redirects=True,
        )

        # Paso 2: Obtener el código de la BD
        user_from_db = db.db.personas.find_one({"_id": user_data["_id"]})
        code = user_from_db["two_factor_code"]

        # Paso 3: Verificar con el código 2FA
        client.post(
            url_for("auth.verify_2fa"),
            data={"code": code},
            follow_redirects=True,
        )