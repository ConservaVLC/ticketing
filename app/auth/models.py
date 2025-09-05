from app import db # Ahora 'db' apunta a la instancia de SQLAlchemy de tu app principal
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin # No importamos current_app aquí
from itsdangerous import URLSafeTimedSerializer as TimedSerializer
from flask import current_app
from sqlalchemy import Numeric


class Role(db.Model):
    __tablename__ = 'role'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(50), unique=True, nullable=False)

    # 'backref='role_obj'' crea una propiedad inversa en Ticket llamada 'role_obj'
    # ticket.role_obj te dará el objeto Category al que pertenece el ticket.
    personas = db.relationship('Persona', backref='role_obj', lazy=True)

    def __repr__(self):
        return f"<Role '{self.name}'>"
    

class Persona(db.Model, UserMixin): # Asumo que Persona es tu modelo de usuario para Flask-Login
    __tablename__ = 'personas'

    # DATOS DE INICIO DE SESION
    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(120), unique=True, nullable=False) # Email único
    password_hash = db.Column(db.String(256))
    
    # DATOS PERSONALES DEL USUARIO
    id = db.Column(db.Integer, primary_key=True) # Clave primaria autoincremental
    name = db.Column(db.String(100), nullable=False)
    middleName = db.Column(db.String(100))
    firstSurname = db.Column(db.String(100), nullable=False)
    secondSurname = db.Column(db.String(100))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
       
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # --- Métodos para Recuperación de Contraseña ---
    def get_reset_password_token(self, expires_in=600):
        s = TimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_password_token(token, expires_in=600):
        s = TimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=expires_in)
        except:
            return None # El token es inválido o ha expirado
        return Persona.query.get(data['user_id'])

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def get_id(self):
        return str(self.id) # UserMixin ya implementa esto, pero es bueno saberlo

    # Para hashing de contraseñas, usaríamos Werkzeug Security
    # password_hash = db.Column(db.String(128), nullable=False)
    # def set_password(self, password):
    #     self.password_hash = generate_password_hash(password)
    # def check_password(self, password):
    #     return check_password_hash(self.password_hash, password)

    
    # --- MÉTODOS DE PROPIEDAD PARA ROLES ---
    @property
    def is_client(self):
        return self.role_obj.value == 'cliente'
    @property
    def is_admin(self):
        return self.role_obj.value == 'admin'

    @property
    def is_supervisor(self):
        return self.role_obj.value == 'supervisor'

    @property
    def is_coordinator(self):
        return self.role_obj.value == 'coordinador'

    @property
    def is_operator(self):
        return self.role_obj.value == 'operador'

    @property
    def is_driver(self):
        return self.role_obj.value == 'conductor'
    
    @property
    def is_engineer(self):
        return self.role_obj.value == 'ingenieria'
    
    @property
    def is_auxiliar(self):
        return self.role_obj.value == 'auxiliar'

    # Un método genérico si quieres comprobar si tiene *alguno* de varios roles
    def has_any_role(self, roles):
        return self.role_obj.value in roles

    def __repr__(self):
        return f"<Persona {self.name} {self.firstSurname} (Posición: {self.role_obj.value})>"
    