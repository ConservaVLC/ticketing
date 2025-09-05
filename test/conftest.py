import pytest
from app import create_app, db as _db
from app.auth.models import Role, Persona

@pytest.fixture(scope='session')
def app():
    """Crea una instancia de la aplicación Flask para toda la sesión de pruebas."""
    return create_app('testing')

@pytest.fixture(scope='function')
def db(app):
    """
    Crea las tablas de la base de datos antes de cada prueba y las elimina después.
    """
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    """Un cliente de prueba para hacer peticiones a la aplicación."""
    return app.test_client()

@pytest.fixture(scope='function')
def seeded_db(db):
    """
    Una fixture que inicializa la base de datos con datos de prueba (roles y usuarios).
    Devuelve un diccionario con los usuarios creados para fácil acceso en los tests.
    """
    # Crear roles
    admin_role = Role(name='Admin', value='admin')
    client_role = Role(name='Cliente', value='cliente')
    db.session.add_all([admin_role, client_role])
    db.session.commit()

    # Crear usuarios
    admin_user = Persona(
        username='adminuser', 
        email='admin@test.com', 
        name='Admin', 
        firstSurname='Test',
        role_id=admin_role.id
    )
    client_user = Persona(
        username='clientuser', 
        email='client@test.com', 
        name='Client', 
        firstSurname='Test',
        role_id=client_role.id
    )
    db.session.add_all([admin_user, client_user])
    db.session.commit()
    
    return {
        'admin': admin_user,
        'client': client_user
    }
