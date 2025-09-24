from flask import render_template, flash, redirect, url_for, Response, request
from flask_login import login_required, current_user
from app.supervisor import supervisor_bp
from app import mongo
from .forms import TicketEditForm, AssignTicketForm, TicketFilterForm
from app.auth.decorators import supervisor_or_admin_required
from datetime import datetime, timezone
from bson.objectid import ObjectId
import pymongo
import logging
from io import BytesIO
from openpyxl import Workbook
from app.utils import log_ticket_history

logger = logging.getLogger(__name__)

@supervisor_bp.route('/tickets', methods=['GET', 'POST'])
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
    
    return render_template('supervisor/list_tickets.html', tickets=tickets, form=form, export_url_args=export_url_args, status_map=status_map)

@supervisor_bp.route('/export_tickets_to_xlsx', methods=['GET'])
@login_required
@supervisor_or_admin_required
def export_tickets_to_xlsx():
    # La lógica de filtrado se puede reutilizar aquí si es necesario
    try:
        tickets_to_export = list(mongo.db.tickets.find({}).sort("created_at", -1))
    except pymongo.errors.PyMongoError as e:
        logger.error(f"Error al exportar tickets: {e}")
        flash("Error al generar el reporte de tickets.", "danger")
        return redirect(url_for('supervisor_bp.list_tickets'))

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

@supervisor_bp.route('/edit_ticket/<string:ticket_id>', methods=['GET', 'POST'])
@login_required
@supervisor_or_admin_required
def edit_ticket(ticket_id):
    try:
        ticket = mongo.db.tickets.find_one({"_id": ObjectId(ticket_id)})
    except Exception as e:
        logger.error(f"Error al buscar ticket {ticket_id} para editar: {e}")
        flash("Error al cargar el ticket.", "danger")
        return redirect(url_for('supervisor_bp.list_tickets'))

    if not ticket:
        flash('Ticket no encontrado.', 'danger')
        return redirect(url_for('supervisor_bp.list_tickets'))

    form = TicketEditForm(data=ticket) # Precargar el formulario con los datos del ticket

    # Poblar SelectFields del formulario
    try:
        statuses = list(mongo.db.statuses.find().sort("name", 1))
        form.status.choices = [('', '--- Seleccione un Estado ---')] + [(s['value'], s['name']) for s in statuses]

        categories = list(mongo.db.categories.find().sort("name", 1))
        form.category.choices = [('', '--- Seleccione una Categoría ---')] + [(c['value'], c['name']) for c in categories]

        # Obtener supervisores y operadores para los SelectFields
        supervisors = list(mongo.db.personas.find({"role": {"$in": ["admin", "supervisor"]}}).sort("username", 1))
        form.supervisor.choices = [('', '--- Sin Supervisor Asignado ---')] + [(str(p['_id']), p['username']) for p in supervisors]

        operators = list(mongo.db.personas.find({"role": "operador"}).sort("username", 1))
        form.operator.choices = [('', '--- Sin Operador Asignado ---')] + [(str(p['_id']), p['username']) for p in operators]

    except pymongo.errors.PyMongoError as e:
        logger.error(f"Error al poblar SelectFields en edit_ticket: {e}")
        flash("Error al cargar opciones para el formulario.", "warning")

    # Si es GET, precargar los valores actuales del ticket en el formulario
    if request.method == 'GET':
        form.status.data = ticket.get('status_value')
        form.category.data = ticket.get('category_value')
        form.supervisor.data = str(ticket['supervisor']['user_id']) if ticket.get('supervisor') else ''
        form.operator.data = str(ticket['operator']['user_id']) if ticket.get('operator') else ''
        form.observation.data = ticket.get('observation', '')

    if form.validate_on_submit():
        try:
            update_data = {
                "description": form.description.data,
                "category_value": form.category.data,
                "status_value": form.status.data,
                "updated_at": datetime.now(timezone.utc)
            }

            # Manejar asignación de supervisor
            if form.supervisor.data:
                supervisor_obj = mongo.db.personas.find_one({"_id": ObjectId(form.supervisor.data)})
                update_data['supervisor'] = {"user_id": supervisor_obj['_id'], "username": supervisor_obj['username']}
            else:
                update_data['supervisor'] = None

            # Manejar asignación de operador
            if form.operator.data:
                operator_obj = mongo.db.personas.find_one({"_id": ObjectId(form.operator.data)})
                update_data['operator'] = {"user_id": operator_obj['_id'], "username": operator_obj['username']}
            else:
                update_data['operator'] = None

            # Manejar observación (si existe el campo)
            if 'observation' in form and form.observation.data:
                update_data['observation'] = form.observation.data
            
            mongo.db.tickets.update_one({"_id": ObjectId(ticket_id)}, {"$set": update_data})

            log_ticket_history(ticket_id, "Edición de Ticket", current_user, f"Ticket editado por {current_user.username}")

            # Lógica de envío de correos (simplificada, a refactorizar)
            # send_notification_email(...)

            flash(f'Ticket {ticket_id} actualizado exitosamente.', 'success')
            return redirect(url_for('supervisor_bp.list_tickets'))

        except Exception as e:
            logger.error(f"Error al actualizar ticket {ticket_id}: {e}", exc_info=True)
            flash('Ocurrió un error al actualizar el ticket.', 'danger')

    return render_template('supervisor/edit_ticket.html', title=f'Editar Ticket #{ticket_id}', form=form, ticket=ticket)

