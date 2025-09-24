from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField
from wtforms.validators import DataRequired, Length, ValidationError
from app import mongo # Importamos mongo
from slugify import slugify

class EmptyForm(FlaskForm):
    submit = SubmitField('Submit')

class CategoryForm(FlaskForm):
    name = StringField('Nombre de la categoría', validators=[DataRequired(), Length(min=2, max=30, message='La categoría debe tener entre 2 y 30 caracteres')])
    submit = SubmitField('Guardar Categoría', render_kw={"class": "btn btn-primary confirm-submit-btn"})

    def __init__(self, original_value=None, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        self.original_value = original_value

    def validate_name(self, name):
        # La validación de unicidad se hará sobre el 'value' generado
        generated_value = slugify(name.data)
        if generated_value != self.original_value:
            category = mongo.db.categories.find_one({"value": generated_value})
            if category:
                raise ValidationError('Ya existe una categoría que genera el mismo valor interno. Por favor, elige un nombre ligeramente diferente.')
