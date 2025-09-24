from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from app.operator import operator_bp
from app import mongo
from app.supervisor.forms import TicketFilterForm
from app.operator.forms import OperatorTicketForm
from datetime import datetime, timezone
from app.auth.decorators import operador_required
import logging
from bson.objectid import ObjectId
import pymongo
from app.utils import log_ticket_history

logger = logging.getLogger(__name__)

@operator_bp.route('/operator_tickets', methods=['GET', 'POST'])
@login_required
@operador_required
def operator_tickets():
    form = TicketFilterForm(request.args)
    query = {"operator.user_id": ObjectId(current_user.id)}

    # Aquí se añadiría la lógica de filtrado del formulario si es necesario

    try:
        tickets = list(mongo.db.tickets.find(query).sort("created_at", -1))
        logger.info(f'Usuario {current_user.username} consultó sus tickets asignados. Se encontraron {len(tickets)} tickets.')
    except pymongo.errors.PyMongoError as e:
        logger.error(f"Error al buscar tickets para el operador {current_user.username}: {e}")
        flash("Error al cargar los tickets asignados.", "danger")
        tickets = []

    # Poblar los formularios de filtro (solo categorías y estados)
    try:
        statuses = list(mongo.db.statuses.find().sort("name", 1))
        form.status.choices = [('', 'Todos los Estados')] + [(s['value'], s['name']) for s in statuses]
        categories = list(mongo.db.categories.find().sort("name", 1))
        form.category.choices = [('', 'Todas las Categorías')] + [(c['value'], c['name']) for c in categories]

        # Crear status_map para la plantilla
        status_map = {s['value']: s['name'] for s in statuses}

    except pymongo.errors.PyMongoError as e:
        logger.error(f"Error al poblar los filtros: {e}")
        flash("Error al cargar opciones de filtro.", "warning")
        status_map = {}

    return render_template('operator/operator_tickets.html', title='Mis Tickets Asignados', tickets=tickets, form=form, status_map=status_map)

@operator_bp.route('/operator_ticket_detail/<string:ticket_id>', methods=['GET', 'POST'])
@login_required
@operador_required
def operator_ticket_detail(ticket_id):
    try:
        ticket = mongo.db.tickets.find_one({"_id": ObjectId(ticket_id), "operator.user_id": ObjectId(current_user.id)})
    except Exception as e:
        logger.error(f"Error al buscar ticket {ticket_id} para detalle: {e}")
        flash("Error al cargar el ticket.", "danger")
        return redirect(url_for('operator_bp.operator_tickets'))

    if not ticket:
        flash('Ticket no encontrado o no asignado a ti.', 'danger')
        return redirect(url_for('operator_bp.operator_tickets'))

    # Definir los estados en los que el ticket es editable para el operador
    editable_status_values = ['pending', 'rejected', 'in_progress']
    is_ticket_editable_by_operator = (ticket['status_value'] in editable_status_values)

    # Definir los estados a los que el operador puede cambiar el ticket
    assignable_status_values = ['completed', 'cancelled']

    logger.debug(f"DEBUG: Ticket status_value: {ticket['status_value']}, is_ticket_editable_by_operator: {is_ticket_editable_by_operator}")

    form = OperatorTicketForm(data=ticket)

    # Poblar SelectField de estados
    try:
        statuses = list(mongo.db.statuses.find().sort("name", 1))
        # Filtrar estados permitidos para el operador
        form.status.choices = [('', '--- Seleccione un Estado ---')] + [(s['value'], s['name']) for s in statuses if s['value'] in assignable_status_values]
        status_map = {s['value']: s['name'] for s in statuses}
    except pymongo.errors.PyMongoError as e:
        logger.error(f"Error al poblar estados en operator_ticket_detail: {e}")
        flash("Error al cargar opciones de estado.", "warning")
        status_map = {}

    # Si es GET, precargar los valores actuales del ticket en el formulario
    if request.method == 'GET':
        form.status.data = ticket.get('status_value')
        form.operator_notes.data = ticket.get('observation', '') # Si hay un campo de observación

    if form.validate_on_submit():
        try:
            new_status_value = form.status.data
            update_data = {
                "status_value": new_status_value,
                "updated_at": datetime.now(timezone.utc)
            }
            if form.operator_notes.data:
                update_data['observation'] = form.operator_notes.data
            
            # Lógica para completed_at
            if new_status_value in ['completed', 'cancelled'] and not ticket.get('completed_at'):
                update_data['completed_at'] = datetime.now(timezone.utc)
            elif new_status_value not in ['completed', 'cancelled'] and ticket.get('completed_at'):
                update_data['completed_at'] = None

            mongo.db.tickets.update_one({"_id": ObjectId(ticket_id)}, {"$set": update_data})

            log_ticket_history(ticket_id, "Actualización de Ticket por Operador", current_user, f"Estado cambiado a {new_status_value}")

            # Lógica de envío de correos (simplificada, a refactorizar)
            # send_notification_email(...)

            flash(f'Ticket {ticket_id} actualizado exitosamente.', 'success')
            return redirect(url_for('operator_bp.operator_tickets'))

        except Exception as e:
            logger.error(f"Error al actualizar ticket {ticket_id}: {e}", exc_info=True)
            flash('Ocurrió un error al actualizar el ticket.', 'danger')

    return render_template('operator/operator_ticket_detail.html', title=f'Detalle Ticket #{ticket_id}', form=form, ticket=ticket, status_map=status_map, is_ticket_editable_by_operator=is_ticket_editable_by_operator)

@operator_bp.route('/ticket/<string:ticket_id>/history', methods=['GET'])
@login_required
def ticket_history(ticket_id):
    try:
        ticket = mongo.db.tickets.find_one({"_id": ObjectId(ticket_id)})
        if not ticket:
            flash('Ticket no encontrado.', 'danger')
            return redirect(url_for('main.home'))
        
        # La lógica de permisos debería estar aquí. 
        # Por ahora, se asume que si el usuario llega aquí, tiene permiso.

        # El historial está incrustado en el propio ticket
        history_records = ticket.get('history', [])
        
        logger.info(f'Usuario {current_user.username} consultó el historial del ticket {ticket_id}.')

        referrer_url = request.referrer or url_for('main.home')

        return render_template('ticket_history.html', ticket=ticket, history_records=history_records, referrer_url=referrer_url)

    except Exception as e:
        logger.error(f"Error al cargar el historial del ticket {ticket_id}: {e}", exc_info=True)
        flash("Error al cargar el historial del ticket.", "danger")
        return redirect(url_for('main.home'))