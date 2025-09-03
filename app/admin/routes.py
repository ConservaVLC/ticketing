from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from app.admin import admin_bp
from app import db
from app.models import Ticket
from sqlalchemy.exc import SQLAlchemyError
from .forms import CategoryForm, EmptyForm
from ..models import Ticket, Category
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from app.auth.decorators import admin_required
from slugify import slugify
import logging


logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
#               FUNCIÓN: LISTADO DE CATEGORIAS (ADMIN)
# ------------------------------------------------------------------------------
@admin_bp.route('/categories')
@login_required
@admin_required
def list_categories():
    form = EmptyForm()
    categories = db.session.execute(select(Category)).scalars().all()
    return render_template('admin/list_categories.html', title='Categories', categories=categories, form=form)

# ------------------------------------------------------------------------------
#               FUNCIÓN: CREAR UNA NUEVA CATEGORIA (ADMIN)
# ------------------------------------------------------------------------------
@admin_bp.route('/category/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_category():
    form = CategoryForm()
    if form.validate_on_submit():
        try:
            #Slugify funciona como .lower() y .replace()
            generated_value = slugify(form.name.data)

            existing_category_with_value = db.session.execute(
                select(Category).filter_by(value=generated_value)
            ).scalar_one_or_none()

            if existing_category_with_value:
                flash(f'Ya existe una categoría con el valor interno "{generated_value}" (generado a partir de "{form.name.data}"). Por favor, elija un nombre diferente que genere un valor único.', 'warning')
                return render_template('admin/create_category.html', title='Crear Categoría', form=form)

            new_category = Category(name=form.name.data, value=generated_value)
            
            db.session.add(new_category)
            db.session.commit()

            # --- Logger: INFO - Nueva categoría creada ---
            logger.info(f'Usuario {current_user.username} (ID: {current_user.id}) creó la categoría {new_category.name}.')
            flash(f'Categoría "{new_category.name}" creada exitosamente con valor interno "{new_category.value}".', 'success')
            return redirect(url_for('admin_bp.list_categories')) # Redirige a la lista de categorías
        
        except SQLAlchemyError as e:
            db.session.rollback()
            # --- Logger: ERROR - Intento de creación de categoría fallido ---
            logger.error(f'Intento de creación de categoría fallido: La categoría {new_category.name} no pudo ser creada por el usuario {current_user.username} (ID: {current_user.id})',exc_info=True)
            flash(f'Ocurrió un error al crear la categoría: {e}', 'error')
        except Exception as e:
            # --- Logger: ERROR - Error inesperado ---
            db.session.rollback()
            message=f"Ocurrió un error inesperado. Por favor, contacte a soporte. Detalles: '{e}'", 'error'
            logger.error(f'Al intentar crear la categoría: {message}',exc_info=True)
            flash(message, 'error')
    
    return render_template('admin/create_category.html', title='Crear Categoría', form=form)

# ------------------------------------------------------------------------------
#               FUNCIÓN: EDITAR UNA CATEGORIA (ADMIN)
# ------------------------------------------------------------------------------
@admin_bp.route('/category/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(category_id):
    category = db.session.execute(select(Category).filter_by(id=category_id)).scalar_one_or_none()

    if not category:
        flash('Categoría no encontrada.', 'danger')
        return redirect(url_for('admin_bp.list_categories'))

    # Inicializa el formulario, pasando el nombre original para la validación de unicidad
    # y el objeto de categoría para precargar los datos
    form = CategoryForm(original_name=category.name, obj=category)

    if form.validate_on_submit():
        try:
            category.name = form.name.data

            #Slugify funciona como .lower() y .replace()
            new_generated_value = slugify(form.name.data)

            existing_category_with_new_value = db.session.execute(
                select(Category).filter(
                    Category.value == new_generated_value,
                    Category.id != category_id # Excluye la categoría actual que estamos editando
                )
            ).scalar_one_or_none()

            if existing_category_with_new_value:
                flash(f'Ya existe otra categoría con el valor interno "{new_generated_value}" (generado a partir de "{form.name.data}"). Por favor, elija un nombre diferente que genere un valor único.', 'warning')
                # Vuelve a renderizar el formulario con el mensaje de error
                return render_template('admin/edit_category.html', title=f'Editar Categoría: {category.name}', form=form, category=category)
            
            # Si el 'value' generado es único (o es el mismo que ya tenía esta categoría), actualiza el 'value'
            category.value = new_generated_value
            
            db.session.add(category) # Añadir a la sesión para que SQLAlchemy detecte los cambios
            db.session.commit()

            # --- Logger: INFO - Categoría editada ---
            logger.info(f'Usuario {current_user.username} (ID: {current_user.id}) cambió la categoría "{category.name}" por "{new_generated_value}".')
            flash(f'Categoría "{category.name}" actualizada correctamente.', 'success')
            return redirect(url_for('admin_bp.list_categories'))

        except SQLAlchemyError as e:
            db.session.rollback()
            # --- Logger: ERROR - Intento de modificación de categoría fallido ---
            logger.error(f'Intento de modifcación de categoría fallido: La categoría {category.name} no pudo ser creada por el usuario {current_user.username} (ID: {current_user.id})',exc_info=True)
            flash(f'Ocurrió un error al modificar la categoría: {e}', 'error')
        except Exception as e:
            # --- Logger: ERROR - Error inesperado ---
            db.session.rollback()
            message=f"Ocurrió un error inesperado. Por favor, contacte a soporte. Detalles: '{e}'", 'error'
            logger.error(f'Al intentar modificar la categoría: {message}',exc_info=True)
            flash(message, 'error')

    # Si es un GET request o el formulario no es válido (en POST)
    return render_template('admin/edit_category.html', title='Editar Categoría', form=form, category=category)

# ------------------------------------------------------------------------------
#               FUNCIÓN: ELIMINAR UNA CATEGORIA (ADMIN)
# ------------------------------------------------------------------------------
@admin_bp.route('/category/<int:category_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    category = db.session.execute(select(Category).filter_by(id=category_id)).scalar_one_or_none()

    if not category:
        flash('Categoría no encontrada.', 'danger')
        return redirect(url_for('admin_bp.list_categories'))

    try:
        associated_tickets_count = db.session.execute(
            select(func.count(Ticket.id)).filter(Ticket.category_id == category.id)
        ).scalar()
        if associated_tickets_count > 0: # <-- Esto asume que Category tiene un backref 'tickets'
            # --- Logger: WARNING - Intento de borrado fallido: Existen tickets asociados a la categoría ---
            logger.warning(f'No se pudo borrar la cateogría "{category.name}" por parte del operador {current_user.username} (ID: {current_user.id}), existen tickets asociados')
            flash(f'No se puede borrar la cateogría "{category.name}". Existen tickets asignados a esta categoría. Por favor elimine o reasigne estos tickets antes de continuar.', 'warning')
            return redirect(url_for('admin_bp.list_categories'))

        db.session.delete(category)
        db.session.commit()
        # --- Logger: INFO - Categoría borrada ---
        logger.info(f'Usuario {current_user.username} (ID: {current_user.id}) borró la categoría "{category.name}".')
        flash(f'Category "{category.name}"Borrado exitoso.', 'success')
        
    except SQLAlchemyError as e:
        db.session.rollback()
        # --- Logger: ERROR - Intento de borrado de categoría fallido ---
        logger.error(f'Intento de borrado de categoría fallido: La categoría {category.name} no pudo ser borrada por el usuario {current_user.username} (ID: {current_user.id})',exc_info=True)
        flash(f'Ocurrió un error al modificar la categoría: {e}', 'error')
    except Exception as e:
        # --- Logger: ERROR - Error inesperado ---
        db.session.rollback()
        message=f"Ocurrió un error inesperado. Por favor, contacte a soporte. Detalles: '{e}'", 'error'
        logger.error(f'Al intentar borrar la categoría: {message}',exc_info=True)
        flash(message, 'error')

    return redirect(url_for('admin_bp.list_categories'))