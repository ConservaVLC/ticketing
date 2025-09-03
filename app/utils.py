# app/ticket_management/utils.py

from app import db
from app.models import Ticket, TicketHistory, Category, Status
from app.auth.models import Persona
from datetime import datetime, timezone
from flask_login import current_user # Asumimos que current_user está disponible
from sqlalchemy import select, cast, String
from flask_mail import Message
from flask import render_template, current_app, request
from app import mail

def log_email_send_error(recipient_email, subject, error_message, exc_info=False):
    """
    Registra un error ocurrido durante el intento de envío de un correo electrónico.

    Args:
        recipient_email (str): La dirección de correo electrónico del destinatario.
        subject (str): El asunto del correo electrónico que falló.
        error_message (str): Un mensaje de error específico (ej. "Conexión SMTP fallida").
        exc_info (bool): Si es True, añade la información de la excepción (traceback) al log.
                         Por defecto es False.
    """
    current_app.logger.error(
        f"Error al enviar correo electrónico a '{recipient_email}' con asunto '{subject}': {error_message}",
        exc_info=exc_info
    )

def get_ticket_attributes_for_history(ticket_obj):
    """
    Retorna un diccionario con los valores de los atributos clave de un objeto Ticket
    que son relevantes para el registro de historial.
    Esto ayuda a evitar la repetición al capturar old_values y new_values.
    """
    if not ticket_obj:
        return {
            'category_id': None,
            'status_id': None,
            'description': None,
            'observation': None,
            'asignated_supervisor_id': None,
            'asigned_operator_id': None,
        }

    return {
        'category_id': ticket_obj.category_id,
        'status_id': ticket_obj.status_id,
        'description': ticket_obj.description,
        'observation': ticket_obj.observation,
        'asignated_supervisor_id': ticket_obj.asignated_supervisor_id,
        'asigned_operator_id': ticket_obj.asigned_operator_id,
        # Asegúrate de que esta lista coincida con el 'field_map' en log_ticket_change
    }

def get_ticket_attributes_for_history(ticket):
    """
    Recopila los atributos clave de un ticket para fines de historial.
    Retorna un diccionario con los IDs y/o valores de los campos.
    """
    return {
        'category_id': ticket.category_id,
        'status_id': ticket.status_id,
        'description': ticket.description,
        'observation': ticket.observation,
        'asignated_supervisor_id': ticket.asignated_supervisor_id,
        'asigned_operator_id': ticket.asigned_operator_id,
        # Puedes añadir más atributos si los estás rastreando en el historial
        'title': ticket.title, # Si el título puede cambiar
        'completed_timestamp': ticket.completed_timestamp,
    }


