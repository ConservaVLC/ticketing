# app/utils.py

from datetime import datetime, timezone
from flask_mail import Message
from flask import render_template, current_app
from app import mail, mongo
from bson.objectid import ObjectId

def log_ticket_history(ticket_id, change_type, changed_by_user, details=""):
    """
    Añade una entrada de historial a un ticket en MongoDB.
    El historial se guarda como un array de sub-documentos dentro del ticket.
    """
    try:
        history_entry = {
            "entry_id": ObjectId(),
            "change_type": change_type,
            "changed_by": {
                "user_id": ObjectId(changed_by_user.id),
                "username": changed_by_user.username
            },
            "timestamp": datetime.now(timezone.utc),
            "details": details
        }
        mongo.db.tickets.update_one(
            {"_id": ObjectId(ticket_id)},
            {"$push": {"history": {"$each": [history_entry], "$position": 0}}} # Añade al principio
        )
    except Exception as e:
        current_app.logger.error(f"Error al registrar historial para ticket {ticket_id}: {e}", exc_info=True)

def send_email_async(app, msg):
    """Función auxiliar para enviar correos en un hilo separado."""
    with app.app_context():
        try:
            mail.send(msg)
            app.logger.info(f"Correo '{msg.subject}' enviado exitosamente a {msg.recipients}.")
        except Exception as e:
            current_app.logger.error(f"Error asíncrono al enviar correo '{msg.subject}' a {msg.recipients}: {str(e)}", exc_info=True)

def send_notification_email(subject, recipients, template, **kwargs):
    """
    Función de utilidad para enviar correos electrónicos.
    """
    msg = Message(subject,
                  sender=current_app.config['MAIL_DEFAULT_SENDER'] or current_app.config['MAIL_USERNAME'],
                  recipients=recipients)
    msg.html = render_template(template, **kwargs)
    
    import threading
    threading.Thread(target=send_email_async, args=(current_app._get_current_object(), msg)).start()
    current_app.logger.debug(f"Email '{subject}' en cola para: {recipients}")