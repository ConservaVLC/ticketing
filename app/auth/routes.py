from flask import render_template, redirect, url_for, flash, request, session
from app.auth import auth_bp
from app.auth.forms import (
    RegistrationForm, LoginForm, ResetPasswordForm, RequestResetPasswordForm, 
    ChangePasswordForm, ProfileEditForm, UserEditForm, Verify2FAForm
)
from app.auth.models import Persona
from app import mongo, limiter
import logging
from app.auth.decorators import admin_required
from werkzeug.security import generate_password_hash
from bson.objectid import ObjectId
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from threading import Thread
from flask import current_app
from flask_mail import Message
from app import mail

logger = logging.getLogger(__name__)

def send_async_email(app, msg):
    """Función auxiliar para enviar el correo en un hilo separado con manejo de errores."""
    with app.app_context():
        try:
            mail.send(msg)
            logger.info(f"Correo enviado exitosamente a {msg.recipients}")
        except Exception as e:
            logger.error(
                f"Error al enviar correo a {msg.recipients}: {e}", exc_info=True
            )

def send_2fa_code_email(user):
    """Envía el código 2FA al usuario."""
    msg = Message(
        "Tu Código de Verificación",
        sender=current_app.config["ADMINS"][0],
        recipients=[user.email],
    )
    msg.body = render_template("email/2fa_code.txt", user=user)
    msg.html = render_template("email/2fa_code.html", user=user)
    Thread(
        target=send_async_email, args=(current_app._get_current_object(), msg)
    ).start()

def send_password_reset_email_wrapper(user):
    token = user.get_reset_password_token()
    msg = Message(
        "Restablecer Contraseña - [TuApp]",
        sender=current_app.config["ADMINS"][0],
        recipients=[user.email],
    )
    msg.body = render_template("email/reset_password.txt", user=user, token=token)
    msg.html = render_template("email/reset_password.html", user=user, token=token)
    Thread(
        target=send_async_email, args=(current_app._get_current_object(), msg)
    ).start()



@auth_bp.route("/register", methods=["GET", "POST"])
@login_required
@admin_required
def register():
    form = RegistrationForm()
    try:
        roles = mongo.db.roles.find()
        role_choices = [(r["value"], r["name"]) for r in roles]
        form.role.choices = [("", "--- Seleccione una opción ---")] + role_choices
    except Exception as e:
        logger.error(f"No se pudieron cargar los roles de la base de datos: {e}")
        flash("Error al cargar los roles. No se puede registrar un usuario.", "danger")
        form.role.choices = []

    if form.validate_on_submit():
        try:
            user = Persona(
                username=form.username.data,
                email=form.email.data,
                name=form.name.data,
                firstSurname=form.firstSurname.data,
                middleName=form.middleName.data,
                secondSurname=form.secondSurname.data,
                role=form.role.data,
            )

            user.set_password(form.password.data)

            user_dict = user.__dict__
            user_dict.pop("id", None)  # Remove id if it exists, as MongoDB will create it

            mongo.db.personas.insert_one(user_dict)
            flash("Usuario registrado con éxito", "success")
            return redirect(url_for("auth.list_users"))
        except Exception as e:
            logger.error(f"Error al registrar el usuario: {e}", exc_info=True)
            flash("Ocurrió un error al registrar el usuario.", "danger")

    return render_template("register.html", form=form)

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = LoginForm()
    if form.validate_on_submit():
        try:
            user_data = mongo.db.personas.find_one(
                {"$or": [{"username": form.username.data}, {"email": form.username.data}]}
            )
            user = Persona(**user_data) if user_data else None

        except Exception as e:
            logger.error(
                f"Error inesperado al intentar iniciar sesión con el usuario '{form.username.data}': {e}",
                exc_info=True,
            )
            flash(
                "Ha ocurrido un error inesperado. Por favor, inténtalo de nuevo.",
                "danger",
            )
            return redirect(url_for("auth.login"))

        if user is None or not user.check_password(form.password.data):
            logger.warning(
                f"Intento de inicio de sesión fallido para el usuario/email '{form.username.data}'"
            )
            flash(
                "Nombre de usuario/correo electrónico o contraseña inválidos", "danger"
            )
            return redirect(url_for("auth.login"))

        # --- INICIO LÓGICA 2FA ---
        user.generate_2fa_code()
        mongo.db.personas.update_one(
            {"_id": ObjectId(user.id)},
            {
                "$set": {
                    "two_factor_code": user.two_factor_code,
                    "two_factor_code_expiration": user.two_factor_code_expiration,
                }
            },
        )

        send_2fa_code_email(user)

        session["2fa_user_id"] = user.id
        flash("Se ha enviado un código de verificación a tu correo.", "info")
        return redirect(url_for("auth.verify_2fa"))

    return render_template("login.html", form=form)

