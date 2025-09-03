from app import db
from app.auth.models import Persona, Role
from app.models import Category, Ticket
from sqlalchemy import or_, select, func

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

class CategoryRepository:
    """Define el contrato para operaciones de datos de categorías."""
    def get_all(self):
        raise NotImplementedError
    
    def find_by_id(self, category_id):
        raise NotImplementedError

    def find_by_value(self, value):
        raise NotImplementedError

    def find_by_value_and_not_id(self, value, category_id):
        raise NotImplementedError

    def add(self, category):
        raise NotImplementedError

    def delete(self, category):
        raise NotImplementedError
        
    def get_associated_ticket_count(self, category_id):
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

class SQLCategoryRepository(CategoryRepository):
    """Implementación concreta del repositorio de categorías para SQLAlchemy."""
    def get_all(self):
        return db.session.execute(select(Category)).scalars().all()

    def find_by_id(self, category_id):
        return db.session.execute(select(Category).filter_by(id=category_id)).scalar_one_or_none()

    def find_by_value(self, value):
        return db.session.execute(select(Category).filter_by(value=value)).scalar_one_or_none()

    def find_by_value_and_not_id(self, value, category_id):
        return db.session.execute(
            select(Category).filter(
                Category.value == value,
                Category.id != category_id
            )
        ).scalar_one_or_none()

    def add(self, category):
        db.session.add(category)

    def delete(self, category):
        db.session.delete(category)
        
    def get_associated_ticket_count(self, category_id):
        return db.session.execute(
            select(func.count(Ticket.id)).filter(Ticket.category_id == category_id)
        ).scalar()
