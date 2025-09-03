from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from app.operator import operator_bp
from app import db
from app.models import Ticket
from app.supervisor.forms import TicketFilterForm
from sqlalchemy.exc import SQLAlchemyError
from app.operator.forms import OperatorTicketForm
from app.models import Ticket, Status, TicketHistory
from app.utils import log_ticket_change, get_ticket_attributes_for_history, send_notification_email, get_filtered_tickets_query
from app.auth.models import Persona
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from flask import request
from app.auth.decorators import operador_required
import logging


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
#               FUNCIÓN: LISTADO DE TICKETS (OPERADOR)
# ------------------------------------------------------------------------------
@operator_bp.route('/operator_tickets', methods=['GET', 'POST']) # <--- Asegúrate de permitir POST también para el formulario
@login_required
@operador_required
def operator_tickets():
    # 1. Inicializa el formulario de filtro con los argumentos de la solicitud
    form = TicketFilterForm(request.args)

    # Si el botón de limpiar filtros fue presionado
    if form.clear_filters.data:
        return redirect(url_for('operator_bp.operator_tickets'))

    # 2. Usa la función de utilidad, pasándole la instancia del formulario
    #    'filter_by_user_role=True' asegura que solo vea sus tickets.
    query = get_filtered_tickets_query(form=form, filter_by_user_role=True)
    
    # Ordena los tickets por timestamp de forma descendente
    tickets = db.session.execute(
        query.order_by(Ticket.timestamp.desc())
    ).scalars().all()

    logger.info(f'Usuario {current_user.username} (ID: {current_user.id}) consultó sus tickets. Se encontraron {len(tickets)} tickets.')
    
    # Prepara los argumentos para el URL de exportación, si lo usas.
    export_url_args = request.args.copy()

    return render_template(
        'operator/operator_tickets.html',
        title='Mis Tickets Asignados',
        tickets=tickets,
        form=form,
        export_url_args=export_url_args
    )

# ------------------------------------------------------------------------------
#               FUNCIÓN: EDICIÓN DE TICKETS (OPERADOR)
# ------------------------------------------------------------------------------

