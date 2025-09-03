from flask import render_template, flash, redirect, url_for, send_file, Response, current_app
from flask_login import login_required, current_user
from app.supervisor import supervisor_bp
from app import db
from app.models import Ticket
from sqlalchemy.exc import SQLAlchemyError
from .forms import TicketEditForm, AssignTicketForm, TicketFilterForm
from ..models import Ticket, Status, Category
from app.utils import log_ticket_change, get_ticket_attributes_for_history, send_notification_email, get_filtered_tickets_query
from app.auth.models import Persona
from sqlalchemy import  select, cast, String, and_
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from flask import request
from app.auth.decorators import admin_required, supervisor_or_admin_required

from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

import logging


logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
#               FUNCIÓN: LISTADO DE TICKETS FILTRABLE (SUPERVISOR/ADMINISTRADOR)
# ------------------------------------------------------------------------------
@supervisor_bp.route('/tickets', methods=['GET', 'POST'])
@login_required
@supervisor_or_admin_required
def list_tickets():
    form = TicketFilterForm(request.args)

    if form.clear_filters.data:
        return redirect(url_for('supervisor_bp.list_tickets'))
    
    # Aquí filter_by_user_role=False, porque el admin debe ver TODOS,
    # y el supervisor se filtra internamente en get_filtered_tickets_query
    query = get_filtered_tickets_query(form=form, filter_by_user_role=True) 
    # El filtro de rol 'is_supervisor' se aplica dentro de get_filtered_tickets_query
    # para el supervisor, y no se aplica para el admin.

    # Ordena y ejecuta la consulta
    tickets = db.session.execute(query.order_by(Ticket.timestamp.desc())).scalars().all()

    logger.info(f'Usuario {current_user.username} (ID: {current_user.id}) consultó los tickets. Se encontraron {len(tickets)} tickets (el número puede variar por aplicación de filtros)')

    export_url_args = request.args.copy()
    
    return render_template(
        'supervisor/list_tickets.html', 
        tickets=tickets, 
        form=form, 
        export_url_args=export_url_args
    )