@supervisor_bp.route('/assign_ticket/<string:ticket_id>', methods=['GET', 'POST'])
@login_required
@supervisor_or_admin_required
def assign_ticket(ticket_id):
    try:
        ticket = mongo.db.tickets.find_one({"_id": ObjectId(ticket_id)})
    except Exception as e:
        logger.error(f"Error al buscar ticket {ticket_id} para asignar: {e}")
        flash("Error al cargar el ticket.", "danger")
        return redirect(url_for('supervisor_bp.list_tickets'))

    if not ticket:
        flash('Ticket no encontrado.', 'danger')
        return redirect(url_for('supervisor_bp.list_tickets'))

    form = AssignTicketForm()

    # Poblar SelectField de operadores
    try:
        operators = list(mongo.db.personas.find({"role": "operador"}).sort("username", 1))
        form.operator.choices = [('', '--- Seleccionar Operador ---')] + [(str(p['_id']), p['username']) for p in operators]
    except pymongo.errors.PyMongoError as e:
        logger.error(f"Error al poblar operadores en assign_ticket: {e}")
        flash("Error al cargar opciones de operador.", "warning")

    if form.validate_on_submit():
        try:
            operator_id = form.operator.data
            if not operator_id: # Si no se seleccionó operador
                flash('Por favor, selecciona un operador válido.', 'warning')
                return render_template('supervisor/assign_ticket.html', title='Asignar Ticket', form=form, ticket=ticket)

            operator_obj = mongo.db.personas.find_one({"_id": ObjectId(operator_id)})
            if not operator_obj:
                flash('Operador seleccionado no válido.', 'danger')
                return render_template('supervisor/assign_ticket.html', title='Asignar Ticket', form=form, ticket=ticket)

            assigned_status = mongo.db.statuses.find_one({"value": "in_progress"})
            if not assigned_status:
                flash('Error: El estado "En Progreso" no está configurado.', 'danger')
                return redirect(url_for('supervisor_bp.list_tickets'))
            
            update_data = {
                "operator": {"user_id": operator_obj['_id'], "username": operator_obj['username']},
                "status_value": assigned_status['value'],
                "updated_at": datetime.now(timezone.utc)
            }
            mongo.db.tickets.update_one({"_id": ObjectId(ticket_id)}, {"$set": update_data})

            log_ticket_history(ticket_id, "Asignación de Operador", current_user, f"Ticket asignado a {operator_obj['username']}")

            # --- ENVÍO DE CORREO AL OPERADOR ASIGNADO ---
            # send_notification_email(...)

            flash(f"Ticket {ticket_id} asignado a {operator_obj['username']} y estado cambiado a \"{assigned_status['name']}\".", 'success')
            return redirect(url_for('supervisor_bp.list_tickets'))

        except Exception as e:
            logger.error(f"Error al asignar ticket {ticket_id}: {e}", exc_info=True)
            flash('Ocurrió un error al asignar el ticket.', 'danger')

    return render_template('supervisor/assign_ticket.html', title='Asignar Ticket', form=form, ticket=ticket)