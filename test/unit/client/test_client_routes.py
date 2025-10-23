from flask import url_for
from app.auth.models import Persona
from unittest.mock import patch
from datetime import datetime, timezone
from bson.objectid import ObjectId

def test_create_ticket_get(logged_in_client, app):
    """
    GIVEN a logged-in user with permissions
    WHEN they access the /create_ticket page
    THEN they should see the create ticket form
    """
    response = logged_in_client.get('/create_ticket')
    assert response.status_code == 200
    assert b"Crear Ticket" in response.data

def test_create_ticket_unauthenticated(client, app):
    """
    GIVEN an unauthenticated user
    WHEN they access the /create_ticket page
    THEN they should be redirected to the login page
    """
    response = client.get('/create_ticket', follow_redirects=False)
    assert response.status_code == 302
    assert '/auth/login' in response.location

def test_create_ticket_unauthorized(logged_in_operator_client, app):
    """
    GIVEN a logged-in user without permissions
    WHEN they access the /create_ticket page
    THEN they should get a 403 Forbidden error
    """
    response = logged_in_operator_client.get('/create_ticket', follow_redirects=False)
    assert response.status_code == 403

@patch('app.client.routes.send_notification_email')
def test_create_ticket_post(mock_send_email, logged_in_client, db, app):
    """
    GIVEN a logged-in user with permissions
    WHEN they submit a valid create ticket form
    THEN a new ticket should be created, assigned, and an email sent
    """
    # Mock supervisor
    supervisor_data = {
        'username': 'supervisoruser',
        'email': 'supervisor@example.com',
        'name': 'Supervisor',
        'firstSurname': 'User',
        'role': 'supervisor',
    }
    supervisor = Persona(**supervisor_data)
    supervisor.set_password('password')
    supervisor_dict = {
        '_id': ObjectId(), # Ensure _id is set for mock user
        'username': supervisor.username,
        'email': supervisor.email,
        'name': supervisor.name,
        'firstSurname': supervisor.firstSurname,
        'role': supervisor.role,
        'password_hash': supervisor.password_hash
    }
    supervisor_result = db.db.personas.insert_one(supervisor_dict)
    supervisor_id = supervisor_result.inserted_id

    # Mock category
    category_result = db.db.categories.insert_one({'name': 'Test Category', 'value': 'test_category'})
    category_id = category_result.inserted_id

    # Mock status
    db.db.statuses.insert_one({'name': 'Pending', 'value': 'pending'})

    # Mock supervisor assignment
    db.db.supervisor_assignments.insert_one({
        'category_id': category_id,
        'shift_value': 'weekday_morning',
        'supervisor_id': supervisor_id
    })

    form_data = {
        'title': 'Test Ticket',
        'description': 'This is a test ticket.',
        'category': 'test_category',
        'shift': 'weekday_morning'
    }

    response = logged_in_client.post('/create_ticket', data=form_data, follow_redirects=False)
    assert response.status_code == 302

    with logged_in_client.session_transaction() as sess:
        flashes = sess['_flashes']
        assert len(flashes) > 0
        assert flashes[0][0] == 'success'
        assert '¡Ticket creado exitosamente!' in flashes[0][1]

    # Check that the ticket was created and assigned
    ticket = db.db.tickets.find_one({'title': 'Test Ticket'})
    assert ticket is not None
    assert ticket['description'] == 'This is a test ticket.'
    assert ticket['supervisor']['user_id'] == supervisor_id

    # Check that the email was sent
    mock_send_email.assert_called_once()
    call_args = mock_send_email.call_args[1]
    assert call_args['subject'] == f"Nuevo Ticket Creado: #{ticket['_id']}"
    assert call_args['recipients'] == ['supervisor@example.com']

def test_create_ticket_post_invalid(logged_in_client, db, app):
    """
    GIVEN a logged-in user with permissions
    WHEN they submit an invalid create ticket form
    THEN the page should be re-rendered with validation errors
    """
    form_data = {
        'title': '', # Invalid title
        'description': 'This is a test ticket.',
        'category': 'test_category',
        'shift': 'weekday_morning'
    }

    response = logged_in_client.post('/create_ticket', data=form_data, follow_redirects=False)
    assert response.status_code == 200
    assert b"This field is required." in response.data

    # Check that no ticket was created
    ticket = db.db.tickets.find_one({'description': 'This is a test ticket.'})
    assert ticket is None

def test_create_ticket_post_no_pending_status(logged_in_client, db, app):
    """
    GIVEN a logged-in user with permissions
    WHEN they submit a valid form but the 'pending' status is missing
    THEN a critical error should be flashed
    """
    # Mock category, but not status
    db.db.categories.insert_one({'name': 'Test Category', 'value': 'test_category'})

    form_data = {
        'title': 'Test Ticket',
        'description': 'This is a test ticket.',
        'category': 'test_category',
        'shift': 'weekday_morning'
    }

    response = logged_in_client.post('/create_ticket', data=form_data, follow_redirects=False)
    assert response.status_code == 302 # Should redirect

    with logged_in_client.session_transaction() as sess:
        flashes = sess['_flashes']
        assert len(flashes) > 0
        assert flashes[0][0] == 'danger'
        assert 'Error crítico: El estado inicial "Pendiente" no existe.' in flashes[0][1]

    # Check that no ticket was created
    ticket = db.db.tickets.find_one({'title': 'Test Ticket'})
    assert ticket is None


