from flask_wtf import FlaskForm
from wtforms import TextAreaField, SelectField, SubmitField, StringField
from wtforms.validators import DataRequired, Length
from app import db 
from app.models import Category
from flask import current_app
from app.repositories import SQLCategoryRepository

class TicketForm(FlaskForm):

    category = SelectField('Categoría', validators=[DataRequired()])
    title= StringField('Título de la tarea', validators=[DataRequired(), Length(min=5, max=100)])
    description = TextAreaField('Descripción de la tarea', validators=[DataRequired(), Length(min=10, max=500)])
    
    submit = SubmitField('Crear Ticket', render_kw={"class": "btn btn-primary confirm-submit-btn"})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Poblar las opciones del SelectField 'category' desde la base de datos
        with current_app.app_context(): # Asegura que estamos en un contexto de aplicación
            category_repository = SQLCategoryRepository()
            # Las opciones son tuplas (valor_interno, nombre_visible)
            self.category.choices = [(c.value, c.name) for c in category_repository.get_all()]

# --- Formulario para agregar nota SOLO PARA EL PERFIL "CLIENTE" un Ticket existente ---
class ClientDescriptionForm(FlaskForm):
    # Campo para que el cliente agregue texto a la descripción
    new_description_text = TextAreaField('Agregar descripción/notas', validators=[DataRequired(), Length(min=10, max=500)])
    submit = SubmitField('Agregar Nota al Ticket', render_kw={"class": "btn btn-primary confirm-submit-btn"})

class RejectTicketForm(FlaskForm):
    note = TextAreaField('Motivo del Rechazo', validators=[DataRequired(), Length(min=10, max=500)],
                         description='Explica por qué rechazas el ticket.')
    submit = SubmitField('Rechazar Ticket', render_kw={"class": "btn btn-danger reject-ticket-confirm-btn"})