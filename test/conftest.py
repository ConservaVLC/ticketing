import pytest
from app import create_app, mongo
from app.auth.models import Persona
from unittest.mock import patch
import mongomock
from bson.objectid import ObjectId

@pytest.fixture(scope='module')
def app():
    """Create and configure a new app instance for each test module."""
    with patch('pymongo.MongoClient', mongomock.MongoClient):
        app = create_app('testing')
        app.config['SERVER_NAME'] = 'test.com' # Set SERVER_NAME for testing
        yield app

@pytest.fixture(scope='module')
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='function')
def db(app):
    """A fixture to provide a clean database for each test function."""
    with app.app_context():
        mongo.db.client.drop_database(mongo.db.name)
        yield mongo.db

@pytest.fixture
def logged_in_client(client, db):
    """A client logged in as a test user with 'cliente' role."""
    # Create a user and save it to the mock database
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'name': 'Test',
        'firstSurname': 'User',
        'role': 'cliente',
    }
    user = Persona(**user_data)
    user.set_password('password')
    
    user_dict = {
        '_id': ObjectId(),
        'username': user.username,
        'email': user.email,
        'name': user.name,
        'firstSurname': user.firstSurname,
        'role': user.role,
        'password_hash': user.password_hash
    }
    
    db.personas.insert_one(user_dict)

    # Log the user in
    client.post('/auth/login', data={
        'username': 'test@example.com',
        'password': 'password'
    }, follow_redirects=True)

    yield client

    # Clean up
    db.personas.delete_one({'email': 'test@example.com'})
    client.get('/auth/logout', follow_redirects=True)

@pytest.fixture
def logged_in_operator_client(client, db):
    """
    A client logged in as a test user with 'operador' role.
    This user does not have permissions to create tickets.
    """
    # Create a user and save it to the mock database
    user_data = {
        'username': 'operatoruser',
        'email': 'operator@example.com',
        'name': 'Operator',
        'firstSurname': 'User',
        'role': 'operador',
    }
    user = Persona(**user_data)
    user.set_password('password')
    
    user_dict = {
        '_id': ObjectId(),
        'username': user.username,
        'email': user.email,
        'name': user.name,
        'firstSurname': user.firstSurname,
        'role': user.role,
        'password_hash': user.password_hash
    }
    
    db.personas.insert_one(user_dict)

    # Log the user in
    client.post('/auth/login', data={
        'username': 'operator@example.com',
        'password': 'password'
    }, follow_redirects=True)

    yield client

    # Clean up
    db.personas.delete_one({'email': 'operator@example.com'})
    client.get('/auth/logout', follow_redirects=True)
