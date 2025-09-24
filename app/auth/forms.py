from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, Regexp, Optional
from app import mongo # Importamos el objeto mongo

class RegistrationForm(FlaskForm):
    username = StringField('Nombre de Usuario', validators=[DataRequired(), Length(min=4, max=50)])
    name = StringField('Primer nombre', validators=[DataRequired(), Length(min=1, max=30)])
    middleName = StringField('Segundo nombre', validators=[Optional(), Length(min=1, max=30)])
    firstSurname = StringField('Primer apellido', validators=[DataRequired(), Length(min=1, max=30)])
    secondSurname = StringField('Segundo apellido', validators=[Optional(), Length(min=1, max=30)])
    role = SelectField("Tipo de usuario", choices=[], validators=[DataRequired()])
    email = StringField('Correo Electrónico', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[
        DataRequired(),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres.'),
        Regexp(r'.*\d.*', message='La contraseña debe contener al menos un número.'),
        Regexp(r'.*[!@#$%^&*(),.?":{}|<>].*', message='La contraseña debe contener al menos un carácter especial.')
    ])
    password2 = PasswordField('Repetir Contraseña', validators=[DataRequired(), EqualTo('password', message='Las contraseñas no coinciden.')])
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
    username = StringField('Nombre de Usuario o Correo Electrónico', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember_me = BooleanField('Recordarme')
    submit = SubmitField('Iniciar Sesión')

class RequestResetPasswordForm(FlaskForm):
    email = StringField('Correo Electrónico', validators=[DataRequired(), Email()])
    submit = SubmitField('Solicitar Restablecimiento de Contraseña')

    def validate_email(self, email):
        user = mongo.db.personas.find_one({"email": email.data})
        if user is None:
            raise ValidationError('No hay cuenta con ese correo electrónico. Por favor, regístrate primero.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nueva Contraseña', validators=[
        DataRequired(),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres.'),
        Regexp(r'.*\d.*', message='La contraseña debe contener al menos un número.'),
        Regexp(r'.*[!@#$%^&*(),.?":{}|<>].*', message='La contraseña debe contener al menos un carácter especial.')
    ])
    password2 = PasswordField('Confirmar Nueva Contraseña', validators=[DataRequired(), EqualTo('password', message='Las contraseñas no coinciden.')])
    submit = SubmitField('Restablecer Contraseña')

class ProfileEditForm(FlaskForm):
    name = StringField('Primer Nombre', validators=[DataRequired(), Length(max=100)])
    middleName = StringField('Segundo Nombre', validators=[Optional(), Length(max=100)])
    firstSurname = StringField('Primer Apellido', validators=[DataRequired(), Length(max=100)])
    secondSurname = StringField('Segundo Apellido', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Actualizar Perfil', render_kw={"class": "btn btn-primary confirm-submit-btn"})
    role = StringField('Rol', render_kw={'readonly': True})

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Contraseña Actual', validators=[DataRequired()])
    new_password = PasswordField('Contraseña', validators=[
        DataRequired(),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres.'),
        Regexp(r'.*\d.*', message='La contraseña debe contener al menos un número.'),
        Regexp(r'.*[!@#$%^&*(),.?":{}|<>].*', message='La contraseña debe contener al menos un carácter especial.')
    ])
    new_password2 = PasswordField('Repetir Nueva Contraseña', validators=[DataRequired(), EqualTo('new_password', message='Las contraseñas no coinciden.')])
    submit = SubmitField('Cambiar Contraseña', render_kw={"class": "btn btn-primary confirm-submit-btn"})

class UserEditForm(FlaskForm):
    username = StringField('Nombre de usuario', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    name = StringField('Primer Nombre', validators=[DataRequired(), Length(max=100)])
    middleName = StringField('Segundo Nombre', validators=[Optional(), Length(max=100)])
    firstSurname = StringField('Primer Apellido', validators=[DataRequired(), Length(max=100)])
    secondSurname = StringField('Segundo Apellido', validators=[Optional(), Length(max=100)])
    password = PasswordField('Nueva contraseña', validators=[
        Optional(),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres.'),
        Regexp(r'.*\d.*', message='La contraseña debe contener al menos un número.'),
        Regexp(r'.*[!@#$%^&*(),.?":{}|<>].*', message='La contraseña debe contener al menos un carácter especial.')
    ])
    confirm_password = PasswordField('Confirmar nueva contraseña', validators=[Optional(), EqualTo('password', message='Las contraseñas no coinciden.')])
    role = SelectField("Tipo de usuario", choices=(), validators=[DataRequired()])
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