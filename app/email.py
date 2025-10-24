from flask_mail import Message
from app import mail # Importa la instancia de Mail de tu app principal
from flask import render_template, current_app # CAMBIO CLAVE: Importar url_for aquí también
from threading import Thread
import threading

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
    
    threading.Thread(target=send_email_async, args=(current_app._get_current_object(), msg)).start()
    current_app.logger.debug(f"Email '{subject}' en cola para: {recipients}")

def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_notification_email(
        subject='Restablecer Contraseña - [TuApp]',
        recipients=[user.email],
        template='email/reset_password.html',
        user=user,
        token=token
    )