from app import db
from app.auth.models import Persona, Role
from sqlalchemy import or_, select

# -----------------------------------------------
# INTERFACES DE REPOSITORIO
# -----------------------------------------------

class UserRepository:
    """Define el contrato para operaciones de datos de usuario."""
    def find_by_username_or_email(self, username_or_email):
        raise NotImplementedError

    def find_by_email(self, email):
        raise NotImplementedError

    def find_by_id(self, user_id):
        raise NotImplementedError

    def get_all(self):
        raise NotImplementedError

    def add(self, user):
        raise NotImplementedError

class RoleRepository:
    """Define el contrato para operaciones de datos de roles."""
    def get_all_ordered_by_name(self):
        raise NotImplementedError

# -----------------------------------------------
# IMPLEMENTACIONES SQL
# -----------------------------------------------

class SQLUserRepository(UserRepository):
    """Implementación concreta del repositorio de usuario para SQLAlchemy."""
    def find_by_username_or_email(self, username_or_email):
        return Persona.query.filter(or_(Persona.username == username_or_email, Persona.email == username_or_email)).first()

    def find_by_email(self, email):
        return Persona.query.filter_by(email=email).first()

    def find_by_id(self, user_id):
        return db.session.execute(select(Persona).filter_by(id=user_id)).scalar_one_or_none()

    def get_all(self):
        return db.session.execute(db.select(Persona).order_by(Persona.firstSurname.desc())).scalars().all()

    def add(self, user):
        db.session.add(user)

class SQLRoleRepository(RoleRepository):
    """Implementación concreta del repositorio de roles para SQLAlchemy."""
    def get_all_ordered_by_name(self):
        return Role.query.order_by(Role.name).all()
