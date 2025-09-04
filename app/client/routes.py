from flask import render_template, flash, redirect, url_for, current_app, request
from flask_login import login_required, current_user
from app.client import client_bp
from app import db
from app.models import Ticket
from sqlalchemy.exc import SQLAlchemyError
from .forms import RejectTicketForm, TicketForm, ClientDescriptionForm
from ..models import Ticket, Status, Category
from app.supervisor.forms import TicketFilterForm
from app.utils import log_ticket_change, get_ticket_attributes_for_history, send_notification_email
from app.auth.models import Persona
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from app.auth.decorators import client_required
import logging
from app.repositories import SQLTicketRepository, SQLStatusRepository, SQLCategoryRepository, SQLUserRepository

# Instantiate repositories
ticket_repository = SQLTicketRepository()
status_repository = SQLStatusRepository()
category_repository = SQLCategoryRepository()
user_repository = SQLUserRepository()


logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
#               FUNCIÓN: CREAR UN TICKET (CLIENTE)
# ------------------------------------------------------------------------------
@client_bp.route('/create_ticket', methods=['GET', 'POST'])
@login_required
def create_ticket():
    form = TicketForm()
    if form.validate_on_submit():
        try:
            selected_category = category_repository.find_by_value(form.category.data)
            
            if not selected_category:
                flash('Categoría seleccionada no válida.', 'error')
                return render_template('client/create_ticket.html', title='Crear Ticket', form=form)

            # Obtén el objeto Status correspondiente a 'pending'
            # Asegúrate de que 'pending' exista en tu tabla Status y tenga el ID correcto.  
            pending_status = status_repository.find_by_value('pending')
                     
            # Si no se encuentra 'pending', podrías lanzar un error o usar un ID por defecto seguro (ej. 1)
            # Aunque tu modelo ya tiene default=1, es buena práctica ser explícito aquí.
            if not pending_status:
                flash('Error: El estado inicial "Pendiente" no se encontró en la base de datos.', 'error')
                return render_template('client/create_ticket.html', title='Crear Ticket', form=form)

            supervisores_en_db = user_repository.find_supervisors_by_username_and_role(
                usernames=['lrguardamagna.etra@grupoetra.com', 'lrguardamagna.etra@grupoetra.com', 'lrguardamagna.etra@grupoetra.com'],
                role_ids=[1, 4, 9]
            )
            
            supervisores_map = {s.username: s for s in supervisores_en_db}

            supervisor_general = supervisores_map.get('lrguardamagna.etra@grupoetra.com')
            supervisor_delineante = supervisores_map.get('lrguardamagna.etra@grupoetra.com')
            supervisor_ingenieria = supervisores_map.get('lrguardamagna.etra@grupoetra.com')

            assignment_rules = {
                'General': supervisor_general,
                'Delineante': supervisor_delineante,
                'Periodismo': supervisor_delineante,
                'Mantenimiento': supervisor_ingenieria,
                'Redes': supervisor_ingenieria,
                'Hardware': supervisor_ingenieria,
                'Software': supervisor_ingenieria,
                'Soporte Técnico': supervisor_ingenieria
            }

            assigned_supervisor_obj = assignment_rules.get(selected_category.name)
            
            if not assigned_supervisor_obj:
                # Opcional: Qué hacer si la categoría no tiene un supervisor asignado
                flash(f'No se encontró una regla de asignación automática o el supervisor para la categoría "{selected_category.name}" no está disponible.', 'info')
                assigned_supervisor_id = None
            else:
                assigned_supervisor_id = assigned_supervisor_obj.id
                flash(f'Supervisor asignado automáticamente: {assigned_supervisor_obj.username}', 'success')
            
            #Asignación de operador, Nula, lo asigna manualmente el supervisor
            asigned_operator = None

            new_ticket = Ticket(
                category_id=selected_category.id,
                title=form.title.data,
                description=form.description.data,
                creator_id=current_user.id,
                status_id=pending_status.id,
                asignated_supervisor_id=assigned_supervisor_id,
                asigned_operator_id=asigned_operator.id if asigned_operator else None
            )
            
            ticket_repository.add(new_ticket)
            db.session.flush()
            

            log_ticket_change(
                ticket=new_ticket,
                changed_by_persona=current_user,
                change_type='Creación de Ticket',
                old_values={}, # No hay valores antiguos al crear
                new_values={
                    'category_id': new_ticket.category_id,
                    'status_id': new_ticket.status_id,
                    'description': new_ticket.description,
                    'observation': new_ticket.observation,
                    'asignated_supervisor_id': new_ticket.asignated_supervisor_id,
                    'asigned_operator_id': new_ticket.asigned_operator_id,
                }
            )

            # --- Logger: INFO - Ticket creado con éxito ---
            logger.info(f"Ticket #{new_ticket.id} creado por usuario {current_user.username} (ID: {current_user.id}), asignado a: {new_ticket.asignated_supervisor_id}")
            db.session.commit()
            flash('¡Ticket de orden de trabajo creado exitosamente!', 'success')
                                    
            # --- ENVÍO DE CORREO: Al supervisor asignado, cuando el cliente crea el ticket ---
            client_email = current_user.email
            client_name = current_user.username

            if new_ticket.asignated_supervisor_obj and new_ticket.asignated_supervisor_obj.email:
                try:
                    send_notification_email(
                        subject=f"Nuevo Ticket Creado: #{new_ticket.id}",
                        recipients=[new_ticket.asignated_supervisor_obj.email],
                        template='emails/ticket_created.html',
                        ticket=new_ticket,
                        supervisor_name=new_ticket.asignated_supervisor_obj.username,
                        client_email=client_email,
                        client_name=client_name
                    )
                except Exception as e:
                    # --- Logger: ERROR - Error al enviar el correo de notificación al supervisor ---
                    logger.error(f"ERROR: No se pudo enviar el correo al supervisor {new_ticket.asignated_supervisor_obj.email}: {e}")
                    flash('Advertencia: No se pudo enviar el correo de notificación al supervisor.', 'warning')

            return redirect(url_for('client_bp.create_ticket'))
        except SQLAlchemyError as e:
            db.session.rollback()
            # --- Logger: ERROR - Fallo al crear ticket ---
            logger.error(f"Error al crear ticket: Usuario {current_user.username}, (ID: {current_user.id}): {str(e)}", exc_info=True) 
            flash(f'Ocurrió un error al guardar el ticket. Detalles: {e}', 'error')
        except Exception as e:
            # --- Logger: ERROR - Error inesperado ---
            db.session.rollback()
            message=f"Ocurrió un error inesperado. Por favor, contacte a soporte. Detalles: '{e}'", 'error'
            logger.error(f'AL crear un nuevo ticket: {message}',exc_info=True)
            flash(message, 'error')

    return render_template('client/create_ticket.html', title='Crear Ticket', form=form)