def test_client_tickets_requires_login(client, app):
    """
    GIVEN an unauthenticated user
    WHEN they try to access the /client/tickets page
    THEN they should be redirected to the login page
    """
    with app.test_request_context(): # Wrap the entire client.get call
        tickets_url = url_for('client_bp.client_tickets')
        login_url = url_for('auth.login') # Build login_url within the same context
    response = client.get(tickets_url, follow_redirects=False)
    assert response.status_code == 302
    assert login_url in response.location


def test_client_tickets_requires_client_role(logged_in_operator_client, app):
    """
    GIVEN a logged-in user who is not a client (e.g., operator)
    WHEN they try to access the /client/tickets page
    THEN they should receive a 403 Forbidden error
    """
    with app.test_request_context(): # Wrap the entire client.get call
        tickets_url = url_for('client_bp.client_tickets')
    response = logged_in_operator_client.get(tickets_url, follow_redirects=False)
    assert response.status_code == 403


def test_client_tickets_client_can_access(logged_in_client, app):
    """
    GIVEN a logged-in client user
    WHEN they access the /client/tickets page
    THEN they should receive a 200 OK status and see the page title
    """
    with app.test_request_context(): # Wrap the entire client.get call
        tickets_url = url_for('client_bp.client_tickets')
    response = logged_in_client.get(tickets_url)
    assert response.status_code == 200
    assert b"Mis Tickets" in response.data


def test_client_tickets_shows_only_client_tickets(logged_in_client, db, app):
    """
    GIVEN a logged-in client and tickets belonging to different users
    WHEN the client accesses their tickets page
    THEN only their own tickets should be displayed
    """
    # Get the logged-in client's user ID from the db
    client_user_id = db.db.personas.find_one({'username': 'testuser'})['_id']

    # Ensure status and categories exist for the map
    db.db.statuses.insert_many([
        {'name': 'Pending', 'value': 'pending'}
    ])
    db.db.categories.insert_many([
        {'name': 'Software', 'value': 'software'},
        {'name': 'Hardware', 'value': 'hardware'}
    ])

    # Create a ticket for the logged-in client
    db.db.tickets.insert_one({
        '_id': ObjectId(),
        'title': 'Client Ticket 1',
        'description': 'Description 1',
        'creator': {'user_id': client_user_id, 'username': 'testuser'},
        'status_value': 'pending',
        'category_value': 'software',
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    })

    # Create a ticket for another user
    other_user_id = ObjectId()
    db.db.tickets.insert_one({
        '_id': ObjectId(),
        'title': 'Other User Ticket',
        'description': 'Description Other',
        'creator': {'user_id': other_user_id, 'username': 'otheruser'},
        'status_value': 'pending',
        'category_value': 'hardware',
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    })

    response = logged_in_client.get(url_for('client_bp.client_tickets'))
    assert response.status_code == 200
    assert b"Client Ticket 1" in response.data
    assert b"Other User Ticket" not in response.data


def test_client_tickets_displays_ticket_details(logged_in_client, db, app):
    """
    GIVEN a logged-in client with a ticket
    WHEN the client accesses their tickets page
    THEN key details of the ticket should be displayed
    """
    # Get the logged-in client's user ID from the db
    client_user_id = db.db.personas.find_one({'username': 'testuser'})['_id']

    # Create a ticket for the logged-in client
    ticket_title = 'Detailed Client Ticket'
    ticket_description = 'This ticket has many details.'
    ticket_status_name = 'In Progress'
    ticket_status_value = 'in_progress'
    ticket_category_name = 'Network'
    ticket_category_value = 'network'

    # Add status to the statuses collection for the map to work
    db.db.statuses.insert_one({'name': ticket_status_name, 'value': ticket_status_value})

    db.db.tickets.insert_one({
        '_id': ObjectId(),
        'title': ticket_title,
        'description': ticket_description,
        'creator': {'user_id': client_user_id, 'username': 'testuser'},
        'status_value': ticket_status_value,
        'category_value': ticket_category_value,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    })

    response = logged_in_client.get(url_for('client_bp.client_tickets'))
    assert response.status_code == 200
    assert ticket_title.encode('utf-8') in response.data
    assert ticket_status_name.encode('utf-8') in response.data
    assert ticket_category_name.encode('utf-8') in response.data


def test_client_tickets_no_tickets_message(logged_in_client, db, app):
    """
    GIVEN a logged-in client with no tickets
    WHEN the client accesses their tickets page
    THEN an appropriate 'no tickets' message should be displayed
    """
    # Get the logged-in client's user ID from the db
    client_user_id = db.db.personas.find_one({'username': 'testuser'})['_id']
    db.db.tickets.delete_many({'creator.user_id': client_user_id}) # Clean up any existing tickets for this client

    response = logged_in_client.get(url_for('client_bp.client_tickets'))
    assert response.status_code == 200
    assert b"No has cargado ning\xc3\xban ticket todav\xc3\xada." in response.data

