from datetime import datetime, timezone
from app import db
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from app.auth.models import Persona


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(50), unique=True, nullable=False)

    # Relación uno-a-muchos: Una categoría puede tener muchos tickets
    # 'tickets' te permite acceder a todos los tickets de una categoría:
    # mi_categoria.tickets
    # 'backref='category_obj'' crea una propiedad inversa en Ticket llamada 'category_obj'
    # ticket.category_obj te dará el objeto Category al que pertenece el ticket.
    tickets = db.relationship('Ticket', backref='category_obj', lazy=True)

    def __repr__(self):
        return f"<Category '{self.name}'>"


class Status(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(50), unique=True, nullable=False)

    # Relación inversa: Permite acceder a los tickets asociados a un estado desde el objeto Status
    # status_obj es la relación que usas en Ticket.
    tickets_by_status = db.relationship('Ticket', backref='status_obj', lazy=True)

    def __repr__(self):
        return f"Status('{self.name}')"


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    title=db.Column(db.Text, nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('status.id'), nullable=False, default=1)
    description = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    modified_timestamp = db.Column(db.DateTime, nullable=True)
    completed_timestamp = db.Column(db.DateTime, nullable=True)
    observation = db.Column(db.Text, nullable=True, default="")
    creator_id = db.Column(db.Integer, db.ForeignKey('personas.id'), nullable=False)
    
    # Asignated Supervisor: Ahora es una clave foránea al ID de la Persona
    # Es nullable=True porque un ticket puede no tener supervisor asignado inicialmente
    asignated_supervisor_id = db.Column(db.Integer, db.ForeignKey('personas.id'), nullable=True)
    # Define la relación con el modelo Persona para el supervisor asignado
    # backref='supervised_tickets' significa que desde un objeto Persona, puedes acceder a persona.supervised_tickets
    asignated_supervisor_obj = db.relationship(
        'Persona', 
        foreign_keys=[asignated_supervisor_id], 
        backref='supervised_tickets', 
        lazy=True # Carga los datos del supervisor cuando se accede a asignated_supervisor_obj
    )

    # Asigned Operator: También una clave foránea al ID de la Persona
    asigned_operator_id = db.Column(db.Integer, db.ForeignKey('personas.id'), nullable=True)
    # Define la relación con el modelo Persona para el operador asignado
    asigned_operator_obj = db.relationship(
        'Persona', 
        foreign_keys=[asigned_operator_id], 
        backref='assigned_operator_tickets', 
        lazy=True # Carga los datos del operador cuando se accede a asigned_operator_obj
    )

        # Esta es la relación que crea el atributo 'creator_obj' en tu objeto Ticket.
    # 'Persona' es el nombre del modelo con el que se relaciona.
    # foreign_keys=[creator_id] especifica qué columna en Ticket es la clave foránea para esta relación.
    # backref='created_tickets' (opcional pero muy útil): Permite, desde un objeto Persona,
    # acceder a una lista de todos los tickets que ha creado esa persona (ej. `persona.created_tickets`).
    creator_obj = db.relationship(
         'Persona', 
         foreign_keys=[creator_id], 
         backref='created_tickets')
    

def __repr__(self):
        status_name = self.status_obj.name if self.status_obj else 'Desconocido'
        supervisor_name = self.asignated_supervisor_obj.username if self.asignated_supervisor_obj else 'N/A'
        operator_name = self.asigned_operator_obj.username if self.asigned_operator_obj else 'N/A'
        category_name = self.category_obj.name if self.category_obj else 'Desconocida'
        # --- AÑADE ESTA LÍNEA ---
        creator_name = self.creator_obj.username if self.creator_obj else 'Desconocido' # Aquí accedes al username del creador

        return (f"<Ticket {self.id} | Desc: {self.description[:30]}... | Cat: {category_name} | "
                f"Estado: {status_name} | Supervisor: {supervisor_name} | Operador: {operator_name} | "
                f"Creador: {creator_name}>")
        
class TicketHistory(db.Model):
    __tablename__ = 'ticket_history' # Nombre explícito de la tabla

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)

    # Campos para almacenar el estado PREVIO y NUEVO de los atributos clave del ticket
    # Usamos ID para Category, Status, Persona y luego relaciones para obtener nombres si es necesario
    previous_category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    new_category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)

    previous_status_id = db.Column(db.Integer, db.ForeignKey('status.id'), nullable=True)
    new_status_id = db.Column(db.Integer, db.ForeignKey('status.id'), nullable=True)

    previous_description = db.Column(db.Text, nullable=True) # Almacena el texto completo de la descripción
    new_description = db.Column(db.Text, nullable=True)

    previous_observation = db.Column(db.Text, nullable=True)
    new_observation = db.Column(db.Text, nullable=True)
    
    previous_supervisor_id = db.Column(db.Integer, db.ForeignKey('personas.id'), nullable=True)
    new_supervisor_id = db.Column(db.Integer, db.ForeignKey('personas.id'), nullable=True)

    previous_operator_id = db.Column(db.Integer, db.ForeignKey('personas.id'), nullable=True)
    new_operator_id = db.Column(db.Integer, db.ForeignKey('personas.id'), nullable=True)

    # Metadatos del registro de historial
    change_timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    changed_by_id = db.Column(db.Integer, db.ForeignKey('personas.id'), nullable=False) # Quién realizó el cambio
    change_type = db.Column(db.String(255), nullable=False) # Ej: 'Creación', 'Edición', 'Cambio de Estado', 'Asignación'
    change_details = db.Column(db.Text, nullable=True) # Un resumen descriptivo de lo que cambió (ej. "Estado de 'Pendiente' a 'En Progreso'")

    # Relaciones para facilitar el acceso a los objetos relacionados desde el historial
    ticket = db.relationship('Ticket', backref=db.backref('history', lazy=True, order_by=change_timestamp)) # Un ticket puede tener muchos registros de historial

    changed_by = db.relationship('Persona', foreign_keys=[changed_by_id], backref='ticket_history_entries_made', lazy=True)
    
    # Relaciones para acceder a los objetos de Category/Status/Persona directamente desde los IDs históricos
    prev_category = db.relationship('Category', foreign_keys=[previous_category_id], remote_side=[Category.id], lazy=True)
    new_category = db.relationship('Category', foreign_keys=[new_category_id], remote_side=[Category.id], lazy=True)
    
    prev_status = db.relationship('Status', foreign_keys=[previous_status_id], remote_side=[Status.id], lazy=True)
    new_status = db.relationship('Status', foreign_keys=[new_status_id], remote_side=[Status.id], lazy=True)

    prev_supervisor = db.relationship('Persona', foreign_keys=[previous_supervisor_id], remote_side=[Persona.id], lazy=True)
    new_supervisor = db.relationship('Persona', foreign_keys=[new_supervisor_id], remote_side=[Persona.id], lazy=True)

    prev_operator = db.relationship('Persona', foreign_keys=[previous_operator_id], remote_side=[Persona.id], lazy=True)
    new_operator = db.relationship('Persona', foreign_keys=[new_operator_id], remote_side=[Persona.id], lazy=True)

    def __repr__(self):
        return (f"<TicketHistory {self.id} | Ticket ID: {self.ticket_id} | Type: {self.change_type} | "
                f"Changed by: {self.changed_by.username if self.changed_by else 'N/A'} at {self.change_timestamp.strftime('%Y-%m-%d %H:%M') if self.change_timestamp else 'N/A'}>")

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Task {self.id}: {self.name}>"