from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, Optional
import re
from markupsafe import Markup
from app import mongo # Importamos el objeto mongo

def password_complexity_validator(form, field):
    password = field.data
    errors = []

    if len(password) < 15:
        errors.append("La contraseña debe tener al menos 15 caracteres.")
    if not re.search(r"\d", password):
        errors.append("La contraseña debe contener al menos un número.")
    if not re.search(r"[A-Z]", password):
        errors.append("La contraseña debe contener al menos una letra mayúscula.")
    if not re.search(r"[a-z]", password):
        errors.append("La contraseña debe contener al menos una letra minúscula.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("La contraseña debe contener al menos un carácter especial.")

    if errors:
        error_html = "".join([f"<li>{error}</li>" for error in errors])
        mensaje_final = Markup(
            f"La contraseña no cumple los siguientes requisitos:<ul>{error_html}</ul>"
        )
        raise ValidationError(mensaje_final)

class RegistrationForm(FlaskForm):
    username = StringField('Nombre de Usuario', validators=[DataRequired(message="Este campo es obligatorio"), Length(min=4, max=50)])
    name = StringField('Primer nombre', validators=[DataRequired(message="Este campo es obligatorio"), Length(min=1, max=30)])
    middleName = StringField('Segundo nombre', validators=[Optional(), Length(min=1, max=30)])
    firstSurname = StringField('Primer apellido', validators=[DataRequired(message="Este campo es obligatorio"), Length(min=1, max=30)])
    secondSurname = StringField('Segundo apellido', validators=[Optional(), Length(min=1, max=30)])
    email = StringField('Correo Electrónico', validators=[DataRequired(message="Este campo es obligatorio"), Email()])
    password = PasswordField(
        "Contraseña",
        validators=[
            DataRequired(message="Este campo es obligatorio"),
            password_complexity_validator,
        ],
    )
    password2 = PasswordField('Repetir Contraseña', validators=[DataRequired(message="Este campo es obligatorio"), EqualTo('password', message='Las contraseñas no coinciden.')])
    submit = SubmitField('Registrar usuario', render_kw={"class": "btn btn-primary confirm-submit-btn col-md-6"})

    def validate_username(self, username):
        user = mongo.db.personas.find_one({"username": username.data})
        if user is not None:
            raise ValidationError('Por favor, elige un nombre de usuario diferente.')

    def validate_email(self, email):
        user = mongo.db.personas.find_one({"email": email.data})
        if user is not None:
            raise ValidationError('Este correo electrónico ya está registrado.')

class LoginForm(FlaskForm):
    username = StringField('Nombre de Usuario o Correo Electrónico', validators=[DataRequired(message="Este campo es obligatorio")])
    password = PasswordField('Contraseña', validators=[DataRequired(message="Este campo es obligatorio")])
    remember_me = BooleanField('Recordarme')
    submit = SubmitField('Iniciar Sesión')

class Verify2FAForm(FlaskForm):
    code = StringField(
        "Código de 6 dígitos", validators=[DataRequired(message="Este campo es obligatorio"), Length(min=6, max=6)]
    )
    trust_device = BooleanField(
        "Mantener sesión iniciada en este dispositivo (8 horas)"
    )
    submit = SubmitField("Verificar")

class RequestResetPasswordForm(FlaskForm):
    email = StringField('Correo Electrónico', validators=[DataRequired(message="Este campo es obligatorio"), Email()])
    submit = SubmitField('Solicitar Restablecimiento de Contraseña')

    def validate_email(self, email):
        user = mongo.db.personas.find_one({"email": email.data})
        if user is None:
            raise ValidationError('No hay cuenta con ese correo electrónico. Por favor, regístrate primero.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField(
        "Contraseña",
        validators=[
            DataRequired(message="Este campo es obligatorio"),
            password_complexity_validator,
        ],
    )
    password2 = PasswordField('Confirmar Nueva Contraseña', validators=[DataRequired(message="Este campo es obligatorio"), EqualTo('password', message='Las contraseñas no coinciden.')])
    submit = SubmitField('Restablecer Contraseña')

class ProfileEditForm(FlaskForm):
    name = StringField('Primer Nombre', validators=[DataRequired(message="Este campo es obligatorio"), Length(max=100)], render_kw={'readonly': True, 'disabled': True})
    middleName = StringField('Segundo Nombre', validators=[Optional(), Length(max=100)], render_kw={'readonly': True, 'disabled': True})
    firstSurname = StringField('Primer Apellido', validators=[DataRequired(message="Este campo es obligatorio"), Length(max=100)], render_kw={'readonly': True, 'disabled': True})
    secondSurname = StringField('Segundo Apellido', validators=[Optional(), Length(max=100)], render_kw={'readonly': True, 'disabled': True})
    role = StringField('Rol', render_kw={'readonly': True, 'disabled': True})

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Contraseña Actual', validators=[DataRequired(message="Este campo es obligatorio")])
    new_password = PasswordField(
        "Contraseña",
        validators=[
            DataRequired(message="Este campo es obligatorio"),
            password_complexity_validator,
        ],
    )
    new_password2 = PasswordField('Repetir Nueva Contraseña', validators=[DataRequired(message="Este campo es obligatorio"), EqualTo('new_password', message='Las contraseñas no coinciden.')])
    submit = SubmitField('Cambiar Contraseña', render_kw={"class": "btn btn-primary confirm-submit-btn"})

class UserEditForm(FlaskForm):
    username = StringField('Nombre de usuario', validators=[DataRequired(message="Este campo es obligatorio"), Length(min=2, max=50)])
    email = StringField('Correo electrónico', validators=[DataRequired(message="Este campo es obligatorio"), Email()])
    name = StringField('Primer Nombre', validators=[DataRequired(message="Este campo es obligatorio"), Length(max=100)])
    middleName = StringField('Segundo Nombre', validators=[Optional(), Length(max=100)])
    firstSurname = StringField('Primer Apellido', validators=[DataRequired(message="Este campo es obligatorio"), Length(max=100)])
    secondSurname = StringField('Segundo Apellido', validators=[Optional(), Length(max=100)])
    password = PasswordField(
        "Contraseña",
        validators=[
            Optional(),
            password_complexity_validator,
        ],
    )
    confirm_password = PasswordField('Confirmar nueva contraseña', validators=[Optional(), EqualTo('password', message='Las contraseñas no coinciden.')])
    role = SelectField("Tipo de usuario", choices=(), validators=[DataRequired(message="Este campo es obligatorio")])
    submit = SubmitField('Actualizar usuario', render_kw={"class": "btn btn-primary confirm-submit-btn col-md-6"})

    def __init__(self, original_username=None, original_email=None, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        if username.data != self.original_username:
            user = mongo.db.personas.find_one({"username": username.data})
            if user:
                raise ValidationError('El nombre de usuario seleccionado ya existe, por favor ingrese otro nombre de usuario.')

    def validate_email(self, email):
        if email.data != self.original_email:
            user = mongo.db.personas.find_one({"email": email.data})
            if user:
                raise ValidationError('El email seleccionado ya existe, por favor ingrese otro email.')