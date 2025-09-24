# --- Modelos SQLAlchemy Originales (Comentados como referencia) ---
# from app import db
# from werkzeug.security import generate_password_hash, check_password_hash
# from flask_login import UserMixin
# from itsdangerous import URLSafeTimedSerializer as TimedSerializer
# from flask import current_app
# from sqlalchemy import Numeric
#
# class Role(db.Model):
#     __tablename__ = 'role'
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(50), unique=True, nullable=False)
#     value = db.Column(db.String(50), unique=True, nullable=False)
#     personas = db.relationship('Persona', backref='role_obj', lazy=True)
#
#     def __repr__(self):
#         return f"<Role '{self.name}'>"
#
# class Persona(db.Model, UserMixin): 
#     __tablename__ = 'personas'
#     username = db.Column(db.String(100), nullable=False, unique=True)
#     email = db.Column(db.String(120), unique=True, nullable=False)
#     password_hash = db.Column(db.String(256))
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), nullable=False)
#     middleName = db.Column(db.String(100))
#     firstSurname = db.Column(db.String(100), nullable=False)
#     secondSurname = db.Column(db.String(100))
#     role_id = db.Column(db.Integer, db.ForeignKey('role.id'))


# --- Nuevos Modelos adaptados para PyMongo (basado en referencia) ---

from app import mongo
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer as TimedSerializer
from flask import current_app
from bson.objectid import ObjectId

class Role:
    """Clase simple para representar un Rol. No es un modelo de base de datos."""
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return f"<Role '{self.name}'>"

class Persona(UserMixin):
    def __init__(self, username, email, name, firstSurname, password="", _id=None, middleName="", secondSurname="", role="cliente", password_hash=None, **kwargs):
        self.username = username
        self.email = email
        self.name = name
        self.middleName = middleName
        self.firstSurname = firstSurname
        self.secondSurname = secondSurname
        self.role = role  # Almacenamos el 'value' del rol como un string

        # Flask-Login requiere que el atributo 'id' sea un string.
        self.id = str(_id) if _id else None

        if password_hash:
            self.password_hash = password_hash
        elif password:
            self.set_password(password)
        else:
            self.password_hash = None

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if self.password_hash:
            return check_password_hash(self.password_hash, password)
        return False

    def get_reset_password_token(self, expires_in=600):
        s = TimedSerializer(current_app.config["SECRET_KEY"])
        return s.dumps({"user_id": self.id})

    @staticmethod
    def verify_reset_password_token(token, expires_in=600):
        s = TimedSerializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token, max_age=expires_in)
            user_id = data.get("user_id")
            if user_id is None:
                return None
            user_data = mongo.db.personas.find_one({"_id": ObjectId(user_id)})
            if user_data:
                return Persona(**user_data)
            return None
        except Exception:
            return None

    # get_id es requerido por Flask-Login
    def get_id(self):
        return self.id

    # --- MÉTODOS DE PROPIEDAD PARA ROLES ---
    @property
    def is_client(self):
        return self.role == "cliente"

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_supervisor(self):
        return self.role == "supervisor"

    @property
    def is_operator(self):
        return self.role == "operador"

    def has_any_role(self, roles):
        return self.role in roles

    def __repr__(self):
        return f"<Persona {self.name} {self.firstSurname} (Posición: {self.role})>"