# -----------------------------------------------------------------------------------
#               FUNCIÓN: EXPORTACIÓN DE TICKETS A XLSX (SUPERVISOR/ADMINISTRADOR)
# -----------------------------------------------------------------------------------
@supervisor_bp.route('/export_tickets_to_xlsx', methods=['GET'])
@login_required
@supervisor_or_admin_required
def export_tickets_to_xlsx():
    form = TicketFilterForm(request.args) # El formulario ya captura los parámetros de la URL

    # --- ¡Aquí está la modificación clave! ---
    # Reutiliza la función de utilidad para obtener la consulta
    # 'filter_by_user_role=True' asegura que si es supervisor, solo verá sus tickets
    # y si es admin, verá todos.
    query = get_filtered_tickets_query(form=form, filter_by_user_role=True)
    # ------------------------------------------

    tickets_to_export = db.session.execute(query.order_by(Ticket.timestamp.desc())).scalars().all()

    # --- Generación del archivo XLSX con openpyxl ---
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Tickets"

    # Definir un estilo de encabezado (opcional, pero mejora la presentación)
    header_font = Font(bold=True)
    header_fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
    thin_border = Border(left=Side(style='thin'), 
                         right=Side(style='thin'), 
                         top=Side(style='thin'), 
                         bottom=Side(style='thin'))

    # Encabezados
    headers = [
        'ID', 'Título', 'Descripción', 'Creado Por', 'Categoría', 'Estado',
        'Operador Asignado', 'Supervisor Asignado', 'Fecha Creación',
        'Última Modificación'
    ]
    
    for col_num, header_text in enumerate(headers):
        cell = worksheet.cell(row=1, column=col_num + 1, value=header_text)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="center", vertical="center")
        worksheet.column_dimensions[chr(65 + col_num)].width = 15 # Ajusta ancho de columna

    # Datos
    for row_num, ticket in enumerate(tickets_to_export):
        row_data = [
            ticket.id,
            ticket.title,
            ticket.description,
            ticket.creator_obj.name,
            ticket.category_obj.name if ticket.category_obj else 'N/A',
            ticket.status_obj.name if ticket.status_obj else 'N/A',
            ticket.asigned_operator_obj.username if ticket.asigned_operator_obj else 'N/A',
            ticket.asignated_supervisor_obj.username if ticket.asignated_supervisor_obj else 'N/A',
            ticket.timestamp.strftime('%d/%m/%Y %H:%M') if ticket.timestamp else 'N/A',
            ticket.modified_timestamp.strftime('%d/%m/%Y %H:%M') if ticket.modified_timestamp else 'N/A'
        ]
        
        for col_num, cell_value in enumerate(row_data):
            cell = worksheet.cell(row=row_num + 2, column=col_num + 1, value=cell_value)
            cell.border = thin_border
            # Ajustar ancho de columnas específicas si es necesario
            if col_num == 1: # Título
                worksheet.column_dimensions[chr(65 + col_num)].width = 30
            elif col_num == 2: # Descripción
                worksheet.column_dimensions[chr(65 + col_num)].width = 50
            elif col_num == 3: # Creador
                worksheet.column_dimensions[chr(65 + col_num)].width = 20


    # Guardar el libro de trabajo en un objeto BytesIO
    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    # --- Logger: INFO - Usuario genera un reporte de tickets ---
    logger.info(f'El usuario {current_user.username} (ID: {current_user.id}) ha generado un reporte de tickets en ".xlsx"')

    return Response(
        output.read(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment;filename=tickets_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"}
    )


# -----------------------------------------------------------------------
#               FUNCIÓN: EDICIÓN DE TICKET (SUPERVISOR/ADMINISTRADOR)
# -----------------------------------------------------------------------
@supervisor_bp.route('/edit_ticket/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
@supervisor_or_admin_required

def edit_ticket(ticket_id):
    ticket = db.session.execute(select(Ticket).filter_by(id=ticket_id)).scalar_one_or_none()

    if not ticket:
        flash('Ticket no encontrado.', 'danger')
        return redirect(url_for('supervisor_bp.list_tickets')) 

    old_status_value = ticket.status_obj.value if ticket.status_obj else None
    old_category_id = ticket.category_id
    old_asigned_operator_id = ticket.asigned_operator_id
    old_observation = ticket.observation or "" 

    form = TicketEditForm(obj=ticket) 

    if request.method == 'GET':
        if ticket.category_obj:
            form.category.data = ticket.category_obj.id
        if ticket.status_obj:
            form.status.data = ticket.status_obj.id
        if ticket.asignated_supervisor_obj:
            form.supervisor.data = ticket.asignated_supervisor_obj.id
        else:
            form.supervisor.data = 0 

        if ticket.asigned_operator_obj:
            form.operator.data = ticket.asigned_operator_obj.id 
        else:
            form.operator.data = 0 
        form.observation.data = ticket.observation


    if form.validate_on_submit():
        new_status_id = form.status.data
        new_category_id = form.category.data
        new_asigned_operator_id = form.operator.data 
        new_observation = form.observation.data or ""

        new_status_obj = db.session.execute(select(Status).filter_by(id=new_status_id)).scalar_one_or_none()
        new_status_value = new_status_obj.value if new_status_obj else None
        
        # Obtener el nombre legible del nuevo estado para las plantillas
        new_status_display_name = new_status_value.replace('_', ' ').capitalize() if new_status_value else "Desconocido"
        
        # Nombre del operador que realiza el cambio (el current_user)
        # Asumo que current_user tiene un atributo .username o .name
        acting_operator_name = current_user.username if current_user and current_user.username else "Administrador"


        old_values = get_ticket_attributes_for_history(ticket)

        try:
            ticket.description = form.description.data
            ticket.category_id = new_category_id
            ticket.observation = new_observation

            supervisor_id = form.supervisor.data
            ticket.asignated_supervisor_id = supervisor_id if supervisor_id != 0 else None

            operator_id = form.operator.data 
            ticket.asigned_operator_id = operator_id if operator_id != 0 else None

            if new_status_obj:
                ticket.status_id = new_status_obj.id
                if new_status_value in ['completed', 'closed']:
                    if not ticket.completed_timestamp:
                        ticket.completed_timestamp = datetime.now(timezone.utc)
                elif ticket.completed_timestamp and new_status_value not in ['completed', 'closed']:
                    ticket.completed_timestamp = None
            else:
                flash('Advertencia: Estado seleccionado no válido.', 'warning')
                

            ticket.modified_timestamp = datetime.now(timezone.utc)

            new_values_for_history = get_ticket_attributes_for_history(ticket) 

            log_ticket_change(
                ticket=ticket,
                changed_by_persona=current_user,
                change_type='Edición de Ticket',
                old_values=old_values,
                new_values=new_values_for_history
            )

            db.session.add(ticket)
            db.session.commit()
            
            # --- LÓGICA DE ENVÍO DE CORREOS ---

            # 1. Correo al Cliente (Creador del Ticket)
            client_email_conditions_met = False
            
            if (new_status_value in ['completed', 'canceled']) and (old_status_value != new_status_value):
                client_email_conditions_met = True
            
            if (new_status_value in ['completed', 'canceled']) and (new_observation and new_observation != old_observation):
                client_email_conditions_met = True

            if client_email_conditions_met and ticket.creator_obj and ticket.creator_obj: 
                subject = f"Actualización de su Ticket #{ticket.id} - {new_status_display_name}"
                
                # Generar URL del ticket para el cliente
                # Asegúrate de que 'client_bp' y 'client_ticket_detail' existan y sean correctos
                # Y que tu app esté configurada para generar _external=True URLs (ej. con SERVER_NAME en config)
                ticket_url_for_client = url_for('client_bp.view_ticket_detail', ticket_id=ticket.id, _external=True) 

                send_notification_email(
                    subject=subject,
                    recipients=[ticket.creator_obj.email],
                    template='emails/ticket_updated.html', # Usamos la plantilla correcta
                    ticket_id=ticket.id, # Pasa el ID del ticket
                    ticket_title=ticket.description, # Asumo que description es el "título"
                    client_name=ticket.creator_obj, # Pasa el nombre del cliente
                    new_status_name=new_status_display_name, # Pasa el nombre formateado
                    operator_name=acting_operator_name, # Pasa el nombre del operador que hizo el cambio
                    ticket_url=ticket_url_for_client # Pasa la URL del ticket
                )
                current_app.logger.info(f"Correo enviado al cliente ({ticket.creator_obj.email}) por actualización de ticket #{ticket.id}.")
            elif client_email_conditions_met and (not ticket.creator_obj or not ticket.creator_obj.email):
                current_app.logger.warning(f"No se pudo enviar correo al cliente para ticket #{ticket.id}: Email del creador no disponible.")


            # 2. Correo al Operador Asignado
            operator_email_conditions_met = False
            
            if new_asigned_operator_id != old_asigned_operator_id:
                operator_email_conditions_met = True
            
            relevant_operator_states = ['pending', 'in_progress', 'closed', 'rejected']
            if (new_status_value in relevant_operator_states) and (old_status_value != new_status_value):
                operator_email_conditions_met = True
            
            if new_category_id != old_category_id:
                operator_email_conditions_met = True

            if (new_status_value in relevant_operator_states) and (new_observation and new_observation != old_observation):
                operator_email_conditions_met = True


            if operator_email_conditions_met and ticket.asigned_operator_obj and ticket.asigned_operator_obj.email:
                subject = f"Actualización de asignación de Ticket #{ticket.id}"
                
                send_notification_email(
                    subject=subject,
                    recipients=[ticket.asigned_operator_obj.email],
                    template='emails/ticket_assigned.html', # Usamos la plantilla correcta
                    ticket=ticket, # La plantilla assigned.html espera el objeto ticket completo
                    operator_name=ticket.asigned_operator_obj.username # Nombre del operador asignado
                )
                current_app.logger.info(f"Correo enviado al operador asignado ({ticket.asigned_operator_obj.email}) por actualización de ticket #{ticket.id}.")
            elif operator_email_conditions_met and (not ticket.asigned_operator_obj or not ticket.asigned_operator_obj.email):
                 current_app.logger.warning(f"No se pudo enviar correo al operador asignado para ticket #{ticket.id}: Operador no asignado o email no disponible.")
            
            current_app.logger.info(f'El usuario {current_user.username} (ID: {current_user.id}), ha modificado el ticket #{ticket.id}')
            flash(f'Ticket {ticket.id} actualizado exitosamente.', 'success')
            
            return redirect(url_for('supervisor_bp.list_tickets'))

        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Error al modificar ticket {ticket.id}: Usuario {current_user.username}, (ID: {current_user.id}): {str(e)}", exc_info=True) 
            flash(f'Ocurrió un error al guardar el ticket. Detalles: {e}', 'error')
        except Exception as e:
            db.session.rollback()
            message=f"Ocurrió un error inesperado. Por favor, contacte a soporte. Detalles: '{e}'"
            current_app.logger.error(f'AL editar el ticket: {message}',exc_info=True)
            flash(message, 'error')
            

    return render_template('supervisor/edit_ticket.html', title=f'Editar Ticket #{ticket.id}', form=form, ticket=ticket)


# -----------------------------------------------------------------------------------
#               FUNCIÓN: ASIGNACIÓN DE TICKET A OPERADORES (SUPERVISOR/ADMINISTRADOR)
# -----------------------------------------------------------------------------------

@supervisor_bp.route('/assign_ticket/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
@supervisor_or_admin_required

def assign_ticket(ticket_id):
    ticket = db.session.execute(select(Ticket).filter_by(id=ticket_id)).scalar_one_or_none()

    if not ticket:
        flash('Ticket no encontrado.', 'danger')
        return redirect(url_for('supervisor_bp.list_tickets')) # O a una lista de tickets

    # Si el ticket ya está asignado o cerrado, quizás no permitir reasignar sin más
    # if ticket.status_obj.value in ['assigned', 'in_progress', 'resolved', 'closed']:
    #     flash('Este ticket ya está en un estado que no permite reasignación directa.', 'warning')
    #     return redirect(url_for('supervisor_bp.ticket_detail', ticket_id=ticket.id))

    form = AssignTicketForm()

    # Si se envía el formulario
    if form.validate_on_submit():

        old_values = new_values = get_ticket_attributes_for_history(ticket)

        try:
            # Obtener el operador seleccionado
            operator_id = form.operator.data
            if operator_id == 0: # Si se seleccionó la opción por defecto
                flash('Por favor, selecciona un operador válido.', 'warning')
                return render_template('supervisor/assign_ticket.html', title='Asignar Ticket', form=form, ticket=ticket)

            selected_operator = db.session.execute(
                select(Persona).filter_by(id=operator_id)
            ).scalar_one_or_none()

            if not selected_operator:
                flash('Operador seleccionado no válido.', 'danger')
                return render_template('supervisor/assign_ticket.html', title='Asignar Ticket', form=form, ticket=ticket)

            # Obtener el estado "asignado"
            assigned_status = db.session.execute(select(Status).filter_by(value='in_progress')).scalar_one_or_none()
            if not assigned_status:
                flash('Error: El estado "Asignado" no se encontró en la base de datos. Por favor, contacte a un administrador.', 'error')
                return render_template('supervisor/assign_ticket.html', title='Asignar Ticket', form=form, ticket=ticket)
            
            operator_changed = ticket.asigned_operator_id != selected_operator.id

            # Asignar el operador y cambiar el estado del ticket
            ticket.asigned_operator_id = selected_operator.id
            ticket.status_id = assigned_status.id
            ticket.modified_timestamp = datetime.now(timezone.utc) # Actualizar la fecha de modificación

            new_values = new_values = get_ticket_attributes_for_history(ticket)

            log_ticket_change(
                ticket=ticket,
                changed_by_persona=current_user, # Asumiendo que current_user es la persona logueada
                change_type='Asignación de Operador', # Tipo de cambio específico para esta acción
                old_values=old_values,
                new_values=new_values
            )

            db.session.add(ticket)
            db.session.commit()

            # --- Logger: INFO - Operador asignado por el Administrador/Supervisor  ---
            logger.info(f'El usuario {current_user.username} (ID: {current_user.id}), ha asignado el ticket #{ticket.id} al operador {selected_operator.username}')

            flash(f'Ticket {ticket.id} asignado a {selected_operator.username} y estado cambiado a "{assigned_status.name}".', 'success')

            if operator_changed and ticket.asigned_operator_obj and ticket.asigned_operator_obj.email:
                try:
                    send_notification_email(
                        subject=f"Ticket Asignado: #{ticket.id}",
                        recipients=[ticket.asigned_operator_obj.email],
                        template='emails/ticket_assigned.html',
                        ticket=ticket,
                        operator_name=ticket.asigned_operator_obj.username
                    )
                    # --- Logger: INFO - Usuario genera un reporte de tickets ---
                    logger.info(f'Enviado correo al operador {ticket.asigned_operator_obj.email}')
                except Exception as e:
                    # --- Logger: WARNING - Correo no envíado ---
                    logger.warning(f"No se pudo enviar el correo al operador {ticket.asigned_operator_obj.email}: {e}")
                    flash('Advertencia: No se pudo enviar el correo de notificación al operador.', 'warning')

            return redirect(url_for('supervisor_bp.list_tickets', ticket_id=ticket.id)) # Redirigir a la vista de detalle del ticket

        except SQLAlchemyError as e:
            db.session.rollback()
            # --- Logger: ERROR - Fallo al asignar ticket a operador ---
            logger.error(f"Error al asinar el ticket {ticket.id} al usuario {ticket.asigned_operator_obj.name}: {str(e)}", exc_info=True) 
            flash(f'Ocurrió un error al asignar el ticket. Detalles: {e}', 'error')
        except Exception as e:
            db.session.rollback()
            # --- Logger: ERROR - Error inesperado ---
            message=f"Ocurrió un error inesperado. Por favor, contacte a soporte. Detalles: '{e}'", 'error'
            logger.error(f'AL asignar el ticket: {message}',exc_info=True)
            flash(message, 'error')

    # Para la petición GET o si la validación falla
    return render_template('supervisor/assign_ticket.html', title='Asignar Ticket', form=form, ticket=ticket)






