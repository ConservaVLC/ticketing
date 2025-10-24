from flask_wtf import FlaskForm
from wtforms import TextAreaField, SelectField, SubmitField, StringField, DateField
from wtforms.validators import DataRequired, Length, Optional

class TicketEditForm(FlaskForm):
    description = TextAreaField('Descripción del Ticket', validators=[DataRequired(message="Este campo es obligatorio"), Length(min=10, max=500)])
    category = SelectField('Categoría', validators=[DataRequired(message="Este campo es obligatorio")], choices=[])
    status = SelectField('Estado del Ticket', validators=[DataRequired(message="Este campo es obligatorio")], choices=[])
    supervisor = SelectField('Supervisor Asignado', validators=[Optional()], choices=[])
    operator = SelectField('Operador Asignado', validators=[Optional()], choices=[])
    observation = TextAreaField('Observación del Supervisor', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Actualizar Ticket', render_kw={"class": "btn btn-primary confirm-submit-btn"})

class AssignTicketForm(FlaskForm):
    operator = SelectField('Asignar a:', validators=[DataRequired(message="Este campo es obligatorio")], choices=[])
    submit = SubmitField('Asignar Ticket', render_kw={"class": "btn btn-primary confirm-submit-btn"})

class TicketFilterForm(FlaskForm):
    class Meta:
        csrf = False
    ticket_id = StringField('ID', validators=[Optional(), Length(max=24)], render_kw={"placeholder": "Buscar por ID"})
    search_title = StringField('Título', validators=[Optional(), Length(max=100)], render_kw={"placeholder": "Buscar en título"})
    creator_username = StringField('Creador', validators=[Optional(), Length(max=64)], render_kw={"placeholder": "Buscar por usuario"})
    category = SelectField('Categoría', choices=[])
    status = SelectField('Estado', choices=[])
    operator_username = StringField('Operador', validators=[Optional(), Length(max=64)], render_kw={"placeholder": "Buscar por operador"})
    supervisor_username = StringField('Supervisor', validators=[Optional(), Length(max=64)], render_kw={"placeholder": "Buscar por supervisor"})
    start_date = DateField('Fecha Desde', format='%Y-%m-%d', validators=[Optional()])
    end_date = DateField('Fecha Hasta', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Aplicar Filtros')
    clear_filters = SubmitField('Limpiar Filtros')
