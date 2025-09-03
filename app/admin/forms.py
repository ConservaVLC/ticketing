from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField
from wtforms.validators import DataRequired, Length, ValidationError
from app import db 
from ..models import Category

# FORMULARIO VACÍO PARA TRATAMIENTO DE 'CSRF'
class EmptyForm(FlaskForm):
    submit = SubmitField('Submit')

# FORUMLARIO PARA EDICIÓN DE CATEGORÍAS
class CategoryForm(FlaskForm):
    name = StringField('Nombre de la categoría', validators=[DataRequired(), Length(min=2, max=30, message='La categoría debe tener entre 2 y 30 caracteres')])
    submit = SubmitField('Guardar Categoría', render_kw={"class": "btn btn-primary confirm-submit-btn"})

    # Para la validación de unicidad en la edición
    def __init__(self, original_name=None, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        from sqlalchemy import select # Importar aquí para evitar posibles importaciones circulares
        if name.data != self.original_name: # Solo validar si el nombre ha cambiado
            category = db.session.execute(select(Category).filter_by(name=name.data)).scalar_one_or_none()
            if category:
                raise ValidationError('Esta categoría ya existe')