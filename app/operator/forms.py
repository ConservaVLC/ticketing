from flask_wtf import FlaskForm
from wtforms import TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional
from app import db 
from ..models import Status

class OperatorTicketForm(FlaskForm):
    # Campo para cambiar el estado del ticket
    status = SelectField('Cambiar Estado', coerce=int, validators=[DataRequired()])
    
    # Campo para notas del operador (opcional, ya que puede que no siempre necesiten añadir notas)
    operator_notes = TextAreaField('Notas del Operador', validators=[Optional(), Length(max=500)]) # Optional() permite que esté vacío

    submit = SubmitField('Actualizar Ticket', render_kw={"class": "btn btn-primary confirm-submit-btn"})

    def __init__(self, *args, **kwargs):
        super(OperatorTicketForm, self).__init__(*args, **kwargs)
        # Poblar las opciones del SelectField 'status'
        # Podrías filtrar aquí los estados que un operador puede seleccionar (ej. no a 'Cerrado' directamente desde 'Pendiente')
        valid_statuses = db.session.execute(db.select(Status)).scalars().all()
        self.status.choices = [(s.id, s.name) for s in valid_statuses]