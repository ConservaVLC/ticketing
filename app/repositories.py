from app import db
from app.auth.models import Persona, Role
from app.models import Category, Ticket, Status, TicketHistory
from sqlalchemy import or_, select, func
from app.utils import get_filtered_tickets_query

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

    def save(self, user):
        raise NotImplementedError

    def find_supervisors_by_username_and_role(self, usernames, role_ids):
        raise NotImplementedError

    def find_by_username(self, username):
        raise NotImplementedError

    def find_by_role_ids(self, role_ids):
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

    def find_by_name(self, name):
        raise NotImplementedError

    def add(self, category):
        raise NotImplementedError

    def delete(self, category):
        raise NotImplementedError
        
    def get_associated_ticket_count(self, category_id):
        raise NotImplementedError

class StatusRepository:
    """Define el contrato para operaciones de datos de estados."""
    def find_by_value(self, value):
        raise NotImplementedError

    def get_all(self):
        raise NotImplementedError

    def find_by_id(self, status_id):
        raise NotImplementedError

class TicketRepository:
    """Define el contrato para operaciones de datos de tickets."""
    def add(self, ticket):
        raise NotImplementedError

    def find_by_id(self, ticket_id):
        raise NotImplementedError

    def find_by_id_and_creator(self, ticket_id, creator_id):
        raise NotImplementedError

    def get_filtered_tickets(self, form, filter_by_user_role):
        raise NotImplementedError
        
    def save(self, ticket):
        raise NotImplementedError


class TicketHistoryRepository:
    """Define el contrato para operaciones de datos de historial de tickets."""
    def find_by_ticket_id(self, ticket_id):
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

    def save(self, user):
        db.session.add(user)

    def find_supervisors_by_username_and_role(self, usernames, role_ids):
        return db.session.execute(
            select(Persona).filter(Persona.username.in_(usernames),
                                 Persona.role_id.in_(role_ids))).scalars().all()

    def find_by_username(self, username):
        return Persona.query.filter_by(username=username).first()

    def find_by_role_ids(self, role_ids):
        return db.session.execute(select(Persona).filter(Persona.role_id.in_(role_ids))).scalars().all()

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

    def find_by_name(self, name):
        return db.session.execute(select(Category).filter_by(name=name)).scalar_one_or_none()

    def add(self, category):
        db.session.add(category)

    def delete(self, category):
        db.session.delete(category)
        
    def get_associated_ticket_count(self, category_id):
        return db.session.execute(
            select(func.count(Ticket.id)).filter(Ticket.category_id == category_id)
        ).scalar()

class SQLStatusRepository(StatusRepository):
    """Implementación concreta del repositorio de estados para SQLAlchemy."""
    def find_by_value(self, value):
        return db.session.execute(select(Status).filter_by(value=value)).scalar_one_or_none()

    def get_all(self):
        return db.session.execute(select(Status)).scalars().all()

    def find_by_id(self, status_id):
        return db.session.execute(select(Status).filter_by(id=status_id)).scalar_one_or_none()

class SQLTicketRepository(TicketRepository):
    """Implementación concreta del repositorio de tickets para SQLAlchemy."""
    def add(self, ticket):
        db.session.add(ticket)

    def find_by_id(self, ticket_id):
        return db.session.execute(select(Ticket).filter_by(id=ticket_id)).scalar_one_or_none()

    def find_by_id_and_creator(self, ticket_id, creator_id):
        return db.session.execute(
            select(Ticket).filter_by(id=ticket_id, creator_id=creator_id)
        ).scalar_one_or_none()

    def get_filtered_tickets(self, form, filter_by_user_role):
        query = get_filtered_tickets_query(form=form, filter_by_user_role=filter_by_user_role)
        return db.session.execute(
            query.order_by(Ticket.timestamp.desc())
        ).scalars().all()
        
    def save(self, ticket):
        db.session.add(ticket)


class SQLTicketHistoryRepository(TicketHistoryRepository):
    """Implementación concreta del repositorio de historial de tickets para SQLAlchemy."""
    def find_by_ticket_id(self, ticket_id):
        return db.session.execute(
            select(TicketHistory)
            .filter_by(ticket_id=ticket_id)
            .order_by(TicketHistory.change_timestamp.desc())
        ).scalars().all()
