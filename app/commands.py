# Inicialización de carga de datos en BBDD

# app/commands.py

from flask.cli import with_appcontext # Para asegurar el contexto de la app
from app import db # Importa la instancia de db
from app.auth.models import Persona, Role # Importa tus modelos
from app.models import Ticket, Status, Category
from werkzeug.security import generate_password_hash # Para las contraseñas si las creas aquí

import click # Necesario para los comandos de Flask CLI

@click.command('init-db-data')
@with_appcontext # Asegura que el comando se ejecute con el contexto de la aplicación
def init_db_data_command():
    """Inicializa la base de datos con datos por defecto (Status, Category, Admin User, etc.)."""
    print("Iniciando carga de datos iniciales...")

    # --- Cargar Status (si no existen individualmente) ---
    print("Verificando y cargando estados iniciales...")
    statuses_data = [
        {'name': 'Pendiente', 'value': 'pending'},
        {'name': 'En Progreso', 'value': 'in_progress'},
        {'name': 'Completado', 'value': 'completed'},
        {'name': 'Cerrado', 'value': 'closed'},
        {'name': 'Cancelado', 'value': 'cancelled'},
        {'name': 'Rechazado', 'value': 'rejected'}, # <-- ¡Asegúrate de que esta línea esté aquí!
    ]
    
    for s_data in statuses_data:
        # Busca si el estado ya existe por su 'value'
        existing_status = db.session.execute(db.select(Status).filter_by(value=s_data['value'])).scalar_one_or_none()
        if not existing_status:
            # Si no existe, lo añade
            status = Status(name=s_data['name'], value=s_data['value'])
            db.session.add(status)
            print(f"  - Añadiendo estado: {s_data['name']}")
        else:
            # Si ya existe, simplemente informa
            print(f"  - El estado '{s_data['name']}' ya existe.")
    db.session.commit()
    print("Estados procesados.")

    # --- Cargar Categorías (si no existen) ---
    if not Category.query.first():
        print("Cargando categorías iniciales...")
        categories_data = [
            {'name': 'General', 'value': 'general'},
            {'name': 'Mantenimiento', 'value': 'mantenimiento'},
            {'name': 'Redes', 'value': 'redes'},
            {'name': 'Soporte Técnico', 'value': 'soporte_tecnico'},
            {'name': 'Hardware', 'value': 'hardware'},
            {'name': 'Software', 'value': 'software'},
            {'name': 'Delineante', 'value': 'delineante'},
            {'name': 'Periodismo', 'value': 'periodismo'},
        ]
        for cat_data in categories_data:
            category = Category(name=cat_data['name'], value=cat_data['value'])
            db.session.add(category)
        db.session.commit()
        print("Categorías cargadas.")
    else:
        print("Las categorías ya existen.")
    

    # --- Cargar Roles (si no existen) ---
    if not Role.query.first():
        print("Cargando roles iniciales...")
        role_data = [
            {'name': 'Administrador', 'value': 'admin'},
            {'name': 'Delegado', 'value': 'delegado'},
            {'name': 'Encargado', 'value': 'encargado'},
            {'name': 'Supervisor', 'value': 'supervisor'},
            {'name': 'Coordinador', 'value': 'coordinador'},
            {'name': 'Operador', 'value': 'operador'},
            {'name': 'Conductor', 'value': 'conductor'},
            {'name': 'Delineante', 'value': 'delineante'},
            {'name': 'Ingeniería', 'value': 'ingenieria'},
            {'name': 'Operario', 'value': 'operario'},
            {'name': 'Cliente', 'value': 'cliente'},
        ]

        for role in role_data:
            category = Role(name=role['name'], value=role['value'])
            db.session.add(category)
        db.session.commit()
        print("Roles cargados.")
    else:
        print("Los Roles ya existen.")


    # --- Cargar Usuario Administrador (si no existe) ---
    if not Persona.query.filter_by(username='admin').first():
        print("Creando usuario 'admin'...")
        admin_user = Persona(
            username='admin',
            name= 'admin',
            firstSurname='admin',
            email='admin@example.com',
            role_id=1,
        )
        admin_user.set_password('admin') # ¡Cambia esto por una contraseña segura!
        db.session.add(admin_user)
        db.session.commit()
        print("Usuario 'admin' creado.")
    else:
        print("El usuario 'admin' ya existe.")
        
    # --- Cargar Usuario Supervisor (si no existe) ---
    if not Persona.query.filter_by(username='supervisor1').first():
        print("Creando usuario 'supervisor1'...")
        supervisor_user = Persona(
            username='supervisor1',
            name= 'super',
            firstSurname='super',
            email='supervisor1@example.com',
            role_id=4
        )
        supervisor_user.set_password('super') # ¡Cambia esto!
        db.session.add(supervisor_user)
        db.session.commit()
        print("Usuario 'supervisor1' creado.")
    else:
        print("El usuario 'supervisor1' ya existe.")

    print("Datos iniciales cargados con éxito.")