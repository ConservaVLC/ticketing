from flask import render_template, flash, redirect, url_for, Response, request
from flask_login import login_required, current_user
from app.admin import admin_bp
from app import mongo
from .forms import CategoryForm, EmptyForm
from app.auth.decorators import admin_required, supervisor_or_admin_required
from slugify import slugify
import logging
import pymongo
from bson.objectid import ObjectId
from datetime import datetime
from io import BytesIO
from openpyxl import Workbook
from app.supervisor.forms import TicketFilterForm # Import from supervisor for now

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

@admin_bp.route('/tickets', methods=['GET', 'POST'])
@login_required
@supervisor_or_admin_required
def list_tickets():
    logger.debug(f"request.args: {request.args}")
    form = TicketFilterForm(request.args)
    query = {}
    tickets = [] # Inicializar tickets aquí para asegurar que siempre esté definida

    # Poblar los formularios de filtro ANTES de la validación
    try:
        statuses = list(mongo.db.statuses.find().sort("name", 1))
        form.status.choices = [('', 'Todos los Estados')] + [(s['value'], s['name']) for s in statuses]
        categories = list(mongo.db.categories.find().sort("name", 1))
        form.category.choices = [('', 'Todas las Categorías')] + [(c['value'], c['name']) for c in categories]

        # Create status_map here
        status_map = {s['value']: s['name'] for s in statuses}
        logger.debug(f"status_map creado: {status_map}")

    except pymongo.errors.PyMongoError as e:
        logger.error(f"Error al poblar los filtros: {e}")
        flash("Error al cargar opciones de filtro.", "warning")
        status_map = {}

    # Lógica de filtrado adaptada para MongoDB (ejemplo básico)
    if form.validate():
        logger.debug("Formulario de filtro validado correctamente.")
        if form.status.data:
            query['status_value'] = form.status.data
            logger.debug(f"Filtro por estado: {form.status.data}")
        if form.category.data:
            query['category_value'] = form.category.data
            logger.debug(f"Filtro por categoría: {form.category.data}")

        # Filtros de texto
        if form.ticket_id.data:
            query['$expr'] = {
                '$regexMatch': {
                    'input': {'$toString': '$_id'},
                    'regex': form.ticket_id.data,
                    'options': 'i'
                }
            }
            logger.debug(f"Filtro por ID de ticket (texto): {form.ticket_id.data}")
        if form.search_title.data:
            query['title'] = {'$regex': form.search_title.data, '$options': 'i'}
            logger.debug(f"Filtro por título: {form.search_title.data}")
        if form.creator_username.data:
            query['creator.username'] = {'$regex': form.creator_username.data, '$options': 'i'}
            logger.debug(f"Filtro por nombre de creador: {form.creator_username.data}")
        if form.operator_username.data:
            query['operator.username'] = {'$regex': form.operator_username.data, '$options': 'i'}
            logger.debug(f"Filtro por nombre de operador: {form.operator_username.data}")
        if form.supervisor_username.data:
            query['supervisor.username'] = {'$regex': form.supervisor_username.data, '$options': 'i'}
            logger.debug(f"Filtro por nombre de supervisor: {form.supervisor_username.data}")

        # Filtros de fecha
        if form.start_date.data or form.end_date.data:
            date_query = {}
            start_datetime = None
            end_datetime = None

            if form.start_date.data:
                start_datetime = datetime.combine(form.start_date.data, datetime.min.time())
                logger.debug(f"Filtro por fecha de inicio (datetime naive): {start_datetime}")
            
            if form.end_date.data:
                end_datetime = datetime.combine(form.end_date.data, datetime.max.time())
                logger.debug(f"Filtro por fecha de fin (datetime naive): {end_datetime}")

            # Si solo se proporciona la fecha de inicio, filtrar por ese día completo
            if start_datetime and not end_datetime:
                end_datetime = datetime.combine(form.start_date.data, datetime.max.time())
                logger.debug(f"Ajuste: Solo fecha de inicio, fin ajustado a: {end_datetime}")
            
            # Si solo se proporciona la fecha de fin, filtrar por ese día completo
            if end_datetime and not start_datetime:
                start_datetime = datetime.combine(form.end_date.data, datetime.min.time())
                logger.debug(f"Ajuste: Solo fecha de fin, inicio ajustado a: {start_datetime}")

            if start_datetime:
                date_query['$gte'] = start_datetime
            if end_datetime:
                date_query['$lte'] = end_datetime
            
            query['created_at'] = date_query

    else:
        logger.debug(f"Errores de validación del formulario de filtro: {form.errors}")

    logger.debug(f"Consulta final de MongoDB: {query}")

    try:
        tickets = list(mongo.db.tickets.find(query).sort("created_at", -1))
        logger.info(f'Usuario {current_user.username} consultó los tickets. Se encontraron {len(tickets)} tickets.')
    except pymongo.errors.PyMongoError as e:
        logger.error(f"Error al buscar tickets para supervisor: {e}")
        flash("Error al cargar los tickets.", "danger")

    export_url_args = request.args.copy()
    
    return render_template('admin/list_tickets.html', tickets=tickets, form=form, export_url_args=export_url_args, status_map=status_map)

@admin_bp.route('/export_tickets_to_xlsx', methods=['GET'])
@login_required
@supervisor_or_admin_required
def export_tickets_to_xlsx():
    # La lógica de filtrado se puede reutilizar aquí si es necesario
    try:
        tickets_to_export = list(mongo.db.tickets.find({}).sort("created_at", -1))
    except pymongo.errors.PyMongoError as e:
        logger.error(f"Error al exportar tickets: {e}")
        flash("Error al generar el reporte de tickets.", "danger")
        return redirect(url_for('admin_bp.list_tickets')) # Redirect to admin_bp.list_tickets

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Tickets"

    headers = ['ID', 'Título', 'Descripción', 'Creado Por', 'Categoría', 'Estado', 'Fecha Creación']
    worksheet.append(headers)

    for ticket in tickets_to_export:
        row_data = [
            str(ticket['_id']),
            ticket.get('title', 'N/A'),
            ticket.get('description', 'N/A'),
            ticket.get('creator', {}).get('username', 'N/A'),
            ticket.get('category_value', 'N/A'),
            ticket.get('status_value', 'N/A'),
            ticket.get('created_at').strftime('%d/%m/%Y %H:%M') if ticket.get('created_at') else 'N/A'
        ]
        worksheet.append(row_data)

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    logger.info(f'Usuario {current_user.username} ha generado un reporte de tickets en ".xlsx"')

    return Response(
        output.read(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment;filename=tickets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"}
    )