@operator_bp.route('/operator_ticket_detail/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
@operador_required
def operator_ticket_detail(ticket_id):
    ticket = db.session.execute(select(Ticket).filter_by(id=ticket_id)).scalar_one_or_none()

    if not ticket or ticket.asigned_operator_id != current_user.id:
        flash('Ticket no encontrado o no asignado a ti.', 'danger')
        return redirect(url_for('operator_bp.operator_tickets'))

    editable_status_values = ['pending', 'rejected', 'in_progress']
    is_ticket_editable_by_operator = (ticket.status_obj and ticket.status_obj.value in editable_status_values)

    old_values = get_ticket_attributes_for_history(ticket)
    old_status_value = db.session.execute(select(Status.value).filter_by(id=old_values['status_id'])).scalar_one_or_none()

    form = OperatorTicketForm(obj=ticket)

    completed_status_obj = db.session.execute(select(Status).filter_by(value='completed')).scalar_one_or_none()
    cancelled_status_obj = db.session.execute(select(Status).filter_by(value='cancelled')).scalar_one_or_none()
    
    allowed_status_choices_for_select = []
    if completed_status_obj:
        allowed_status_choices_for_select.append((completed_status_obj.id, completed_status_obj.name))
    if cancelled_status_obj:
        allowed_status_choices_for_select.append((cancelled_status_obj.id, cancelled_status_obj.name))
    
    form.status.choices = allowed_status_choices_for_select
    form.status.choices.sort(key=lambda x: x[1])

    if request.method == 'GET':
        # ¡IMPORTANTE! Si ya no quieres que el campo `observation` se muestre
        # y edite directamente, no precargues `form.operator_notes.data`.
        # Si `operator_notes` es para la *nueva* nota de historial, déjalo vacío en GET.
        # form.operator_notes.data = ticket.observation # <-- Considera eliminar o ajustar esto

        # Si el operador debe ver la "última observación" del historial,
        # deberías cargarla desde el registro de TicketHistory más reciente, no de `ticket.observation`.
        # Pero si el campo `operator_notes` es solo para AÑADIR una nueva nota, déjalo así.
        pass # No hacemos nada aquí, el campo de notas queda vacío para una nueva entrada.


    if form.validate_on_submit() and is_ticket_editable_by_operator:
        try:
            new_status_id = form.status.data
            new_status_obj = db.session.execute(
                select(Status).filter_by(id=new_status_id)
            ).scalar_one_or_none()

            flash_status_msg = ''
            should_send_client_email = False 
            
            email_trigger_status_values = ['completed', 'cancelled']

            if new_status_obj:
                if ticket.status_id != new_status_obj.id:
                    ticket.status_id = new_status_obj.id
                    flash_status_msg = f'Estado cambiado a "{new_status_obj.name}".'
                    
                    if new_status_obj.value in email_trigger_status_values:
                        if old_status_value not in email_trigger_status_values:
                            should_send_client_email = True
                            flash_status_msg += ' Se enviará notificación al cliente.'
                else:
                    flash_status_msg = 'El estado no fue modificado.'
            else:
                flash_status_msg = 'Advertencia: Estado seleccionado no válido.'
            
            # Lógica para manejar completed_timestamp
            if new_status_obj and new_status_obj.value in ['completed', 'cancelled'] and old_status_value not in ['completed', 'cancelled', 'closed']:
                ticket.completed_timestamp = datetime.now(timezone.utc)
            elif ticket.completed_timestamp and new_status_obj and new_status_obj.value in editable_status_values:
                ticket.completed_timestamp = None
                flash_status_msg += ' Fecha de finalización eliminada (ticket reabierto).'

            ticket.modified_timestamp = datetime.now(timezone.utc)

            new_values = get_ticket_attributes_for_history(ticket)

            operator_note = form.operator_notes.data
            change_details_msg = f'Notas del operador: {operator_note}' if operator_note else None
            if flash_status_msg:
                change_details_msg = f'{flash_status_msg}. {change_details_msg}' if change_details_msg else flash_status_msg

            log_ticket_change(
                ticket=ticket,
                changed_by_persona=current_user,
                change_type='Actualización de Ticket por Operador', # Puedes hacer esto más específico si solo hubo cambio de estado/nota
                old_values=old_values,
                new_values=new_values,
                change_details=change_details_msg 
            )

            db.session.add(ticket)
            db.session.commit()
        
            flash(f'Ticket {ticket.id} actualizado exitosamente. {flash_status_msg}', 'success')
            
            # --- LÓGICA DE ENVÍO DE CORREO AL CLIENTE ---
            if should_send_client_email and ticket.creator_obj and ticket.creator_obj.email: 
                # Variables para la plantilla del cliente
                new_status_display_name = new_status_obj.name.capitalize() if new_status_obj else "Desconocido" # Usa .name para el nombre legible
                acting_operator_name = current_user.username if current_user and current_user.username else "Operador Desconocido"
                
                subject = f"Actualización de su Ticket #{ticket.id} - {new_status_display_name}"
                
                # Generar URL del ticket para el cliente
                # Asegúrate de que 'client_bp' y 'view_ticket_detail' existan en tus rutas de cliente
                ticket_url_for_client = url_for('client_bp.client_tickets', ticket_id=ticket.id, _external=True) 

                send_notification_email(
                    subject=subject,
                    recipients=[ticket.creator_obj.email],
                    template='emails/ticket_updated.html', # La plantilla del cliente
                    ticket_id=ticket.id, 
                    ticket_title=ticket.description, # Asumo que description es el "título"
                    client_name=ticket.creator_obj.username, 
                    new_status_name=new_status_display_name, 
                    operator_name=acting_operator_name,      
                    ticket_url=ticket_url_for_client 
                )
                logger.info(f"Correo enviado al cliente ({ticket.creator_obj.email}) por actualización de ticket #{ticket.id}.")
            elif should_send_client_email and (not ticket.creator_obj or not ticket.creator_obj.email):
                logger.warning(f"No se pudo enviar correo al cliente para ticket #{ticket.id}: Email del creador no disponible o objeto creador nulo.")

            return redirect(url_for('operator_bp.operator_tickets'))

        except SQLAlchemyError as e:
            db.session.rollback()
            # --- Logger: ERROR - Intento de modificación de ticket fallido ---
            logger.error(f'Intento de modificación de ticket fallido: Ticket ID: {ticket_id} no pudo editarse por el usuario {current_user.username} (ID: {current_user.id})',exc_info=True)
            flash(f'Ocurrió un error al editar el ticket: {e}', 'error')
        except Exception as e:
            # --- Logger: ERROR - Error inesperado ---
            db.session.rollback()
            message=f"Ocurrió un error inesperado. Por favor, contacte a soporte. Detalles: '{e}'", 'error'
            logger.error(f'Al intentar modificar el ticket: {message}',exc_info=True)
            flash(message, 'error')
    
    elif not is_ticket_editable_by_operator and request.method == 'POST':
        flash('Este ticket no puede ser modificado por el operador en su estado actual.', 'warning')

    return render_template('operator/operator_ticket_detail.html',
                           title=f'Detalle Ticket #{ticket.id}',
                           form=form,
                           ticket=ticket,
                           is_ticket_editable_by_operator=is_ticket_editable_by_operator)   


# ------------------------------------------------------------------------------
#               FUNCIÓN: HISTORICO DE TICKETS (ACCESIBLE A TODOS LOS PERFIELS)
# ------------------------------------------------------------------------------
@operator_bp.route('/ticket/<int:ticket_id>/history', methods=['GET'])
@login_required # Sigue siendo necesario para asegurar que solo usuarios autenticados accedan
def ticket_history(ticket_id):
    """
    Muestra el historial de cambios para un ticket específico.
    Si el usuario puede acceder a esta ruta, se asume que tiene permisos para ver el ticket.
    """
    ticket = db.session.execute(
        select(Ticket).filter_by(id=ticket_id)
    ).scalar_one_or_none()

    if not ticket:
        flash('Ticket no encontrado.', 'danger')
        # Redirige a una página segura si el ticket no existe
        # Considera una página de error o la página principal de un usuario
        return redirect(url_for('main_bp.index')) # O a 'client_bp.my_tickets' si es un cliente, etc.

    # ** Lógica de permisos removida aquí **
    # La presunción es que si el usuario logró acceder a la URL para ver el historial de `ticket_id`,
    # ya ha pasado por una verificación de permisos en la página de detalle del ticket.
    # Si esa verificación falló, nunca habrían llegado a esta URL.

    history_records = db.session.execute(
        select(TicketHistory)
        .filter_by(ticket_id=ticket_id)
        .order_by(TicketHistory.change_timestamp.desc())
    ).scalars().all()

    # --- Logger: INFO - Consulta de histórico por parte del usuario ---
    logger.info(f'Usuario {current_user.username} (ID: {current_user.id}) consultó el registro histórico del ticket {ticket.id}.')

    # Este diccionario `changed_by_users` sigue siendo útil si no confías totalmente
    # en las relaciones de SQLAlchemy para cargar los usernames directamente,
    # o si quieres mapearlos a IDs por eficiencia.
    # No obstante, si `record.changed_by.username` funciona, puedes simplificar la plantilla.
    changed_by_users = {record.changed_by.id: record.changed_by.username for record in history_records if record.changed_by}

    # Captura la URL de referencia (la página anterior)
    # Si no hay referrer (ej. si se accedió directamente a la URL), puedes proporcionar una URL por defecto
    referrer_url = request.referrer if request.referrer else url_for('main_bp.index')


    return render_template(
        'ticket_history.html',
        ticket=ticket,
        history_records=history_records,
        changed_by_users=changed_by_users, # Pasar esto por seguridad o consistencia
        referrer_url=referrer_url
    )