# ------------------------------------------------------------------------------
#               FUNCIÓN: LISTADO DE TICKETS (CLIENTE)
# ------------------------------------------------------------------------------
@client_bp.route('/client_tickets', methods=['GET', 'POST']) # <--- Asegúrate de permitir POST
@login_required
@client_required
def client_tickets():
    # Inicializa el formulario de filtro
    form = TicketFilterForm(request.args)

    if form.clear_filters.data:
        return redirect(url_for('client_bp.client_tickets'))

    # Usa la función de utilidad, pasándole el formulario.
    
    tickets = ticket_repository.get_filtered_tickets(form=form, filter_by_user_role=True) 
    
    logger.info(f'Usuario {current_user.username} (ID: {current_user.id}) consultó sus tickets. Se encontraron {len(tickets)} tickets.')
    
    # El `if not tickets` y el `flash` para "Ticket no encontrado" que tenías
    # deberías revisarlo. Si se usan filtros, el flash podría aparecer incorrectamente.
    # Es mejor manejarlo en la plantilla o con un mensaje más general.
    # if not tickets and request.method == 'GET' and not request.args: 
    #     flash('No se encontraron tickets creados por usted.', 'info')

    export_url_args = request.args.copy() # Si el cliente también tiene opción de exportar

    return render_template(
        'client/client_tickets.html',
        title='Mis Tickets',
        tickets=tickets,
        form=form, # <--- Pasa el formulario a la plantilla
        export_url_args=export_url_args
    )

