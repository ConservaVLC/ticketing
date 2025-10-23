from flask import url_for
from flask_login import current_user
from unittest.mock import patch
from test.conftest import login
from datetime import datetime, timedelta
import pytest

# Las fixtures (app, client, db, seed_test_user, seed_test_admin) y la funciÃ³n de ayuda (login)
# son proporcionadas automÃ¡ticamente por conftest.py


@patch("app.auth.routes.send_2fa_code_email")
def test_login_2fa_and_logout(mock_send_2fa_email, client, db, seed_test_user, app):
    """Test que un usuario puede iniciar sesión con 2FA y cerrar sesión."""
    with app.test_request_context():
        # 1. Intento de login
        login_response = client.post(
            url_for("auth.login"),
            data={"username": "testuser", "password": "ThisIsA-Valid-Password123!"},
            follow_redirects=True,
        )
        assert login_response.status_code == 200
        assert (
            b"Se ha enviado un c\xc3\xb3digo de verificaci\xc3\xb3n a tu correo."
            in login_response.data
        )
        assert not current_user.is_authenticated
        mock_send_2fa_email.assert_called_once()

        # 2. Obtener el código 2FA de la base de datos
        user_data, _ = seed_test_user
        user_from_db = db.db.personas.find_one({"_id": user_data["_id"]})
        assert user_from_db is not None
        code = user_from_db["two_factor_code"]
        assert code is not None

        # 3. Verificar con el código 2FA
        with client.session_transaction() as session:
            assert session.get("2fa_user_id") == str(user_data["_id"])

        verify_response = client.post(
            url_for("auth.verify_2fa"),
            data={"code": code},
            follow_redirects=True,
        )
        assert verify_response.status_code == 200
        assert b"\xc2\xa1Bienvenido de nuevo!" in verify_response.data
        assert current_user.is_authenticated

        # 4. Logout
        logout_response = client.get(url_for("auth.logout"), follow_redirects=True)
        assert logout_response.status_code == 200
        assert b"Has cerrado sesi\xc3\xb3n correctamente." in logout_response.data
        assert not current_user.is_authenticated


def test_login_with_invalid_2fa_code(client, seed_test_user, app):
    """Test que el login falla con un código 2FA incorrecto."""
    with app.test_request_context():
        # 1. Intento de login para generar el código 2FA
        client.post(
            url_for("auth.login"),
            data={"username": "testuser", "password": "ThisIsA-Valid-Password123!"},
            follow_redirects=True,
        )

        # 2. Intentar verificar con un código incorrecto
        verify_response = client.post(
            url_for("auth.verify_2fa"),
            data={"code": "000000"},  # Código incorrecto
            follow_redirects=True,
        )
        assert verify_response.status_code == 200
        assert b"C\xc3\xb3digo incorrecto o expirado." in verify_response.data
        assert not current_user.is_authenticated


def test_login_with_expired_2fa_code(client, db, seed_test_user, app):
    """Test que el login falla con un código 2FA expirado."""
    with app.test_request_context():
        # 1. Intento de login para generar el código 2FA
        client.post(
            url_for("auth.login"),
            data={"username": "testuser", "password": "ThisIsA-Valid-Password123!"},
            follow_redirects=True,
        )

        # 2. Envejecer el código en la base de datos
        user_data, _ = seed_test_user
        user_from_db = db.db.personas.find_one({"_id": user_data["_id"]})
        code = user_from_db["two_factor_code"]
        expired_time = datetime.utcnow() - timedelta(minutes=15)
        db.db.personas.update_one(
            {"_id": user_data["_id"]},
            {"$set": {"two_factor_code_expiration": expired_time}},
        )

        # 3. Intentar verificar con el código expirado
        verify_response = client.post(
            url_for("auth.verify_2fa"),
            data={"code": code},
            follow_redirects=True,
        )
        assert verify_response.status_code == 200
        assert b"C\xc3\xb3digo incorrecto o expirado." in verify_response.data
        assert not current_user.is_authenticated


def test_register_page_loads(authenticated_admin_client):
    """Test que la pÃ¡gina de registro carga correctamente."""
    response = authenticated_admin_client.get(url_for("auth.register"))
    assert response.status_code == 200
    assert b"Registrar un usuario" in response.data


def test_register_existing_email(authenticated_admin_client, seed_test_user):
    """Test que el registro falla si el email ya existe."""
    form_data = {
        "username": "anotheruser",
        "email": "test@example.com",  # Email del usuario de prueba ya existente
        "name": "Another",
        "firstSurname": "User",
        "role": "cliente",
        "password": "ThisIsA-Valid-Password123!",
        "password2": "ThisIsA-Valid-Password123!",
    }
    response = authenticated_admin_client.post(url_for("auth.register"), data=form_data)
    assert response.status_code == 200
    assert b"Este correo electr\xc3\xb3nico ya est\xc3\xa1 registrado." in response.data


