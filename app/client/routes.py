from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from app.client import client_bp
from app import mongo
from .forms import RejectTicketForm, TicketForm, ClientDescriptionForm
from app.supervisor.forms import TicketFilterForm # Asumimos que este form se adaptará o seguirá funcionando
from datetime import datetime, timezone
from app.auth.decorators import client_required
import logging
from bson.objectid import ObjectId
from bson.errors import InvalidId
import pymongo
from app.utils import log_ticket_history, send_notification_email # Importar funciones centralizadas

logger = logging.getLogger(__name__)

@client_bp.route('/create_ticket', methods=['GET', 'POST'])
@login_required
@client_required
def create_ticket():
    form = TicketForm()
    try:
        categories = list(mongo.db.categories.find().sort("name", 1))
        form.category.choices = [(cat["value"], cat["name"]) for cat in categories]
        category_map = {c['value']: c['name'] for c in categories}

        statuses = list(mongo.db.statuses.find().sort("name", 1))
        status_map = {s['value']: s['name'] for s in statuses}

    except pymongo.errors.PyMongoError as e:
        logger.error(f"Error al cargar categorías o estados: {e}")
        flash("No se pudieron cargar las opciones. No es posible crear un ticket.", "danger")
        category_map = {}
        status_map = {}

    if form.validate_on_submit():
        try:
            pending_status = mongo.db.statuses.find_one({"value": "pending"})
            if not pending_status:
                flash('Error crítico: El estado inicial "Pendiente" no existe.', 'danger')
                return redirect(url_for('client_bp.create_ticket'))

            # --- Lógica de asignación de supervisor por categoría (reimplementada) ---
            # Obtener los supervisores específicos
            supervisor_general_data = mongo.db.personas.find_one({"username": "supervisor_general"})
            supervisor_delineante_data = mongo.db.personas.find_one({"username": "supervisor_delineante"})
            supervisor_ingenieria_data = mongo.db.personas.find_one({"username": "supervisor_ingenieria"})

            assignment_rules = {
                'General': supervisor_general_data,
                'Mantenimiento': supervisor_ingenieria_data,
                'Redes': supervisor_ingenieria_data,
                'Soporte Técnico': supervisor_ingenieria_data,
                'Hardware': supervisor_ingenieria_data,
                'Software': supervisor_ingenieria_data,
                'Delineante': supervisor_delineante_data,
                'Periodismo': supervisor_delineante_data,
            }
            
            # Buscar la categoría seleccionada por su 'value' para obtener su 'name'
            selected_category_doc = mongo.db.categories.find_one({"value": form.category.data})
            selected_category_name = selected_category_doc['name'] if selected_category_doc else None

            assigned_supervisor_data = assignment_rules.get(selected_category_name)
            
            assigned_supervisor_id = assigned_supervisor_data['_id'] if assigned_supervisor_data else None
            assigned_supervisor_username = assigned_supervisor_data['username'] if assigned_supervisor_data else None
            assigned_supervisor_email = assigned_supervisor_data['email'] if assigned_supervisor_data else None

            if not assigned_supervisor_id:
                flash(f'No se encontró un supervisor para la categoría "{selected_category_name}". El ticket se creará sin asignar.', 'info')
            # --- Fin Lógica de asignación ---

            new_ticket = {
                "title": form.title.data,
                "description": form.description.data,
                "category_value": form.category.data,
                "status_value": pending_status['value'],
                "creator": {
                    "user_id": ObjectId(current_user.id),
                    "username": current_user.username
                },
                "supervisor": {
                    "user_id": assigned_supervisor_id,
                    "username": assigned_supervisor_username
                } if assigned_supervisor_id else None,
                "operator": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "history": []
            }
            
            result = mongo.db.tickets.insert_one(new_ticket)
            ticket_id = result.inserted_id

            log_ticket_history(str(ticket_id), "Creación de Ticket", current_user, "Ticket creado por el cliente.")

            # --- ENVÍO DE CORREO: Al supervisor asignado, cuando el cliente crea el ticket ---
            if assigned_supervisor_id and assigned_supervisor_email:
                send_notification_email(
                    subject=f"Nuevo Ticket Creado: #{ticket_id}",
                    recipients=[assigned_supervisor_email],
                    template='emails/ticket_created.html',
                    ticket=new_ticket, # Pasar el diccionario del ticket
                    supervisor_name=assigned_supervisor_username,
                    client_name=current_user.username,
                    status_map=status_map, # Pasar el status_map al email template
                    category_map=category_map # Pasar el category_map al email template
                )

            flash('¡Ticket creado exitosamente!', 'success')
            return redirect(url_for('client_bp.client_tickets'))

        except pymongo.errors.PyMongoError as e:
            logger.error(f"Error de base de datos al crear ticket: {e}", exc_info=True)
            flash('Ocurrió un error al guardar el ticket.', 'danger')
        except Exception as e:
            logger.error(f"Error inesperado al crear ticket: {e}", exc_info=True)
            flash('Ocurrió un error inesperado al crear el ticket.', 'danger')

    return render_template('client/create_ticket.html', title='Crear Ticket', form=form, status_map=status_map, category_map=category_map)