# ------------------------------------------------------------------------------
#               FUNCIÓN: RECHAZAR LA RESOLUCIÓN DE UN TICKET (CLIENTE)
# ------------------------------------------------------------------------------
@client_bp.route('/client/ticket/<int:ticket_id>/manage', methods=['GET', 'POST'])
@login_required
@client_required
def client_manage_completed_ticket(ticket_id):
    ticket = ticket_repository.find_by_id_and_creator(ticket_id, current_user.id)

    if not ticket:
        flash('Ticket no encontrado o no tienes permiso para gestionarlo.', 'danger')
        return redirect(url_for('client_bp.client_tickets'))

    # Asegurarse de que el ticket esté en un estado gestionable por el cliente
    # (Completado o Cancelado)
    if ticket.status_obj.value not in ['completed', 'cancelled']:
        flash('Este ticket no está en un estado que requiera gestión del cliente (Completado o Cancelado).', 'warning')
        return redirect(url_for('client_bp.client_tickets'))

    form = RejectTicketForm()

    if form.validate_on_submit():
        # Capturamos los valores del ticket antes de la modificación para el log de historial
        old_values = get_ticket_attributes_for_history(ticket)

        try:
            # 1. Cambiar el estado a 'Rechazado'
            rejected_status = status_repository.find_by_value('rejected')
            if rejected_status:
                ticket.status_id = rejected_status.id
            else:
                # --- Logger: ERROR - Estado "Rechazado" no encontrado ---
                logger.error(f'No se ha encontrado el estado "Rechazado", compruebe que la base de datos contiene este estado')
                flash('Error: El estado "Rechazado" no está configurado en la base de datos.', 'danger')
                return redirect(url_for('client_bp.client_tickets'))

            ticket.modified_timestamp = datetime.now(timezone.utc) # Actualizar la fecha de modificación

            # Capturamos los nuevos valores del ticket para el log de historial
            new_values = get_ticket_attributes_for_history(ticket)

            # Registrar el cambio en el log
            log_ticket_change(
                ticket=ticket,
                changed_by_persona=current_user,
                change_type='Rechazo de Resolución',
                old_values=old_values,
                new_values=new_values,
                change_details=form.note.data
            )
            
            ticket_repository.save(ticket) # Añadimos el ticket modificado a la sesión
            db.session.commit()

            # --- Logger: INFO - Ticket rechazado con éxito ---
            logger.info(f'Usuario {current_user.username} (ID: {current_user.id}) ha rechazado el ticket ID: {ticket_id}, con motivo: {form.note.data}.')
            flash(f'Ticket #{ticket.id} rechazado exitosamente. El operador ha sido notificado.', 'success')

                        # --- ENVÍO DE CORREO AL OPERADOR Y SUPERVISOR ---
            recipients = []
            if ticket.asigned_operator_obj and ticket.asigned_operator_obj.email:
                recipients.append(ticket.asigned_operator_obj.email)
            if ticket.asignated_supervisor_obj and ticket.asignated_supervisor_obj.email:
                recipients.append(ticket.asignated_supervisor_obj.email)
            
            if recipients:
                try:
                    send_notification_email(
                        subject=f"Ticket Rechazado: #{ticket.id}",
                        recipients=recipients,
                        template='emails/ticket_rejected.html', # ¡Usaremos esta plantilla!
                        ticket=ticket,
                        client_name=current_user.username,
                        note=form.note.data,
                        # Para generar el enlace, si es necesario, pásalo como variable
                        ticket_url=url_for('operator_bp.operator_tickets', ticket_id=ticket.id, _external=True)
                    )
                except Exception as e:
                    logger.error(f"ERROR: No se pudo enviar el correo de rechazo para ticket #{ticket.id}: {e}")
                    flash('Advertencia: No se pudo enviar el correo de notificación al operador/supervisor.', 'warning')
            else:
                logger.warning(f"No se pudo enviar correo para ticket #{ticket.id} (operador/supervisor email no disponible)")
                flash(f"Advertencia: No se pudo enviar correo de notificación para ticket #{ticket.id}",'warning')

            return redirect(url_for('client_bp.client_tickets'))

        except SQLAlchemyError as e:
            db.session.rollback()
            # --- Logger: ERROR - Intento de rechazo de ticket fallido ---
            logger.error(f'Intento de rechazo de ticket fallido: Ticket ID: {ticket_id} no pudo rechazarse por el usuario {current_user.username} (ID: {current_user.id})',exc_info=True)
            flash(f'Ocurrió un error al rechazar el ticket: {e}', 'error')
        except Exception as e:
            # --- Logger: ERROR - Error inesperado ---
            db.session.rollback()
            message=f"Ocurrió un error inesperado. Por favor, contacte a soporte. Detalles: '{e}'", 'error'
            logger.error('Al intentar rechazar el ticket: {message}',exc_info=True)
            flash(message, 'error')
    
    return render_template('client/client_manage_completed_ticket.html',
                           title=f'Gestionar Ticket #{ticket.id}',
                           ticket=ticket,
                           form=form)

