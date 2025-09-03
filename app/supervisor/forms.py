from flask_wtf import FlaskForm
from wtforms import TextAreaField, SelectField, SubmitField, StringField, DateField
from wtforms.validators import DataRequired, Length, Optional
from app import db 
from ..models import Status, Category
from app.auth.models import Persona


# --- Formulario para EDITAR/GESTIONAR un Ticket existente ---
class TicketEditForm(FlaskForm):
    # Campos existentes para el creador y descripción
    description = TextAreaField('Descripción del Ticket', validators=[DataRequired(), Length(min=10, max=500)])
    
    # Campo para la categoría (SelectField)
    category = SelectField('Categoría', coerce=int, validators=[DataRequired()])
    
    # Campos para el administrador: Estado, Supervisor, Operador, Notas Internas, Observación del Supervisor
    status = SelectField('Estado del Ticket', coerce=int, validators=[DataRequired()])
    supervisor = SelectField('Supervisor Asignado', coerce=int, validators=[Optional()]) # Optional para permitir 'N/A'
    operator = SelectField('Operador Asignado', coerce=int, validators=[Optional()]) # Optional para permitir 'N/A'

    observation = TextAreaField('Observación del Supervisor', validators=[Optional(), Length(max=1000)])

    submit = SubmitField('Actualizar Ticket', render_kw={"class": "btn btn-primary confirm-submit-btn"})

    def __init__(self, *args, **kwargs):
        super(TicketEditForm, self).__init__(*args, **kwargs)
        
        # Poblar opciones para la Categoría
        categories = db.session.execute(db.select(Category)).scalars().all()
        self.category.choices = [(c.id, c.name) for c in categories]

        # Poblar opciones para el Estado
        statuses = db.session.execute(db.select(Status)).scalars().all()
        self.status.choices = [(s.id, s.name) for s in statuses]
        
        # Poblar opciones para el Supervisor (filtrar por rol 'supervisor'(4) o 'admin'(1))
        supervisors = db.session.execute(db.select(Persona).filter(Persona.role_id.in_([1, 4]))).scalars().all()
        self.supervisor.choices = [(p.id, p.username) for p in supervisors]
        self.supervisor.choices.insert(0, (0, '--- Sin Supervisor Asignado ---')) # Opción para desasignar o no asignar
        
        # Poblar opciones para el Operador (filtrar por rol 'operator'(6) o 'cliente'(11))
        operators = db.session.execute(db.select(Persona).filter(Persona.role_id.in_([6,11]))).scalars().all()
        self.operator.choices = [(p.id, p.username) for p in operators]
        self.operator.choices.insert(0, (0, '--- Sin Operador Asignado ---')) # Opción para desasignar o no asignar

# --- Formulario para ASIGNAR un Ticket existente ---

class AssignTicketForm(FlaskForm):
    # Este SelectField se poblará dinámicamente en la ruta
    operator = SelectField('Asignar a:', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Asignar Ticket', render_kw={"class": "btn btn-primary confirm-submit-btn"})

    def __init__(self, *args, **kwargs):
        super(AssignTicketForm, self).__init__(*args, **kwargs)
        # Poblar las opciones del SelectField con usuarios de la base de datos
        # Puedes filtrar por rol si solo quieres asignar a 'operadores' o 'usuarios'
        # Por ahora, traeremos todos los usuarios (excepto supervisores y admins si quieres)
        
        # Ejemplo: traer solo usuarios con rol 'user' u 'operator'
        users = db.session.execute(
            db.select(Persona).filter(Persona.role_id.in_([4, 6])) # Ajusta los roles según tu necesidad
        ).scalars().all()
        
        # Las opciones deben ser una lista de tuplas: (valor, etiqueta)
        # El valor será el ID del usuario, la etiqueta será su nombre de usuario o nombre completo
        self.operator.choices = [(user.id, user.username) for user in users]
        # O si prefieres nombre completo: [(user.id, f"{user.first_name} {user.last_name}") for user in users]
        
        # Añadir una opción por defecto "Seleccionar operador..."
        self.operator.choices.insert(0, (0, '--- Seleccionar Operador ---')) # ID 0 como valor no válido


class TicketFilterForm(FlaskForm):
    # Campos de búsqueda de texto para cada columna
    ticket_id = StringField('ID', validators=[Optional(), Length(max=10)], render_kw={"placeholder": "Buscar por ID"})
    search_title = StringField('Título', validators=[Optional(), Length(max=100)], render_kw={"placeholder": "Buscar en título"})
    creator_obj = StringField('Creador', validators=[Optional(), Length(max=64)], render_kw={"placeholder": "Buscar por usuario"})
    category_name = StringField('Categoría', validators=[Optional(), Length(max=100)], render_kw={"placeholder": "Buscar por categoría"})
    status_name = StringField('Estado', validators=[Optional(), Length(max=100)], render_kw={"placeholder": "Buscar por estado"})
    operator_username = StringField('Operador', validators=[Optional(), Length(max=64)], render_kw={"placeholder": "Buscar por operador"})
    supervisor_username = StringField('Supervisor', validators=[Optional(), Length(max=64)], render_kw={"placeholder": "Buscar por supervisor"})
    start_date = DateField('Fecha Desde', format='%Y-%m-%d', validators=[Optional()])
    end_date = DateField('Fecha Hasta', format='%Y-%m-%d', validators=[Optional()])
    
    # Mantenemos los botones de acción del formulario
    submit = SubmitField('Aplicar Filtros')
    clear_filters = SubmitField('Limpiar Filtros')



            