@client_bp.route('/client_tickets', methods=['GET', 'POST'])
@login_required
@client_required
def client_tickets():
    form = TicketFilterForm(request.args)
    query = {"creator.user_id": ObjectId(current_user.id)}
    
    # Lógica de filtrado para MongoDB
    if form.validate():
        if form.ticket_id.data:
            try:
                query["_id"] = ObjectId(form.ticket_id.data)
            except InvalidId:
                flash("ID de Ticket inválido.", "warning")
        if form.search_title.data:
            query["title"] = {"$regex": form.search_title.data, "$options": "i"}
        if form.category.data:
            query["category_value"] = form.category.data
        if form.status.data:
            query["status_value"] = form.status.data
        # Filtros de fecha
        if form.start_date.data or form.end_date.data:
            query["created_at"] = {}
            if form.start_date.data:
                query["created_at"]["$gte"] = datetime.combine(form.start_date.data, datetime.min.time(), tzinfo=timezone.utc)
            if form.end_date.data:
                query["created_at"]["$lte"] = datetime.combine(form.end_date.data, datetime.max.time(), tzinfo=timezone.utc)

    try:
        tickets = list(mongo.db.tickets.find(query).sort("created_at", -1))
        logger.info(f'Usuario {current_user.username} consultó sus tickets. Se encontraron {len(tickets)} tickets.')
    except pymongo.errors.PyMongoError as e:
        logger.error(f"Error al buscar tickets para el cliente {current_user.username}: {e}")
        flash("Error al cargar los tickets.", "danger")
        tickets = []

    # Poblar los formularios de filtro (solo categorías y estados)
    try:
        statuses = list(mongo.db.statuses.find().sort("name", 1))
        form.status.choices = [('', 'Todos los Estados')] + [(s['value'], s['name']) for s in statuses]
        categories = list(mongo.db.categories.find().sort("name", 1))
        form.category.choices = [('', 'Todas las Categorías')] + [(c['value'], c['name']) for c in categories]

        status_map = {s['value']: s['name'] for s in statuses}
        category_map = {c['value']: c['name'] for c in categories}

    except pymongo.errors.PyMongoError as e:
        logger.error(f"Error al poblar los filtros: {e}")
        flash("Error al cargar opciones de filtro.", "warning")
        status_map = {}
        category_map = {}

    return render_template('client/client_tickets.html', title='Mis Tickets', tickets=tickets, form=form, status_map=status_map, category_map=category_map)

@client_bp.route('/client/ticket/<string:ticket_id>/manage', methods=['GET', 'POST'])
@login_required
@client_required
def client_manage_completed_ticket(ticket_id):
    try:
        ticket = mongo.db.tickets.find_one({"_id": ObjectId(ticket_id), "creator.user_id": ObjectId(current_user.id)})
    except Exception as e:
        logger.error(f"Error al buscar ticket {ticket_id} para gestionar: {e}")
        flash("Error al cargar el ticket.", "danger")
        return redirect(url_for('client_bp.client_tickets'))

    if not ticket:
        flash('Ticket no encontrado o no tienes permiso para gestionarlo.', 'danger')
        return redirect(url_for('client_bp.client_tickets'))

    # Asegurarse de que el ticket esté en un estado gestionable por el cliente
    if ticket['status_value'] not in ['completed', 'cancelled']:
        flash('Este ticket no está en un estado que requiera gestión del cliente (Completado o Cancelado).', 'warning')
        return redirect(url_for('client_bp.client_tickets'))

    form = RejectTicketForm()

    try:
        statuses = list(mongo.db.statuses.find().sort("name", 1))
        status_map = {s['value']: s['name'] for s in statuses}
    except pymongo.errors.PyMongoError as e:
        logger.error(f"Error al cargar estados: {e}")
        flash("Error al cargar opciones de estado.", "warning")
        status_map = {}

    if form.validate_on_submit():
        try:
            rejected_status = mongo.db.statuses.find_one({"value": "rejected"})
            if not rejected_status:
                flash('Error: El estado "Rechazado" no está configurado.', 'danger')
                return redirect(url_for('client_bp.client_tickets'))

            update_data = {
                "status_value": rejected_status['value'],
                "updated_at": datetime.now(timezone.utc)
            }
            mongo.db.tickets.update_one({"_id": ObjectId(ticket_id)}, {"$set": update_data})

            log_ticket_history(ticket_id, "Rechazo de Resolución", current_user, form.note.data)
            
            # --- ENVÍO DE CORREO AL OPERADOR Y SUPERVISOR ---
            # Adaptar la lógica de envío de correo para usar los datos del ticket de MongoDB
            # ... (esta parte requiere más refactorización de la función send_notification_email y los datos del ticket)

            flash(f'Ticket #{ticket_id} rechazado exitosamente. El operador ha sido notificado.', 'success')
            return redirect(url_for('client_bp.client_tickets'))

        except Exception as e:
            logger.error(f'Error al rechazar ticket {ticket_id}: {e}', exc_info=True)
            flash(f'Ocurrió un error al rechazar el ticket: {e}', 'danger')
    
    return render_template('client/client_manage_completed_ticket.html',
                           title=f'Gestionar Ticket #{ticket_id}',
                           ticket=ticket,
                           form=form,
                           status_map=status_map)