@auth_bp.route("/verify_2fa", methods=["GET", "POST"])
def verify_2fa():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    user_id = session.get("2fa_user_id")
    if not user_id:
        flash(
            "La sesión de verificación ha expirado. Por favor, inicia sesión de nuevo.",
            "warning",
        )
        return redirect(url_for("auth.login"))

    user_data = mongo.db.personas.find_one({"_id": ObjectId(user_id)})
    if not user_data:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for("auth.login"))

    user = Persona(**user_data)
    form = Verify2FAForm()

    if form.validate_on_submit():
        if user.check_2fa_code(form.code.data):
            login_user(user, remember=form.trust_device.data)

            # Limpiar los datos de 2FA de la base de datos
            mongo.db.personas.update_one(
                {"_id": ObjectId(user.id)},
                {"$unset": {"two_factor_code": "", "two_factor_code_expiration": ""}},
            )
            session.pop("2fa_user_id", None)  # Limpiar la sesión

            flash("¡Bienvenido de nuevo!", "success")
            return redirect(url_for("main.home"))
        else:
            flash("Código incorrecto o expirado.", "danger")

    return render_template("verify_2fa.html", form=form)

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for("main.home"))

@auth_bp.route("/request_password_reset", methods=["GET", "POST"])
def request_password_reset():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = RequestResetPasswordForm()
    if form.validate_on_submit():
        user_data = mongo.db.personas.find_one({"email": form.email.data})
        if user_data:
            user = Persona(**user_data)
            send_password_reset_email_wrapper(user)
        flash("Si tu correo está registrado, recibirás un email con instrucciones.", "info")
        return redirect(url_for("auth.login"))
    return render_template("request_password_reset.html", title="Restablecer Contraseña", form=form)

@auth_bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    user = Persona.verify_reset_password_token(token)
    if not user:
        flash("El enlace de restablecimiento no es válido o ha expirado.", "danger")
        return redirect(url_for("auth.request_password_reset"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        mongo.db.personas.update_one(
            {"_id": ObjectId(user.id)},
            {
                "$set": {
                    "password_hash": user.password_hash,
                    "password_changed_at": datetime.utcnow(),
                }
            },
        )
        flash("Tu contraseña ha sido restablecida. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("auth.login"))
    return render_template("reset_password.html", title="Restablecer Contraseña", form=form)

@auth_bp.route("/profile/view", methods=["GET"])
@login_required
def edit_profile():
    form = ProfileEditForm(obj=current_user)

    if request.method == 'GET':
        form.role.data = current_user.role

    return render_template("edit_profile.html", title="Ver Perfil", form=form)

@auth_bp.route("/profile/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.old_password.data):
            flash("Contraseña actual incorrecta.", "danger")
        else:
            current_user.set_password(form.new_password.data)
            mongo.db.personas.update_one(
                {"_id": ObjectId(current_user.id)},
                {
                    "$set": {
                        "password_hash": current_user.password_hash,
                        "password_changed_at": datetime.utcnow(),
                    }
                },
            )
            flash("Tu contraseña ha sido actualizada. Vuelve a iniciar sesión.", "success")
            logout_user()
            return redirect(url_for("auth.login"))
    return render_template("change_password.html", title="Cambiar Contraseña", form=form)

@auth_bp.route("/users")
@login_required
@admin_required
def list_users():
    personas_data = mongo.db.personas.find()
    personas = [Persona(**p) for p in personas_data]
    return render_template("list_users.html", personas=personas)

@auth_bp.route("/user/<user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id):
    user_data = mongo.db.personas.find_one({"_id": ObjectId(user_id)})
    if not user_data:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for("auth.list_users"))

    user = Persona(**user_data)
    form = UserEditForm(original_username=user.username, original_email=user.email, obj=user)
    
    try:
        roles = mongo.db.roles.find()
        form.role.choices = [(r["value"], r["name"]) for r in roles]
        if request.method == 'GET':
            form.role.data = user.role # Pre-seleccionar el rol actual
    except Exception as e:
        logger.error(f"No se pudieron cargar los roles de la base de datos: {e}")
        flash("Error al cargar los roles.", "danger")

    if form.validate_on_submit():
        update_data = {
            "username": form.username.data,
            "email": form.email.data,
            "name": form.name.data,
            "middleName": form.middleName.data,
            "firstSurname": form.firstSurname.data,
            "secondSurname": form.secondSurname.data,
            "role": form.role.data,
        }
        if form.password.data:
            update_data["password_hash"] = generate_password_hash(form.password.data)
            update_data["password_changed_at"] = datetime.utcnow()
        
        mongo.db.personas.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
        flash(f"Perfil del usuario {user.username} actualizado correctamente.", "success")
        return redirect(url_for("auth.list_users"))

    return render_template("admin_edit_user.html", title="Editar Usuario", form=form, user=user)