@pytest.mark.parametrize(
    "password, error_message",
    [
        ("short", "15 caracteres"),
        ("NoNumberPassword!", "un número"),
        ("nouppercasepassword1!", "una letra mayúscula"),
        ("NOLOWERCASEPASSWORD1!", "una letra minúscula"),
        ("NoSymbolPassword123", "un carácter especial"),
    ],
)
def test_password_complexity_failures(
    authenticated_admin_client, password, error_message
):
    """Test que la validación de complejidad de contraseña falla con contraseñas inválidas."""
    form_data = {
        "username": "newuser",
        "email": "new@example.com",
        "name": "New",
        "firstSurname": "User",
        "role": "cliente",
        "password": password,
        "password2": password,
    }
    response = authenticated_admin_client.post(url_for("auth.register"), data=form_data)
    assert response.status_code == 200
    assert error_message.encode("utf-8") in response.data


@patch("app.auth.routes.send_password_reset_email_wrapper")
def test_password_reset_request(mock_send_email, client, seed_test_user):
    """Test que la solicitud de reseteo de contraseña funciona."""
    response = client.post(
        url_for("auth.request_password_reset"),
        data={"email": "test@example.com"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    with client.session_transaction() as session:
        flashes = session.get("_flashes", [])
        assert len(flashes) > 0
        assert "Si tu correo está registrado, recibirás un email con instrucciones." in flashes[0][1]
    mock_send_email.assert_called_once()


def test_password_reset_with_valid_token(client, app, seed_test_user):
    """Test que se puede cambiar la contraseÃ±a con un token vÃ¡lido."""
    with app.app_context():
        user_data, user_obj = seed_test_user
        token = user_obj.get_reset_password_token()

    response = client.post(
        url_for("auth.reset_password", token=token),
        data={
            "password": "ThisIsA-Valid-Password123!",
            "password2": "ThisIsA-Valid-Password123!",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Tu contrase\xc3\xb1a ha sido restablecida" in response.data

    # Verificar con un nuevo login
    response = client.post(
        url_for("auth.login"),
        data={"username": "testuser", "password": "ThisIsA-Valid-Password123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Iniciar Sesi\xc3\xb3n" in response.data


def test_admin_can_access_user_list(authenticated_admin_client):
    """Test que un admin puede acceder a la lista de usuarios."""
    response = authenticated_admin_client.get(url_for("auth.list_users"))
    assert response.status_code == 200
    assert b"Listado de Usuarios" in response.data


def test_user_cannot_access_user_list(logged_in_client):
    """Test que un usuario normal no puede acceder a la lista de usuarios."""
    response = logged_in_client.get(url_for("auth.list_users"))
    assert response.status_code == 403  # Forbidden


def test_password_expired_redirects_to_change_password(client, db, seed_test_user):
    """Test que un usuario con contraseÃ±a expirada es redirigido."""
    user_data, _ = seed_test_user
    # Envejecer la contraseÃ±a del usuario de prueba
    expired_date = datetime.utcnow() - timedelta(days=50)
    db.db.personas.update_one(
        {"_id": user_data["_id"]}, {"$set": {"password_changed_at": expired_date}}
    )

    # Iniciar sesiÃ³n
    login(client, db, user_data)

    # Intentar acceder a una pÃ¡gina protegida (el dashboard principal)
    response = client.get(url_for("main.home"), follow_redirects=False)

    # Verificar la redirecciÃ³n
    assert response.status_code == 302
    assert response.location == url_for("auth.change_password", _external=False)

    # Verificar el mensaje flash
    with client.session_transaction() as session:
        flashes = session.get("_flashes", [])
        assert len(flashes) > 0
        assert "Tu contraseña ha expirado. Por favor, crea una nueva." in flashes[0][1]


def test_password_not_expired_allows_access(logged_in_client, db, seed_test_user):
    """Test que un usuario con contraseÃ±a vÃ¡lida puede acceder a las pÃ¡ginas."""
    user_data, _ = seed_test_user
    # Asegurarse de que la contraseÃ±a es reciente
    recent_date = datetime.utcnow() - timedelta(days=10)
    db.db.personas.update_one(
        {"_id": user_data["_id"]}, {"$set": {"password_changed_at": recent_date}}
    )

    # Intentar acceder a una pÃ¡gina protegida
    response = logged_in_client.get(url_for("main.home"), follow_redirects=True)

    # Verificar que el acceso es exitoso
    assert response.status_code == 200
    assert b"Bienvenido" in response.data  # Asumiendo que el index muestra este texto


def test_legacy_user_forced_to_change_password(client, db, seed_test_user):
    """Test que un usuario sin fecha de cambio de contraseÃ±a es redirigido."""
    user_data, _ = seed_test_user
    # Eliminar el campo `password_changed_at` para simular un usuario antiguo
    db.db.personas.update_one(
        {"_id": user_data["_id"]}, {"$unset": {"password_changed_at": ""}}
    )

    login(client, db, user_data)

    response = client.get(url_for("main.home"), follow_redirects=False)

    assert response.status_code == 302
    assert response.location == url_for("auth.change_password", _external=False)

    with client.session_transaction() as session:
        flashes = session.get("_flashes", [])
        assert len(flashes) > 0
        assert (
            "Por seguridad, debes cambiar tu contraseña para continuar."
            in flashes[0][1]
        )