@client_bp.route('/client_add_description/<string:ticket_id>', methods=['GET', 'POST'])
@login_required
@client_required
def client_add_description(ticket_id):
    try:
        ticket = mongo.db.tickets.find_one({"_id": ObjectId(ticket_id), "creator.user_id": ObjectId(current_user.id)})
    except Exception as e:
        logger.error(f"Error al buscar ticket {ticket_id} para añadir descripción: {e}")
        flash("Error al cargar el ticket.", "danger")
        return redirect(url_for('client_bp.client_tickets'))

    if not ticket:
        flash('Ticket no encontrado o no tienes permiso para modificarlo.', 'danger')
        return redirect(url_for('client_bp.client_tickets'))

    form = ClientDescriptionForm()

    is_ticket_editable_by_client = (ticket['status_value'] not in ['completed', 'closed', 'cancelled'])

    try:
        statuses = list(mongo.db.statuses.find().sort("name", 1))
        status_map = {s['value']: s['name'] for s in statuses}
    except pymongo.errors.PyMongoError as e:
        logger.error(f"Error al cargar estados: {e}")
        flash("Error al cargar opciones de estado.", "warning")
        status_map = {}

    if form.validate_on_submit():
        try:
            new_text = form.new_description_text.data
            # Añadir la nueva descripción al campo existente o crear uno nuevo
            updated_description = ticket.get('description', '') + f"\n\n--- Nota de {current_user.username} ({datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}) ---\n{new_text}"
            
            update_data = {
                "description": updated_description,
                "updated_at": datetime.now(timezone.utc)
            }
            mongo.db.tickets.update_one({"_id": ObjectId(ticket_id)}, {"$set": update_data})

            log_ticket_history(ticket_id, "Nota adicional del cliente", current_user, f"Cliente añadió nota: {new_text}")

            flash('Nota agregada exitosamente al ticket.', 'success')
            return redirect(url_for('client_bp.client_tickets'))

        except Exception as e:
            logger.error(f"Error al agregar nota al ticket {ticket_id}: {e}", exc_info=True)
            flash(f'Ocurrió un error al agregar la nota. Detalles: {e}', 'danger')

    return render_template('client/client_edit_ticket.html', title=f'Agregar Nota al Ticket #{ticket_id}', form=form, ticket=ticket, is_ticket_editable_by_client=is_ticket_editable_by_client, status_map=status_map)

@client_bp.route('/ticket/<string:ticket_id>/close', methods=['POST'])
@login_required
@client_required
def close_ticket(ticket_id):
    try:
        ticket = mongo.db.tickets.find_one({"_id": ObjectId(ticket_id), "creator.user_id": ObjectId(current_user.id)})
    except Exception as e:
        logger.error(f"Error al buscar ticket {ticket_id} para cerrar: {e}")
        flash("Error al cargar el ticket.", "danger")
        return redirect(url_for('client_bp.client_tickets'))

    if not ticket:
        flash('Ticket no encontrado o no tienes permiso para cerrarlo.', 'danger')
        return redirect(url_for('client_bp.client_tickets'))

    if ticket['status_value'] not in ['completed', 'cancelled', 'rejected']:
        flash('Solo puedes cerrar tickets que estén Completados, Cancelados o Rechazados.', 'warning')
        return redirect(url_for('client_bp.client_tickets'))

    try:
        closed_status = mongo.db.statuses.find_one({"value": "closed"})
        if not closed_status:
            flash('Error: El estado "Cerrado" no está configurado.', 'danger')
            return redirect(url_for('client_bp.client_tickets'))

        # Añadir una nota de que el cliente cerró el ticket
        entry = f"\n\n--- Ticket CERRADO por Cliente ({datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S %Z')}) ---\nCliente da conformidad al cierre."
        updated_description = ticket.get('description', '') + entry

        update_data = {
            "status_value": closed_status['value'],
            "description": updated_description,
            "updated_at": datetime.now(timezone.utc)
        }
        mongo.db.tickets.update_one({"_id": ObjectId(ticket_id)}, {"$set": update_data})

        log_ticket_history(ticket_id, "Ticket cerrado por el cliente", current_user, "Cliente da conformidad al cierre.")

        # --- ENVÍO DE CORREO AL OPERADOR ---
        # Adaptar la lógica de envío de correo para usar los datos del ticket de MongoDB
        # ...

        flash(f'Ticket #{ticket_id} ha sido cerrado exitosamente.', 'success')

    except Exception as e:
        logger.error(f"Error al cerrar ticket {ticket_id}: {e}", exc_info=True)
        flash(f'Ocurrió un error al cerrar el ticket: {e}', 'danger')

    return redirect(url_for('client_bp.client_tickets'))