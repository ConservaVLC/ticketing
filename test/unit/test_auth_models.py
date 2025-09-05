from app.auth.models import Persona, Role
import time

# Nota: No es necesario importar db, app, etc. Pytest los inyecta a través de las fixtures.

def test_password_hashing(seeded_db):
    """
    Prueba que la contraseña se guarda hasheada y no en texto plano.
    """
    admin_user = seeded_db['admin']
    password = 'mysecretpassword'
    admin_user.set_password(password)
    
    assert admin_user.password_hash is not None
    assert admin_user.password_hash != password

def test_password_verification(seeded_db):
    """
    Prueba que check_password() funciona correctamente.
    """
    client_user = seeded_db['client']
    password = 'supersecret'
    client_user.set_password(password)
    
    assert client_user.check_password(password) is True
    assert client_user.check_password('wrongpassword') is False

def test_password_reset_token(seeded_db):
    """
    Prueba la generación y verificación de tokens para el reseteo de contraseña.
    """
    admin_user = seeded_db['admin']
    token = admin_user.get_reset_password_token()
    assert isinstance(token, str)
    
    # Verificar que el token es válido para el usuario correcto
    verified_user = Persona.verify_reset_password_token(token)
    assert verified_user is not None
    assert verified_user.id == admin_user.id

def test_invalid_password_reset_token(db):
    """
    Prueba que un token inválido o manipulado no funciona.
    """
    invalid_token = 'untokencompletamenteinvalido'
    verified_user = Persona.verify_reset_password_token(invalid_token)
    assert verified_user is None

def test_expired_password_reset_token(seeded_db):
    """
    Prueba que un token expira y no puede ser verificado.
    """
    client_user = seeded_db['client']
    # Generamos un token
    token = client_user.get_reset_password_token()
    
    # Esperamos 2 segundos para que el token expire
    time.sleep(2)
    
    # Verificamos el token con una expiración de 1 segundo. Debería fallar.
    verified_user = Persona.verify_reset_password_token(token, expires_in=1)
    assert verified_user is None

def test_role_properties(seeded_db):
    """
    Prueba las propiedades booleanas de rol (is_admin, is_client, etc.).
    """
    admin_user = seeded_db['admin']
    client_user = seeded_db['client']

    assert admin_user.is_admin is True
    assert admin_user.is_client is False
    
    assert client_user.is_client is True
    assert client_user.is_admin is False

def test_user_representation(seeded_db):
    """
    Prueba el método __repr__ para una representación clara del objeto.
    """
    admin_user = seeded_db['admin']
    expected_repr = f"<Persona {admin_user.name} {admin_user.firstSurname} (Posición: {admin_user.role_obj.value})>"
    assert repr(admin_user) == expected_repr

def test_role_representation(seeded_db):
    """
    Prueba el método __repr__ del modelo Role.
    """
    # seeded_db ya ha creado los roles, así que ahora la consulta funcionará
    admin_role = Role.query.filter_by(value='admin').first()
    expected_repr = f"<Role '{admin_role.name}'>"
    assert repr(admin_role) == expected_repr