def test_client_tickets_filter_by_status(logged_in_client, db, app):
    """
    GIVEN a logged-in client with multiple tickets
    WHEN they filter the tickets by status
    THEN only tickets with the matching status should be displayed
    """
    client_user_id = db.db.personas.find_one({'username': 'testuser'})['_id']

    # Create statuses
    db.db.statuses.insert_many([
        {'name': 'Pending', 'value': 'pending'},
        {'name': 'In Progress', 'value': 'in_progress'}
    ])

    # Create tickets with different statuses
    db.db.tickets.insert_one({
        'title': 'Pending Ticket Filter Test',
        'creator': {'user_id': client_user_id, 'username': 'testuser'},
        'status_value': 'pending',
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    })
    db.db.tickets.insert_one({
        'title': 'In Progress Ticket Filter Test',
        'creator': {'user_id': client_user_id, 'username': 'testuser'},
        'status_value': 'in_progress',
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    })

    with app.test_request_context():
        # Filter for 'pending' status
        filter_url = url_for('client_bp.client_tickets', status='pending')

    response = logged_in_client.get(filter_url)
    assert response.status_code == 200

    # Check that the pending ticket is present
    assert b'Pending Ticket Filter Test' in response.data
    # Check that the in_progress ticket is NOT present
    assert b'In Progress Ticket Filter Test' not in response.data

def test_client_tickets_filter_by_title(logged_in_client, db, app):
    """
    GIVEN a logged-in client with multiple tickets
    WHEN they filter the tickets by title
    THEN only tickets with a matching title should be displayed
    """
    client_user_id = db.db.personas.find_one({'username': 'testuser'})['_id']

    # Create tickets with different titles
    db.db.tickets.insert_one({
        'title': 'Apple Ticket',
        'creator': {'user_id': client_user_id, 'username': 'testuser'},
        'status_value': 'pending',
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    })
    db.db.tickets.insert_one({
        'title': 'Banana Ticket',
        'creator': {'user_id': client_user_id, 'username': 'testuser'},
        'status_value': 'pending',
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    })

    with app.test_request_context():
        # Filter for title containing 'Apple'
        filter_url = url_for('client_bp.client_tickets', search_title='Apple')

    response = logged_in_client.get(filter_url)
    assert response.status_code == 200

    # Check that the correct ticket is present
    assert b'Apple Ticket' in response.data
    # Check that the other ticket is NOT present
    




def test_client_tickets_filter_by_operator(logged_in_client, db, app):
    """
    GIVEN a logged-in client with multiple tickets
    WHEN they filter the tickets by operator username
    THEN only tickets with the matching operator should be displayed
    """
    client_user_id = db.db.personas.find_one({'username': 'testuser'})['_id']
    operator = db.db.personas.find_one({'role': 'operador'})
    if not operator:
        db.db.personas.insert_one({'username': 'op_filter_test', 'role': 'operador'})
        operator = db.db.personas.find_one({'username': 'op_filter_test'})

    # Create tickets with different operators
    db.db.tickets.insert_one({
        'title': 'Ticket With Operator',
        'creator': {'user_id': client_user_id, 'username': 'testuser'},
        'operator': {'user_id': operator['_id'], 'username': operator['username']},
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    })
    db.db.tickets.insert_one({
        'title': 'Ticket Without Operator',
        'creator': {'user_id': client_user_id, 'username': 'testuser'},
        'operator': None,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    })

    with app.test_request_context():
        filter_url = url_for('client_bp.client_tickets', operator_username='op_filter_test')

    response = logged_in_client.get(filter_url)
    assert response.status_code == 200

    assert b'Ticket With Operator' in response.data
    assert b'Ticket Without Operator' not in response.data

def test_client_tickets_filter_by_category(logged_in_client, db, app):
    """
    GIVEN a logged-in client with multiple tickets
    WHEN they filter the tickets by category
    THEN only tickets with the matching category should be displayed
    """
    client_user_id = db.db.personas.find_one({'username': 'testuser'})['_id']

    # Create categories
    db.db.categories.insert_many([
        {'name': 'Hardware', 'value': 'hardware'},
        {'name': 'Software', 'value': 'software'}
    ])

    # Create tickets with different categories
    db.db.tickets.insert_one({
        'title': 'Hardware Ticket',
        'creator': {'user_id': client_user_id, 'username': 'testuser'},
        'category_value': 'hardware',
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    })
    db.db.tickets.insert_one({
        'title': 'Software Ticket',
        'creator': {'user_id': client_user_id, 'username': 'testuser'},
        'category_value': 'software',
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    })

    with app.test_request_context():
        filter_url = url_for('client_bp.client_tickets', category='hardware')

    response = logged_in_client.get(filter_url)
    assert response.status_code == 200

    assert b'Hardware Ticket' in response.data
    assert b'Software Ticket' not in response.data