def log_ticket_change(
    ticket: Ticket,
    changed_by_persona: Persona,
    change_type: str,
    old_values: dict,
    new_values: dict,
    change_details: str = None # <--- ¡Este es el nuevo parámetro!
):
    """
    Registra un cambio en un ticket en la tabla TicketHistory.

    :param ticket: El objeto Ticket que ha sido modificado.
    :param changed_by_persona: El objeto Persona que realizó el cambio.
    :param change_type: Una descripción del tipo de cambio (ej. 'Edición', 'Cambio de Estado').
    :param old_values: Un diccionario con los valores antiguos de los atributos clave.
    :param new_values: Un diccionario con los nuevos valores de los atributos clave.
    :param change_details: Una descripción textual opcional del cambio o notas adicionales.
    """
    # Comparar y obtener solo los campos que realmente cambiaron, o usar los proporcionados
    # para `previous_` y `new_` si la lógica de comparación está en otro lugar
    
    # Para la descripción y observación, siempre guardamos la versión completa si está en old/new_values
    prev_description_val = old_values.get('description')
    new_description_val = new_values.get('description')

    prev_observation_val = old_values.get('observation')
    new_observation_val = new_values.get('observation')

    # Determinar si el campo realmente cambió, para evitar guardar "N/A -> N/A"
    prev_category_id_val = old_values.get('category_id')
    new_category_id_val = new_values.get('category_id')
    if prev_category_id_val == new_category_id_val and 'category_id' in old_values: # Si no cambió, no lo guardamos explícitamente a menos que sea una creación
        prev_category_id_val = None
        new_category_id_val = None

    prev_status_id_val = old_values.get('status_id')
    new_status_id_val = new_values.get('status_id')
    if prev_status_id_val == new_status_id_val and 'status_id' in old_values:
        prev_status_id_val = None
        new_status_id_val = None
        
    prev_supervisor_id_val = old_values.get('asignated_supervisor_id')
    new_supervisor_id_val = new_values.get('asignated_supervisor_id')
    if prev_supervisor_id_val == new_supervisor_id_val and 'asignated_supervisor_id' in old_values:
        prev_supervisor_id_val = None
        new_supervisor_id_val = None

    prev_operator_id_val = old_values.get('asigned_operator_id')
    new_operator_id_val = new_values.get('asigned_operator_id')
    if prev_operator_id_val == new_operator_id_val and 'asigned_operator_id' in old_values:
        prev_operator_id_val = None
        new_operator_id_val = None


    history_entry = TicketHistory(
        ticket_id=ticket.id,
        changed_by_id=changed_by_persona.id,
        change_type=change_type,
        change_timestamp=datetime.now(timezone.utc),
        
        # Asignar los valores antiguos y nuevos, solo si han sido proporcionados
        previous_category_id=prev_category_id_val,
        new_category_id=new_category_id_val,

        previous_status_id=prev_status_id_val,
        new_status_id=new_status_id_val,

        previous_description=prev_description_val,
        new_description=new_description_val,

        previous_observation=prev_observation_val,
        new_observation=new_observation_val,

        previous_supervisor_id=prev_supervisor_id_val,
        new_supervisor_id=new_supervisor_id_val,

        previous_operator_id=prev_operator_id_val,
        new_operator_id=new_operator_id_val,

        change_details=change_details # <--- ¡Aquí se asigna al modelo!
    )
    db.session.add(history_entry)
    # db.session.commit() # No se hace commit aquí, se espera que la función que llama haga el commit.


def send_email_async(app, msg):
    """Función auxiliar para enviar correos en un hilo separado."""
    with app.app_context(): # Es crucial para que Flask-Mail funcione en un hilo
        try:
            mail.send(msg)
            app.logger.info(f"Correo '{msg.subject}' enviado exitosamente a {msg.recipients}.")
        except Exception as e:
            app.logger.error(f"Error asíncrono al enviar correo '{msg.subject}' a {msg.recipients}: {str(e)}", exc_info=True)


def send_notification_email(subject, recipients, template, **kwargs):
    """
    Función de utilidad para enviar correos electrónicos.
    :param subject: Asunto del correo.
    :param recipients: Lista de direcciones de correo electrónico.
    :param template: Nombre de la plantilla Jinja2 (ej. 'emails/ticket_created.html').
    :param kwargs: Argumentos adicionales para la plantilla del correo.
    """
    msg = Message(subject,
                  sender=current_app.config['MAIL_USERNAME'],
                  recipients=recipients)
    msg.html = render_template(template, **kwargs)
    
    # Opcional: Para el cuerpo de texto plano si no se muestra HTML
    msg.body = render_template(template, **kwargs).replace('<br>', '\n').replace('</p>', '\n').replace('<p>', '') 
    # ^ Esto es una simplificación muy básica, idealmente tendrías una plantilla de texto plano separada.

    # Envío asíncrono usando un hilo (simple, para depuración/desarrollo)
    # Para producción, considera Celery o similar para tareas en segundo plano.
    import threading
    threading.Thread(target=send_email_async, args=(current_app._get_current_object(), msg)).start()
    
    # Envío síncrono (bloquea la petición, no recomendado para producción)
    # mail.send(msg)
    print(f"DEBUG: Email '{subject}' queued for recipients: {recipients}") # Solo para depuración

