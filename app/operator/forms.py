from flask_wtf import FlaskForm
from wtforms import TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

class OperatorTicketForm(FlaskForm):
    # El campo 'status' ahora se poblará desde la ruta.
    status = SelectField('Cambiar Estado', validators=[DataRequired()], choices=[])
    operator_notes = TextAreaField('Notas del Operador', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Actualizar Ticket', render_kw={"class": "btn btn-primary confirm-submit-btn"})
