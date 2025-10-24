from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from app.supervisor import supervisor_bp
from app import mongo
from .forms import TicketEditForm, AssignTicketForm
from app.auth.decorators import supervisor_or_admin_required
from datetime import datetime, timezone
from bson.objectid import ObjectId
import pymongo
import logging
from app.utils import log_ticket_history
from app.email import send_notification_email

logger = logging.getLogger(__name__)

@supervisor_bp.route('/edit_ticket/<string:ticket_id>', methods=['GET', 'POST'])
@login_required
@supervisor_or_admin_required
def edit_ticket(ticket_id):
    try:
        ticket = mongo.db.tickets.find_one({"_id": ObjectId(ticket_id)})
    except Exception as e:
        logger.error(f"Error al buscar ticket {ticket_id} para editar: {e}")
        flash("Error al cargar el ticket.", "danger")
        return redirect(url_for('admin_bp.list_tickets'))

    if not ticket:
        flash('Ticket no encontrado.', 'danger')
        return redirect(url_for('admin_bp.list_tickets'))

    # --- Control de acceso para supervisores ---
    if current_user.is_supervisor and not current_user.is_admin:
        if ticket.get('supervisor') and ticket['supervisor']['user_id'] != ObjectId(current_user.id):
            flash('No tienes permiso para editar este ticket, ya está asignado a otro supervisor.', 'danger')
            return redirect(url_for('admin_bp.list_tickets'))
    # --- Fin Control de acceso ---

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
            return redirect(url_for('admin_bp.list_tickets'))

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
        return redirect(url_for('admin_bp.list_tickets'))

    if not ticket:
        flash('Ticket no encontrado.', 'danger')
        return redirect(url_for('admin_bp.list_tickets'))

    # --- Control de acceso para supervisores ---
    if current_user.is_supervisor and not current_user.is_admin:
        if ticket.get('supervisor') and ticket['supervisor']['user_id'] != ObjectId(current_user.id):
            flash('No tienes permiso para asignar este ticket, ya está asignado a otro supervisor.', 'danger')
            return redirect(url_for('admin_bp.list_tickets'))
    # --- Fin Control de acceso ---

    form = AssignTicketForm()
    status_map = {}

    # Poblar SelectField de operadores y status_map
    try:
        operators = list(mongo.db.personas.find({"role": "operador"}).sort("username", 1))
        form.operator.choices = [('', '--- Seleccionar Operador ---')] + [(str(p['_id']), p['username']) for p in operators]
        
        statuses = list(mongo.db.statuses.find())
        status_map = {s['value']: s['name'] for s in statuses}

    except pymongo.errors.PyMongoError as e:
        logger.error(f"Error al poblar datos para la página de asignación: {e}")
        flash("Error al cargar opciones para la asignación.", "warning")

    if form.validate_on_submit():
        try:
            operator_id = form.operator.data
            if not operator_id:
                flash('Por favor, selecciona un operador válido.', 'warning')
                return render_template('supervisor/assign_ticket.html', title='Asignar Ticket', form=form, ticket=ticket, status_map=status_map)

            operator_obj = mongo.db.personas.find_one({"_id": ObjectId(operator_id)})
            if not operator_obj:
                flash('Operador seleccionado no válido.', 'danger')
                return render_template('supervisor/assign_ticket.html', title='Asignar Ticket', form=form, ticket=ticket, status_map=status_map)

            assigned_status = mongo.db.statuses.find_one({"value": "in_progress"})
            if not assigned_status:
                flash('Error: El estado "En Progreso" no está configurado.', 'danger')
                return redirect(url_for('admin_bp.list_tickets'))

            update_data = {
                "operator": {"user_id": operator_obj['_id'], "username": operator_obj['username']},
                "status_value": assigned_status['value'],
                "updated_at": datetime.now(timezone.utc)
            }
            mongo.db.tickets.update_one({"_id": ObjectId(ticket_id)}, {"$set": update_data})

            log_ticket_history(ticket_id, "Asignación de Operador", current_user, f"Ticket asignado a {operator_obj['username']}")

            # --- ENVÍO DE CORREO AL OPERADOR ASIGNADO ---
            send_notification_email(
                subject='Ticket Asignado - [TuApp]',
                recipients=[operator_obj['email']],
                template='emails/ticket_assigned.html',
                operator=operator_obj,
                ticket=ticket,
                supervisor=current_user
            )

            flash(f"Ticket {ticket_id} asignado a {operator_obj['username']} y estado cambiado a \"{assigned_status['name']}\".", 'success')
            return redirect(url_for('admin_bp.list_tickets'))

        except Exception as e:
            logger.error(f"Error al asignar ticket {ticket_id}: {e}", exc_info=True)
            flash('Ocurrió un error al asignar el ticket.', 'danger')

    return render_template('supervisor/assign_ticket.html', title='Asignar Ticket', form=form, ticket=ticket, status_map=status_map)

@supervisor_bp.route('/ticket/<string:ticket_id>/take', methods=['POST'])
@login_required
@supervisor_or_admin_required
def take_ticket(ticket_id):
    logger.info(f"--- Intento de tomar ticket {ticket_id} por usuario {current_user.username} ---")
    try:
        ticket = mongo.db.tickets.find_one({"_id": ObjectId(ticket_id)})

        if not ticket:
            logger.warning(f"Take Ticket: Ticket {ticket_id} no encontrado en la base de datos.")
            flash('Ticket no encontrado.', 'danger')
            return redirect(url_for('admin_bp.list_tickets'))

        logger.info(f"Take Ticket: Ticket {ticket_id} encontrado.")

        if ticket.get('supervisor'):
            logger.warning(f"Take Ticket: Ticket {ticket_id} ya está asignado a {ticket.get('supervisor', {}).get('username')}.")
            flash('Este ticket ya ha sido asignado a otro supervisor.', 'warning')
            return redirect(url_for('admin_bp.list_tickets'))

        # Asignar el supervisor actual al ticket
        update_data = {
            "supervisor": {
                "user_id": ObjectId(current_user.id),
                "username": current_user.username
            },
            "updated_at": datetime.now(timezone.utc)
        }
        logger.info(f"Take Ticket: Preparando la actualización para ticket {ticket_id} con los datos: {update_data}")

        result = mongo.db.tickets.update_one({"_id": ObjectId(ticket_id)}, {"$set": update_data})
        
        logger.info(f"Take Ticket: Resultado de la actualización: matched_count={result.matched_count}, modified_count={result.modified_count}")

        if result.modified_count == 1:
            # Registrar en el historial
            log_ticket_history(ticket_id, "Ticket Tomado", current_user, f"El supervisor {current_user.username} ha tomado el ticket.")
            logger.info(f"Take Ticket: Historial registrado para ticket {ticket_id}.")
            flash(f'Has tomado el ticket #{ticket_id}. Ahora está en tu lista de tickets.', 'success')
        else:
            logger.error(f"Take Ticket: La actualización del ticket {ticket_id} no modificó ningún documento.")
            flash('Hubo un problema al intentar asignar el ticket. No se pudo actualizar.', 'danger')
        
    except Exception as e:
        logger.error(f"Error excepcional al tomar el ticket {ticket_id}: {e}", exc_info=True)
        flash('Ocurrió un error excepcional al intentar tomar el ticket.', 'danger')

    return redirect(url_for('admin_bp.list_tickets'))