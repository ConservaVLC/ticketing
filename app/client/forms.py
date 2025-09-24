from flask_wtf import FlaskForm
from wtforms import TextAreaField, SelectField, SubmitField, StringField
from wtforms.validators import DataRequired, Length

class TicketForm(FlaskForm):
    # El campo 'category' ahora se poblará desde la ruta.
    category = SelectField('Categoría', validators=[DataRequired()], choices=[])
    title = StringField('Título de la tarea', validators=[DataRequired(), Length(min=5, max=100)])
    description = TextAreaField('Descripción de la tarea', validators=[DataRequired(), Length(min=10, max=500)])
    submit = SubmitField('Crear Ticket', render_kw={"class": "btn btn-primary confirm-submit-btn"})

class ClientDescriptionForm(FlaskForm):
    new_description_text = TextAreaField('Agregar descripción/notas', validators=[DataRequired(), Length(min=10, max=500)])
    submit = SubmitField('Agregar Nota al Ticket', render_kw={"class": "btn btn-primary confirm-submit-btn"})

class RejectTicketForm(FlaskForm):
    note = TextAreaField('Motivo del Rechazo', validators=[DataRequired(), Length(min=10, max=500)],
                         description='Explica por qué rechazas el ticket.')
    submit = SubmitField('Rechazar Ticket', render_kw={"class": "btn btn-danger reject-ticket-confirm-btn"})
