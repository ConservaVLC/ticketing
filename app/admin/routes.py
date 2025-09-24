from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from app.admin import admin_bp
from app import mongo
from .forms import CategoryForm, EmptyForm
from app.auth.decorators import admin_required
from slugify import slugify
import logging
import pymongo
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)

@admin_bp.route('/categories')
@login_required
@admin_required
def list_categories():
    form = EmptyForm()
    try:
        categories = list(mongo.db.categories.find().sort("name", 1))
    except pymongo.errors.PyMongoError as e:
        logger.error(f"Error al cargar categorías: {e}")
        flash("Error al cargar las categorías.", "danger")
        categories = []
    return render_template('admin/list_categories.html', title='Categorías', categories=categories, form=form)

@admin_bp.route('/category/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_category():
    form = CategoryForm()
    if form.validate_on_submit():
        try:
            generated_value = slugify(form.name.data)
            existing = mongo.db.categories.find_one({"value": generated_value})
            if existing:
                flash(f'Ya existe una categoría con el valor interno "{generated_value}".', 'warning')
                return render_template('admin/create_category.html', title='Crear Categoría', form=form)

            new_category = {"name": form.name.data, "value": generated_value}
            mongo.db.categories.insert_one(new_category)
            
            logger.info(f'Usuario {current_user.username} creó la categoría {form.name.data}.')
            flash(f'Categoría "{form.name.data}" creada exitosamente.', 'success')
            return redirect(url_for('admin_bp.list_categories'))
        except pymongo.errors.PyMongoError as e:
            logger.error(f"Error al crear categoría: {e}", exc_info=True)
            flash('Ocurrió un error al crear la categoría.', 'danger')
    
    return render_template('admin/create_category.html', title='Crear Categoría', form=form)

@admin_bp.route('/category/<string:category_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(category_id):
    try:
        category = mongo.db.categories.find_one({"_id": ObjectId(category_id)})
    except Exception as e:
        logger.error(f"Error al buscar categoría {category_id}: {e}")
        flash("Error al cargar la categoría.", "danger")
        return redirect(url_for('admin_bp.list_categories'))

    if not category:
        flash('Categoría no encontrada.', 'danger')
        return redirect(url_for('admin_bp.list_categories'))

    form = CategoryForm(data=category)

    if form.validate_on_submit():
        try:
            new_value = slugify(form.name.data)
            # Comprobar si el nuevo 'value' ya existe en otro documento
            existing = mongo.db.categories.find_one({"value": new_value, "_id": {"$ne": ObjectId(category_id)}})
            if existing:
                flash(f'Ya existe otra categoría con el valor interno "{new_value}".', 'warning')
                return render_template('admin/edit_category.html', title='Editar Categoría', form=form, category=category)

            update_data = {"$set": {"name": form.name.data, "value": new_value}}
            mongo.db.categories.update_one({"_id": ObjectId(category_id)}, update_data)
            
            logger.info(f'Usuario {current_user.username} actualizó la categoría {form.name.data}.')
            flash(f'Categoría "{form.name.data}" actualizada correctamente.', 'success')
            return redirect(url_for('admin_bp.list_categories'))
        except pymongo.errors.PyMongoError as e:
            logger.error(f"Error al actualizar categoría: {e}", exc_info=True)
            flash('Ocurrió un error al actualizar la categoría.', 'danger')

    return render_template('admin/edit_category.html', title='Editar Categoría', form=form, category=category)

@admin_bp.route('/category/<string:category_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    try:
        # Comprobar si algún ticket usa esta categoría
        ticket_using_category = mongo.db.tickets.find_one({"category_value": mongo.db.categories.find_one({"_id": ObjectId(category_id)})['value']})
        if ticket_using_category:
            flash('No se puede borrar la categoría porque está siendo usada por al menos un ticket.', 'warning')
            return redirect(url_for('admin_bp.list_categories'))

        result = mongo.db.categories.delete_one({"_id": ObjectId(category_id)})
        if result.deleted_count == 1:
            flash('Categoría borrada exitosamente.', 'success')
        else:
            flash('No se encontró la categoría para borrar.', 'warning')
    except Exception as e:
        logger.error(f"Error al borrar categoría: {e}", exc_info=True)
        flash('Ocurrió un error al borrar la categoría.', 'danger')

    return redirect(url_for('admin_bp.list_categories'))