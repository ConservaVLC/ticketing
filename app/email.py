from flask_mail import Message
from app import mail # Importa la instancia de Mail de tu app principal
from flask import render_template, current_app # CAMBIO CLAVE: Importar url_for aquí también
from threading import Thread

def send_async_email(app, msg):
    # Función auxiliar para enviar el correo en un hilo separado
    with app.app_context():
        mail.send(msg)

def send_password_reset_email(user):
    token = user.get_reset_password_token() # Obtiene el token del modelo de usuario
    
    # Crea el mensaje de correo
    msg = Message('Restablecer Contraseña - [TuApp]',
                  sender=current_app.config['ADMINS'][0], # Remitente desde la configuración
                  recipients=[user.email])
    
    # Renderiza las plantillas de correo.
    # CAMBIO CLAVE: Al usar render_template, Jinja2 buscará en las carpetas de plantillas
    # configuradas. Si 'auth_bp' está registrado con su propio template_folder,
    # y las plantillas de email están DENTRO de ese template_folder, la ruta es relativa a él.
    # Por eso especificamos 'email/reset_password.txt' y 'email/reset_password.html'
    msg.body = render_template('email/reset_password.txt', user=user, token=token)
    msg.html = render_template('email/reset_password.html', user=user, token=token)
    
    # Envía el correo en un hilo separado para no bloquear la aplicación principal
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()