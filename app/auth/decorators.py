# app/auth/decorators.py

from functools import wraps
from flask import abort, flash
from flask_login import current_user, login_required

# Decorador general para requerir uno o varios roles
def role_required(roles):
    """
    Decorador que verifica si el usuario actual tiene alguno de los roles especificados.
    
    Uso:
    @role_required('admin')
    @role_required(['admin', 'supervisor'])
    """
    def decorator(f):
        @wraps(f)
        @login_required # Asegura que el usuario esté logueado antes de comprobar el rol
        def decorated_function(*args, **kwargs):
            # Convertir 'roles' a una lista si se pasó un solo rol como cadena
            if isinstance(roles, str):
                allowed_roles = [roles]
            else:
                allowed_roles = roles
                
            # Verifica si el rol del usuario está en la lista de roles permitidos
            if current_user.role not in allowed_roles:
                flash(f'No tienes permiso para acceder a esta página. Tu rol es "{current_user.role}".', 'danger')
                abort(403) # HTTP 403 Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Decoradores específicos para cada rol (opcional, pero recomendados para claridad) ---
# Estos hacen que tu código de rutas sea más legible.

def client_required(f):
    """Solo permite acceso a usuarios con el rol 'client" """
    return role_required('cliente')(f)

def admin_required(f):
    """Solo permite acceso a usuarios con el rol 'admin'."""
    return role_required('admin')(f)

def operador_required(f):
    """Solo permite acceso a usuarios con el rol 'operador'."""
    return role_required('operador')(f)

def coordinador_required(f):
    """Solo permite acceso a usuarios con el rol 'coordinador'."""
    return role_required('coordinador')(f)

def supervisor_required(f):
    """Solo permite acceso a usuarios con el rol 'supervisor'."""
    return role_required('supervisor')(f)

def auxiliar_required(f):
    """Solo permite acceso a usuarios con el rol 'auxiliar'."""
    return role_required('auxiliar')(f)

def ingenieria_required(f):
    """Solo permite acceso a usuarios con el rol 'ingenieria'."""
    return role_required('ingenieria')(f)

def conductor_required(f):
    """Solo permite acceso a usuarios con el rol 'conductor'."""
    return role_required('conductor')(f)

'''# --- Decoradores para combinaciones comunes de roles (ej. un rol o uno superior) --- '''
def supervisor_or_admin_required(f):
    """Permite acceso a 'admin' o 'supervisor'."""
    return role_required(['admin', 'supervisor'])(f)