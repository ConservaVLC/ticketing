# --- Modelos SQLAlchemy Originales (Comentados como referencia) ---
# from datetime import datetime, timezone
# from app import db
# from sqlalchemy import ForeignKey
# from sqlalchemy.orm import relationship
# from app.auth.models import Persona
#
# class Category(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(50), unique=True, nullable=False)
#     value = db.Column(db.String(50), unique=True, nullable=False)
#     tickets = db.relationship('Ticket', backref='category_obj', lazy=True)
#
#     def __repr__(self):
#         return f"<Category '{self.name}'>"
#
# class Status(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(50), unique=True, nullable=False)
#     value = db.Column(db.String(50), unique=True, nullable=False)
#     tickets_by_status = db.relationship('Ticket', backref='status_obj', lazy=True)
#
#     def __repr__(self):
#         return f"Status('{self.name}')"
#
# class Ticket(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
#     title=db.Column(db.Text, nullable=False)
#     status_id = db.Column(db.Integer, db.ForeignKey('status.id'), nullable=False, default=1)
#     description = db.Column(db.Text, nullable=False)
#     timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
#     modified_timestamp = db.Column(db.DateTime, nullable=True)
#     completed_timestamp = db.Column(db.DateTime, nullable=True)
#     observation = db.Column(db.Text, nullable=True, default="")
#     creator_id = db.Column(db.Integer, db.ForeignKey('personas.id'), nullable=False)
#     asignated_supervisor_id = db.Column(db.Integer, db.ForeignKey('personas.id'), nullable=True)
#     asignated_supervisor_obj = db.relationship('Persona', foreign_keys=[asignated_supervisor_id], backref='supervised_tickets', lazy=True)
#     asigned_operator_id = db.Column(db.Integer, db.ForeignKey('personas.id'), nullable=True)
#     asigned_operator_obj = db.relationship('Persona', foreign_keys=[asigned_operator_id], backref='assigned_operator_tickets', lazy=True)
#     creator_obj = db.relationship('Persona', foreign_keys=[creator_id], backref='created_tickets')
#
# class TicketHistory(db.Model):
#     __tablename__ = 'ticket_history'
#     id = db.Column(db.Integer, primary_key=True)
#     ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
#     # ... y muchos otros campos ...

# --- Nuevas "Clases" adaptadas para PyMongo ---
# Con PyMongo, no se suelen usar clases de modelo como con un ORM.
# Los datos se manejan como diccionarios (documentos de MongoDB).
# Estas clases son solo para mantener una estructura conceptual clara si se desea.


class Category:
    """Representación conceptual de una Categoría."""
    def __init__(self, name, value, _id=None):
        self.id = _id
        self.name = name
        self.value = value

class Status:
    """Representación conceptual de un Estado."""
    def __init__(self, name, value, _id=None):
        self.id = _id
        self.name = name
        self.value = value

class Ticket:
    """
    Representación conceptual de un Ticket.
    En la práctica, será un diccionario en la base de datos.
    """
    # Esta clase puede usarse para validación o para instanciar objetos
    # desde los diccionarios que devuelve PyMongo, pero no es obligatorio.
    pass

class TicketHistory:
    """
    Representación conceptual de una entrada de historial de Ticket.
    En la práctica, será un diccionario en la base de datos.
    """
    pass

class Task:
    """
    Representación conceptual de una Tarea.
    """
    def __init__(self, name, description, _id=None):
        self.id = _id
        self.name = name
        self.description = description