def get_filtered_tickets_query(form=None, filter_by_user_role=True):
    """
    Construye y devuelve un objeto de consulta de SQLAlchemy para tickets,
    aplicando filtros según el rol del usuario actual y los criterios del formulario.

    :param form: Una instancia de TicketFilterForm o None si no se usa formulario.
    :param filter_by_user_role: Si es True, aplica el filtro de rol (cliente, operador, supervisor).
                                Si es False (ej. para admin), no aplica este filtro de rol base.
    :return: Un objeto de consulta de SQLAlchemy (Select object).
    """
    query = db.select(Ticket)

    # --- FILTRADO BASE POR ROL DEL USUARIO AUTENTICADO ---
    if filter_by_user_role:
        if current_user.is_client:
            # Los clientes solo ven los tickets que han creado
            query = query.filter(Ticket.creator_id == current_user.id)
        elif current_user.is_operator:
            # Los operadores solo ven los tickets que tienen asignados
            query = query.filter(Ticket.asigned_operator_id == current_user.id)
        elif current_user.is_supervisor:
            # Los supervisores solo ven los tickets que tienen asignados
            query = query.filter(Ticket.asignated_supervisor_id == current_user.id)
        # Nota: Si current_user es admin, no entra en ninguna de estas condiciones
        # y la 'query' permanece como 'db.select(Ticket)', lo que significa todos.
    
    # Realiza JOINs necesarios para los filtros del formulario o para mostrar datos
    # Estos JOINs se hacen aquí para que estén disponibles para CUALQUIER filtro de formulario
    query = query.join(Category, Ticket.category_id == Category.id, isouter=True)
    query = query.join(Status, Ticket.status_id == Status.id, isouter=True)
    
    Creator = db.aliased(Persona)
    Operator = db.aliased(Persona)
    Supervisor = db.aliased(Persona)
    
    query = query.join(Creator, Ticket.creator_id == Creator.id, isouter=True)
    query = query.join(Operator, Ticket.asigned_operator_id == Operator.id, isouter=True)
    query = query.join(Supervisor, Ticket.asignated_supervisor_id == Supervisor.id, isouter=True)

    # --- APLICAR FILTROS DEL FORMULARIO (si se proporciona un formulario) ---
    if form and (form.validate() or request.method == 'GET'): # 'request' necesita ser importado si esta funcion no esta en el contexto de una ruta Flask
        # Nota: Si esta función no se llama desde una ruta Flask, 'request' no estaría disponible.
        # En ese caso, la validación del formulario debería ocurrir antes de llamar a esta función.
        # Para simplificar, asumimos que esta función se llamará dentro del contexto de una solicitud Flask.

        if form.ticket_id.data:
            search_term = f"%{form.ticket_id.data}%"
            query = query.filter(cast(Ticket.id, String).ilike(search_term))
        
        if form.search_title.data:
            search_term = f"%{form.search_title.data}%"
            query = query.filter(Ticket.title.ilike(search_term))

        if form.creator_obj.data:
            search_term = f"%{form.creator_obj.data}%"
            # Filtra sobre la columna `username` del alias del creador
            query = query.filter(Creator.username.ilike(search_term))

        if form.category_name.data:
            search_term = f"%{form.category_name.data}%"
            query = query.filter(Category.name.ilike(search_term))

        if form.status_name.data:
            search_term = f"%{form.status_name.data}%"
            query = query.filter(Status.name.ilike(search_term))
        
        if form.operator_username.data:
            search_term = f"%{form.operator_username.data}%"
            query = query.filter(Operator.username.ilike(search_term))

        if form.supervisor_username.data:
            search_term = f"%{form.supervisor_username.data}%"
            query = query.filter(Supervisor.username.ilike(search_term))

        if form.start_date.data:
            start_datetime_utc = datetime.combine(form.start_date.data, datetime.min.time()).replace(tzinfo=timezone.utc)
            query = query.filter(Ticket.timestamp >= start_datetime_utc)

        if form.end_date.data:
            end_datetime_utc = datetime.combine(form.end_date.data, datetime.max.time()).replace(tzinfo=timezone.utc)
            query = query.filter(Ticket.timestamp <= end_datetime_utc)
            
    return query
