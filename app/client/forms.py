from flask_wtf import FlaskForm
from wtforms import TextAreaField, SelectField, SubmitField, StringField, RadioField
from wtforms.validators import DataRequired, Length

class CreateTicketForm(FlaskForm):
    # El campo 'category' ahora se poblará desde la ruta.
    category = SelectField('Categoría', validators=[DataRequired(message="Este campo es obligatorio")], choices=[])
    title = StringField('Título de la tarea', validators=[DataRequired(message="Este campo es obligatorio"), Length(min=5, max=100)])
    description = TextAreaField('Descripción de la tarea', validators=[DataRequired(message="Este campo es obligatorio"), Length(min=10, max=500)])
    shift = RadioField(
        'Turno',
        choices=[
            ('weekday_morning', 'Mañana'),
            ('weekday_afternoon', 'Tarde'),
            ('weekday_night', 'Noche'),
            ('weekend_morning', 'Mañana'),
            ('weekend_afternoon', 'Tarde'),
            ('weekend_night', 'Noche')
        ],
        validators=[DataRequired(message="Por favor, selecciona un turno.")]
    )
    submit = SubmitField('Crear Ticket', render_kw={"class": "btn btn-primary confirm-submit-btn"})

class ClientDescriptionForm(FlaskForm):
    new_description_text = TextAreaField('Agregar descripción/notas', validators=[DataRequired(message="Este campo es obligatorio"), Length(min=10, max=500)])
    submit = SubmitField('Agregar Nota al Ticket', render_kw={"class": "btn btn-primary confirm-submit-btn"})

class RejectTicketForm(FlaskForm):
    note = TextAreaField('Motivo del Rechazo', validators=[DataRequired(message="Este campo es obligatorio"), Length(min=10, max=500)],
                         description='Explica por qué rechazas el ticket.')
    submit = SubmitField('Rechazar Ticket', render_kw={"class": "btn btn-danger reject-ticket-confirm-btn"})