# ------------------------------------------------------------------------------
#               FUNCIÓN: AGREGAR COMENTARIOS A UN TICKET (CLIENTE)
# ------------------------------------------------------------------------------
@client_bp.route('/client_add_description/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
@client_required
def client_add_description(ticket_id):
    ticket = ticket_repository.find_by_id(ticket_id)
    
    old_values = get_ticket_attributes_for_history(ticket)

    # Verificar si el ticket existe y si fue creado por el usuario actual (cliente)
    if not ticket or ticket.creator_id != current_user.id:
        flash('Ticket no encontrado o no tienes permiso para modificarlo.', 'danger')
        return redirect(url_for('client_bp.client_tickets'))

    form = ClientDescriptionForm()

    is_ticket_editable_by_client = (ticket.status_obj and
                                    ticket.status_obj.value not in ['completed', 'closed', 'canceled'])

    if form.validate_on_submit():
        try:
            new_text = form.new_description_text.data
            
            ticket.modified_timestamp = datetime.now(timezone.utc) # Actualizar la fecha de modificación

            new_values = get_ticket_attributes_for_history(ticket)

            log_ticket_change(
                ticket=ticket,
                changed_by_persona=current_user,
                change_type='Nota adicional del cliente', # O 'Descripción actualizada por cliente'
                old_values=old_values,
                new_values=new_values,
                change_details=f"Nota del cliente: {new_text}", # Aquí va la nota del cliente
            )

            ticket_repository.save(ticket)
            db.session.commit()

            # --- Logger: INFO - Ticket rechazado con éxito ---
            logger.info(f'Usuario {current_user.username} (ID: {current_user.id}) ha agregadi una nota al ticket ID: {ticket_id}. Nota: {new_text}.')

            flash('Nota agregada exitosamente al ticket.', 'success')
            return redirect(url_for('client_bp.client_tickets')) # Volver a la lista de tickets del cliente

        except SQLAlchemyError as e:
            db.session.rollback()
            # --- Logger: ERROR - Fallo al agregar Nota a ticket ---
            logger.error(f"Error al agregar Nota al ticket #{ticket.id}: Usuario {current_user.username}, (ID: {current_user.id}): {str(e)}", exc_info=True)
            flash(f'Ocurrió un error al agregar la nota. Detalles: {e}', 'error')
        except Exception as e:
            # --- Logger: ERROR - Error inesperado ---
            db.session.rollback()
            message=f"Ocurrió un error inesperado. Por favor, contacte a soporte. Detalles: '{e}'", 'error'
            logger.error(f'Al intentar agregar Nota al ticket #{ticket.id}: {message}',exc_info=True)
            flash(message, 'error')

    # Para la petición GET
    return render_template('client/client_edit_ticket.html', title=f'Agregar Nota al Ticket #{ticket.id}', form=form, ticket=ticket, is_ticket_editable_by_client=is_ticket_editable_by_client)

# ------------------------------------------------------------------------------
#               FUNCIÓN: CERRAR UN TICKET (CLIENTE)
# ------------------------------------------------------------------------------
@client_bp.route('/ticket/<int:ticket_id>/close', methods=['POST'])
@login_required
@client_required # Solo el cliente puede cerrar sus propios tickets
def close_ticket(ticket_id):
    ticket = ticket_repository.find_by_id_and_creator(ticket_id, current_user.id)

    if not ticket:
        flash('Ticket no encontrado o no tienes permiso para cerrarlo.', 'danger')
        return redirect(url_for('client_bp.client_tickets'))

    # Asegúrate de que el ticket esté en un estado que permita ser cerrado por el cliente
    # (completado, cancelado o rechazado)
    if ticket.status_obj.value not in ['completed', 'cancelled', 'rejected']:
        flash('Solo puedes cerrar tickets que estén Completados, Cancelados o Rechazados.', 'warning')
        return redirect(url_for('client_bp.client_tickets'))

    # Capturamos los valores del ticket antes de la modificación para el log de historial
    old_values = get_ticket_attributes_for_history(ticket)

    try:
        # Obtener el objeto Status para 'closed'
        closed_status = status_repository.find_by_value('closed')
        if closed_status:
            ticket.status_id = closed_status.id
            
            # Añadir una nota de que el cliente cerró el ticket al campo 'description'
            timestamp = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S %Z')
            
            # Formato de la nueva entrada: "Fecha [Usuario]: Texto nuevo"
            entry = f"\n\n--- Ticket CERRADO por Cliente ({timestamp}) ---\nCliente da conformidad al cierre."
            
            if ticket.description:
                ticket.description += entry # Si ya hay descripción, añade un salto de línea antes
            else:
                ticket.description = entry # Si es la primera nota, simplemente la asigna
            # --- FIN DE LA MODIFICACIÓN CLAVE ---

            ticket.modified_timestamp = datetime.now(timezone.utc) # Actualizar la fecha de modificación

            # Capturamos los nuevos valores del ticket para el log de historial
            new_values = get_ticket_attributes_for_history(ticket)

            # Registrar el cambio en el log
            log_ticket_change(
                ticket=ticket,
                changed_by_persona=current_user,
                change_type='Ticket cerrado por el cliente',
                old_values=old_values,
                new_values=new_values
            )

            ticket_repository.save(ticket) # Añadimos el ticket modificado a la sesión
            db.session.commit()

             # --- Logger: INFO - Ticket cerrado con éxito ---
            logger.info(f'Usuario {current_user.username} (ID: {current_user.id}) ha cerrado el ticket ID: {ticket_id}')
            flash(f'Ticket #{ticket.id} ha sido cerrado exitosamente.', 'success')
            
            # --- ENVÍO DE CORREO AL OPERADOR ---
            if ticket.asigned_operator_obj and ticket.asigned_operator_obj.email:
                subject = f"Ticket Cerrado por Cliente: #{ticket.id} - {ticket.title}"
                body_text = (
                    f"Hola {ticket.asigned_operator_obj.username},\n\n"
                    f"El cliente ({current_user.username}) ha CERRADO el ticket #{ticket.id} ('{ticket.title}').\n\n"
                    f"Esto indica que el trabajo ha sido completado a su satisfacción.\n\n"
                    f"Puedes ver el ticket aquí: {url_for('operator_bp.operator_tickets', ticket_id=ticket.id, _external=True)}\n\n" # Asumiendo una ruta de vista para operador
                    f"Gracias."
                )
                recipients=[ticket.asigned_operator_obj.email]

                send_notification_email(subject, recipients, 'emails/ticket_closed.html', body_text=body_text, ticket=ticket)
            else:
                # --- Logger: WARNING - Ticket rechazado con éxito ---
                logger.warning(f"No se pudo enviar correo para ticket #{ticket.id} (operador/supervisor email no disponible)")
                flash(f"No se pudo enviar correo para ticket #{ticket.id} (operador/supervisor email no disponible)",'warning')
        else:
            flash('Error: El estado "Cerrado" no está configurado en la base de datos.', 'danger')
            
    except SQLAlchemyError as e:
        db.session.rollback()
        # --- Logger: ERROR - Fallo al cerrar ticket ---
        logger.error(f"Error al cerrar ticket #{ticket.id}: Usuario {current_user.username}, (ID: {current_user.id}): {str(e)}", exc_info=True)
        flash(f'Ocurrió un error al cerrar el ticket: {e}', 'error')
    except Exception as e:
        db.session.rollback()
        # --- Logger: ERROR - Error inesperado ---
        message=f"Ocurrió un error inesperado. Por favor, contacte a soporte. Detalles: '{e}'", 'error'
        logger.error(f'Al intentar cerrar ticket #{ticket.id}: {message}',exc_info=True)
        flash(message, 'error')

    return redirect(url_for('client_bp.client_tickets'))
