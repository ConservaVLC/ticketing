# app/auth/decorators.py

from functools import wraps
from flask import abort, flash, redirect, url_for, request
from flask_login import current_user, login_required
from datetime import datetime, timedelta


# Decorador para verificar si la contraseña ha expirado
def check_password_expiration(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Primero, asegurarse de que el usuario esté autenticado
        if not current_user.is_authenticated:
            return f(*args, **kwargs)

        # Excluir endpoints que no deben tener esta verificación para evitar bucles
        if request.endpoint in ["auth.change_password", "auth.logout"]:
            return f(*args, **kwargs)

        # Forzar cambio si la fecha no existe (para usuarios antiguos)
        if (
            not hasattr(current_user, "password_changed_at")
            or not current_user.password_changed_at
        ):
            flash(
                "Por seguridad, debes cambiar tu contraseña para continuar.", "warning"
            )
            return redirect(url_for("auth.change_password"))

        # Calcular si la contraseña ha expirado (45 días)
        expiration_date = current_user.password_changed_at + timedelta(days=45)
        if datetime.utcnow() > expiration_date:
            flash("Tu contraseña ha expirado. Por favor, crea una nueva.", "warning")
            return redirect(url_for("auth.change_password"))

        return f(*args, **kwargs)

    return decorated_function


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
        @login_required  # Asegura que el usuario esté logueado antes de comprobar el rol
        def decorated_function(*args, **kwargs):
            # Convertir 'roles' a una lista si se pasó un solo rol como cadena
            if isinstance(roles, str):
                allowed_roles = [roles]
            else:
                allowed_roles = roles

            # Verifica si el rol del usuario está en la lista de roles permitidos
            if current_user.role not in allowed_roles:
                flash(
                    f'No tienes permiso para acceder a esta página. Tu rol es "{current_user.role}".',
                    "danger",
                )
                abort(403)  # HTTP 403 Forbidden
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# --- Decoradores específicos para cada rol (opcional, pero recomendados para claridad) ---
# Estos hacen que tu código de rutas sea más legible.


def client_required(f):
    """Solo permite acceso a usuarios con el rol 'client" """
    return role_required("cliente")(f)


def admin_required(f):
    """Solo permite acceso a usuarios con el rol 'admin'."""
    return role_required("admin")(f)


def operator_required(f):
    """Solo permite acceso a usuarios con el rol 'operador'."""
    return role_required("operador")(f)


def supervisor_required(f):
    """Solo permite acceso a usuarios con el rol 'supervisor'."""
    return role_required("supervisor")(f)


"""# --- Decoradores para combinaciones comunes de roles (ej. un rol o uno superior) --- """


def supervisor_or_admin_required(f):
    """Permite acceso a 'admin' o 'supervisor'."""
    return role_required(["admin", "supervisor"])(f)
