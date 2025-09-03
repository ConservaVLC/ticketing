from flask import render_template, redirect, url_for, flash, request, current_app
from app.auth import auth_bp
from app.auth.forms import RegistrationForm, LoginForm, ResetPasswordForm, RequestResetPasswordForm, ChangePasswordForm, ProfileEditForm, UserEditForm
from app.auth.models import Persona, Role
from sqlalchemy.exc import SQLAlchemyError
from app import db # Importar db desde la aplicación principal
from app.email import send_password_reset_email
import logging
from app.auth.decorators import admin_required

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

# Necesitamos Flask-Login para gestionar sesiones de usuario de forma más robusta
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

# Inicializar Flask-Login con la aplicación (esto debería ir en app.py, pero lo pongo aquí para simplicidad de ejemplo del blueprint)
# En una aplicación real, inicializarías login_manager.init_app(app) en create_app()

# Obtén el logger específico para este módulo

# Importar 'or_' de SQLAlchemy
from sqlalchemy import or_

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
#               FUNCIÓN: REGISTRAR UN USUARIO
# ------------------------------------------------------------------------------
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
  
    form = RegistrationForm()
    
    roles = Role.query.order_by(Role.name).all()
    role_choices = [(r.id, r.name) for r in roles]
    form.role.choices = [('', '--- Seleccione una opción ---')] + role_choices

    if form.validate_on_submit():
        
        user = Persona(
            
            username=form.username.data, 
            email=form.email.data, 
            name=form.name.data,
            firstSurname=form.firstSurname.data,
            middleName = form.middleName.data,
            secondSurname=form.secondSurname.data,
            role_id=form.role.data)
        
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        # --- Logger: INFO - Usuario registrado ---
        logger.info(f'Usuario {current_user.username} (ID: {current_user.id}) ha creado un nuevo usuario: Usuario: {user.username} (ID: {user.id})')
        flash('Usuario registrado con éxito', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html', form=form)

# ------------------------------------------------------------------------------
#               FUNCIÓN: INICIAR SESIÓN
# ------------------------------------------------------------------------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():

        try:
            user = Persona.query.filter(or_(Persona.username == form.username.data,
                                        Persona.email == form.username.data)).first()      
        except SQLAlchemyError as e:
            # --- Logger: INFO - Error en base de datos ---
            logger.error(f"Error en la base de datos al intentar inicio de sesión'{form.username.data}': {e}", exc_info=True)
            flash('Lo sentimos, no pudimos procesar tu solicitud en este momento. Inténtalo de nuevo más tarde.', 'danger')
            return redirect(url_for('auth.login'))
        
        except Exception as e:
            # --- Logger: INFO - Error inesperado ---
            logger.error(f"Error insesperado al intentar iniciar sesión con el usuario '{form.username.data}': {e}", exc_info=True)
            flash('Ha ocurrido un error inesperado. Por favor, inténtalo de nuevo.', 'danger')
            return redirect(url_for('auth.login'))
        
        if user is None:
            # --- Logger: WARNING - Usuario no encontrado ---
            logger.warning(f"Intento de inicio de sesión fallido: user/email '{form.username.data}' no encontrado")
            flash('Nombre de usuario/correo electrónico o contraseña inválidos', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.check_password(form.password.data): # <-- Clave 2
            flash('Nombre de usuario/correo electrónico o contraseña inválidos', 'danger')
            return redirect(url_for('auth.login'))
        
        # Pasa el valor de 'remember_me' a login_user
        login_user(user, remember=form.remember_me.data)
        
        # --- Logger: INFO - Inicio de sesión exitoso ---
        logger.info(f"Usuario {user.username} ha iniciado sesión exitosamente desde IP: {request.remote_addr}")
        flash(f'¡Bienvenido de nuevo, {user.username}!', 'success')
        
        return redirect(url_for('main.home'))
    return render_template('login.html', form=form)

# ------------------------------------------------------------------------------
#               FUNCIÓN: CERRAR SESIÓN
# ------------------------------------------------------------------------------
@auth_bp.route('/logout')
@login_required # Requiere que el usuario esté logueado para acceder a esta ruta
def logout():
    logout_user() # Flask-Login cierra la sesión
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('main.home'))

@auth_bp.route('/request_password_reset', methods=['GET', 'POST'])
def request_password_reset():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = RequestResetPasswordForm()
    if form.validate_on_submit():
        user = Persona.query.filter_by(email=form.email.data).first()
        if user:
            # --- Logger: INFO - Solicitud de recuperación de contraseña ---
            logger.info(f"Usuario {user.username} ha solicitado recuperación de contraseña a través de Token")
            send_password_reset_email(user)
            flash('Se ha enviado un correo electrónico con instrucciones para restablecer tu contraseña.', 'info')
        else:
            # --- Logger: WARNING - Solicitud de recuperación de contraseña por Token en usuario no autorizado ---
            logger.warning(f"Solicitud de recuperación de contraseña para usuario/email no existente desde IP: {request.remote_addr}")
            # Por seguridad, no decimos si el email no existe, damos el mismo mensaje.
            flash('Se ha enviado un correo electrónico con instrucciones para restablecer tu contraseña.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('request_password_reset.html', title='Restablecer Contraseña', form=form)

# ------------------------------------------------------------------------------
#               FUNCIÓN: RECUPERAR CONTRASEÑA MEDIANTE TOKEN (MAIL)
# ------------------------------------------------------------------------------
@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    user = Persona.verify_reset_password_token(token)
    if not user:
        # --- Logger: WARNING - Token de recuperación de contraseña incorrecto ---
        logger.warning(f"Se he intentado utilizar un Token incorrecto para recuperar la contraseña del usuario {user.username} desde IP: {request.remote_addr}")
        flash('El enlace de restablecimiento de contraseña no es válido o ha expirado.', 'danger')
        return redirect(url_for('auth.request_password_reset'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        # --- Logger: INFO - Contraseña recuperada con éxito median Token ---
        logger.info(f"Usuario {user.username} ha recuperado su contraseña correctamente mediante Token")
        flash('Tu contraseña ha sido restablecida. Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', title='Restablecer Contraseña', form=form)

# ------------------------------------------------------------------------------
#               FUNCIÓN: EDITAR PERFIL DE USUARIO (USUARIO)
# ------------------------------------------------------------------------------
@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = ProfileEditForm(obj=current_user)

    if request.method == 'GET':
        form.role.data = current_user.role_obj.name

    if form.validate_on_submit():
        try:
            # Mapea los datos del formulario a los atributos del modelo Persona
            current_user.name = form.name.data
            current_user.middleName = form.middleName.data
            current_user.firstSurname = form.firstSurname.data
            current_user.secondSurname = form.secondSurname.data
            
            # El rol NO se modifica aquí, ya que esta vista es para que el usuario
            # edite sus propios datos personales, no su nivel de privilegio.
            
            db.session.add(current_user) # Añade el objeto actualizado a la sesión
            db.session.commit() # Guarda los cambios en la base de datos
            
            # --- Logger: INFO - Perfil actualizado correctamente ---
            logger.info(f"Usuario {current_user.username} ha actualizado su perfil correctamente")
            flash('Tu perfil ha sido actualizado exitosamente.', 'success')
            return redirect(url_for('auth.edit_profile')) # Redirige de nuevo a la página de edición para ver los cambios
            
        except SQLAlchemyError as e:
            db.session.rollback()
            # --- Logger: ERROR - Fallo en BBDD al editar el usuario ---
            logger.error(f"Error en la base de datos al editar el perfil: Usuario {current_user.username}, (ID: {current_user.id}): {str(e)}", exc_info=True) 
            flash(f'Ocurrió un error en la base de datos al actualizar tu perfil: {e}', 'danger')
        except Exception as e:
            # --- Logger: ERROR - Error inesperado ---
            db.session.rollback()
            message=f"Ocurrió un error inesperado. Por favor, contacte a soporte. Detalles: '{e}'", 'error'
            logger.error(f'Al editar el perfil: {message}',exc_info=True)
            flash(message, 'error')

    # Si es GET o la validación falla, renderiza el formulario
    return render_template('edit_profile.html', title='Editar Perfil', form=form)

# ------------------------------------------------------------------------------
#               FUNCIÓN: CAMBIAR CONTRASEÑA (USUARIO)
# ------------------------------------------------------------------------------
@auth_bp.route('/profile/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.old_password.data):
            # --- Logger: WARNING - Contraseña actual incorrecta ---
            logger.warning(f"Usuario {current_user.username} ha proporcionado una contraseña actual incorrecta al intentar modificar su contraseña")
            flash('Contraseña actual incorrecta.', 'danger')
        else:
            try:
                current_user.set_password(form.new_password.data)
                db.session.add(current_user)
                db.session.commit()

                # --- Logger: INFO - Contraseña recuperada con éxito ---
                logger.info(f"Usuario {current_user.username} ha modificado su contraseña correctamente")
                flash('Tu contraseña ha sido actualizada exitosamente. Vuelve a iniciar sesión', 'success')
                
                logout_user()

                return redirect(url_for('auth.login'))

            except SQLAlchemyError as e:
                db.session.rollback()
                # --- Logger: ERROR - Fallo en BBDD al editar el usuario ---
                logger.error(f"Error en la base de datos al cambiar contraseña: Usuario {current_user.username}, (ID: {current_user.id}): {str(e)}", exc_info=True) 
                flash(f'Ocurrió un error en la base de datos al actualizar tu contraseña: {e}', 'danger')
            except Exception as e:
                # --- Logger: ERROR - Error inesperado ---
                db.session.rollback()
                message=f"Ocurrió un error inesperado. Por favor, contacte a soporte. Detalles: '{e}'", 'error'
                logger.error(f'Al actualizar contraseña: {message}',exc_info=True)
                flash(message, 'error')

    return render_template('change_password.html', title='Cambiar Contraseña', form=form)

# ------------------------------------------------------------------------------
#               FUNCIÓN: LISTADO DE USUARIOS
# ------------------------------------------------------------------------------
@auth_bp.route('/users')
@login_required
@admin_required
def list_users():
    personas = db.session.execute(db.select(Persona).order_by(Persona.firstSurname.desc())).scalars().all()
    # --- Logger: INFO - Consulta de tickets exitosa ---
    logger.info(f'Usuario {current_user.username} (ID: {current_user.id}) consultó el listado de usuarios. Se encontraron {len(personas)} usuarios.')
    
    return render_template('list_users.html', personas=personas)

# ------------------------------------------------------------------------------
#               FUNCIÓN: EDITAR PERFIL DE USUARIO (ADMIN)
# ------------------------------------------------------------------------------
@auth_bp.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = db.session.execute(select(Persona).filter_by(id=user_id)).scalar_one_or_none()

    if not user:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('auth.list_users'))

    form = UserEditForm(original_username=user.username, original_email=user.email, obj=user)

    roles = Role.query.order_by(Role.name).all()
    role_choices = [(r.id, r.name) for r in roles]
    form.role.choices = [('', '--- Seleccione una opción ---')] + role_choices

    if form.validate_on_submit():
        try:
            user.username = form.username.data
            user.email = form.email.data
            user.name = form.name.data
            user.middleName = form.middleName.data
            user.firstSurname = form.firstSurname.data
            user.secondSurname = form.secondSurname.data
            user.role_id = form.role.data

            if form.password.data:
                user.password_hash = generate_password_hash(form.password.data)
            
            db.session.add(user)
            db.session.commit()
            
            # --- Logger: INFO - Admin/Supervisor modifica exitosamente perfil de otro usuario ---
            logger.info(f"Usuario {current_user.username} ha modificado correctamente el perfil del usuario {user.username}")
            flash(f'Perfil del usuario {user.username} actualizado correctamente.', 'success')
            return redirect(url_for('auth.list_users'))

        except SQLAlchemyError as e:
            db.session.rollback()
            # --- Logger: ERROR - Fallo en BBDD al editar el usuario ---
            logger.error(f"Usuario {current_user.username} obtiene error en la base de datos modificar el perfil: Usuario {user.username}, (ID: {user.id}): {str(e)}", exc_info=True) 
            flash(f'Ocurrió un error en la base de datos al actualizar el usuario: {e}', 'danger')
        except Exception as e:
            # --- Logger: ERROR - Error inesperado ---
            db.session.rollback()
            message=f"Ocurrió un error inesperado. Por favor, contacte a soporte. Detalles: '{e}'", 'error'
            logger.error(f'Usuario {current_user.username} al modificar un perfil: {message}',exc_info=True)
            flash(message, 'error')
    
    return render_template('admin_edit_user.html', title='Edit User', form=form, user=user)
