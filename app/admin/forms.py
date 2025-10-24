from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired, Length, ValidationError
from wtforms.widgets import ListWidget, CheckboxInput
from app import mongo # Importamos mongo
from slugify import slugify
from bson.objectid import ObjectId

class EmptyForm(FlaskForm):
    submit = SubmitField('Submit')

class CategoryForm(FlaskForm):
    name = StringField('Nombre de la categoría', validators=[DataRequired(message="Este campo es obligatorio"), Length(min=2, max=30, message='La categoría debe tener entre 2 y 30 caracteres')])
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


class SupervisorAssignmentForm(FlaskForm):
    category = SelectMultipleField(
        'Categoría(s)',
        option_widget=CheckboxInput(),
        widget=ListWidget(prefix_label=False),
        validators=[DataRequired(message="Por favor, seleccione al menos una categoría.")]
    )
    shift = SelectField('Turno', validators=[DataRequired(message="Por favor, seleccione un turno.")])
    supervisor = SelectField('Supervisor', validators=[DataRequired(message="Por favor, seleccione un supervisor.")])
    submit = SubmitField('Guardar Asignación', render_kw={"class": "btn btn-primary confirm-submit-btn"})

    def __init__(self, *args, **kwargs):
        super(SupervisorAssignmentForm, self).__init__(*args, **kwargs)
        # Poblar choices dinámicamente desde la ruta
        self.category.choices = [(str(c['_id']), c['name']) for c in mongo.db.categories.find().sort("name", 1)]
        self.supervisor.choices = [("", "--- Seleccione un Supervisor ---")] + [(str(s['_id']), s['username']) for s in mongo.db.personas.find({"role": "supervisor"}).sort("username", 1)]
        # Los turnos son estáticos, pero los cargamos aquí para mantener la consistencia
        self.shift.choices = [
            ("", "--- Seleccione un Turno ---"),
            ('weekday_morning', 'Mañana (L-V)'),
            ('weekday_afternoon', 'Tarde (L-V)'),
            ('weekday_night', 'Noche (L-V)'),
            ('weekend_morning', 'Mañana (S-D)'),
            ('weekend_afternoon', 'Tarde (S-D)'),
            ('weekend_night', 'Noche (S-D)')
        ]

    def validate(self, extra_validators=None):
        if not super(SupervisorAssignmentForm, self).validate(extra_validators):
            return False

        # Validación de unicidad para cada categoría seleccionada
        for category_id_str in self.category.data:
            category_id = ObjectId(category_id_str)
            existing_assignment = mongo.db.supervisor_assignments.find_one({
                "category_id": category_id,
                "shift_value": self.shift.data
            })

            if existing_assignment:
                supervisor_id = existing_assignment.get('supervisor_id')
                supervisor = mongo.db.personas.find_one({"_id": supervisor_id})
                supervisor_name = supervisor['username'] if supervisor else 'desconocido'
                
                category = mongo.db.categories.find_one({"_id": category_id})
                category_name = category['name'] if category else 'desconocida'

                self.category.errors.append(
                    f"La categoría '{category_name}' ya tiene una asignación para este turno (asignado a '{supervisor_name}'). "
                    f"Bórrela si desea crear una nueva."
                )
                return False
        
        return True
