from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from app.admin import admin_bp
from app import db
from sqlalchemy.exc import SQLAlchemyError
from .forms import CategoryForm, EmptyForm
from ..models import Category # Se mantiene para la creación de instancias
from app.auth.decorators import admin_required
from app.repositories import SQLCategoryRepository # Importar el nuevo repositorio
from slugify import slugify
import logging

logger = logging.getLogger(__name__)

# Instanciar el repositorio
category_repository = SQLCategoryRepository()

# ------------------------------------------------------------------------------
#               FUNCIÓN: LISTADO DE CATEGORIAS (ADMIN)
# ------------------------------------------------------------------------------
@admin_bp.route('/categories')
@login_required
@admin_required
def list_categories():
    form = EmptyForm()
    categories = category_repository.get_all()
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
            generated_value = slugify(form.name.data)

            existing_category_with_value = category_repository.find_by_value(generated_value)

            if existing_category_with_value:
                flash(f'Ya existe una categoría con el valor interno "{generated_value}" (generado a partir de "{form.name.data}"). Por favor, elija un nombre diferente que genere un valor único.', 'warning')
                return render_template('admin/create_category.html', title='Crear Categoría', form=form)

            new_category = Category(name=form.name.data, value=generated_value)
            
            category_repository.add(new_category)
            db.session.commit()

            # --- Logger: INFO - Nueva categoría creada ---
            logger.info(f'Usuario {current_user.username} (ID: {current_user.id}) creó la categoría {new_category.name}.')
            flash(f'Categoría "{new_category.name}" creada exitosamente con valor interno "{new_category.value}".', 'success')
            return redirect(url_for('admin_bp.list_categories'))
        
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
    category = category_repository.find_by_id(category_id)

    if not category:
        flash('Categoría no encontrada.', 'danger')
        return redirect(url_for('admin_bp.list_categories'))

    form = CategoryForm(original_name=category.name, obj=category)

    if form.validate_on_submit():
        try:
            category.name = form.name.data
            new_generated_value = slugify(form.name.data)

            existing_category_with_new_value = category_repository.find_by_value_and_not_id(new_generated_value, category_id)

            if existing_category_with_new_value:
                flash(f'Ya existe otra categoría con el valor interno "{new_generated_value}" (generado a partir de "{form.name.data}"). Por favor, elija un nombre diferente que genere un valor único.', 'warning')
                return render_template('admin/edit_category.html', title=f'Editar Categoría: {category.name}', form=form, category=category)
            
            category.value = new_generated_value
            
            category_repository.add(category)
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

    return render_template('admin/edit_category.html', title='Editar Categoría', form=form, category=category)

# ------------------------------------------------------------------------------
#               FUNCIÓN: ELIMINAR UNA CATEGORIA (ADMIN)
# ------------------------------------------------------------------------------
@admin_bp.route('/category/<int:category_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    category = category_repository.find_by_id(category_id)

    if not category:
        flash('Categoría no encontrada.', 'danger')
        return redirect(url_for('admin_bp.list_categories'))

    try:
        associated_tickets_count = category_repository.get_associated_ticket_count(category.id)
        if associated_tickets_count > 0:
            # --- Logger: WARNING - Intento de borrado fallido: Existen tickets asociados a la categoría ---
            logger.warning(f'No se pudo borrar la cateogría "{category.name}" por parte del operador {current_user.username} (ID: {current_user.id}), existen tickets asociados')
            flash(f'No se puede borrar la cateogría "{category.name}". Existen tickets asignados a esta categoría. Por favor elimine o reasigne estos tickets antes de continuar.', 'warning')
            return redirect(url_for('admin_bp.list_categories'))

        category_repository.delete(category)
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
