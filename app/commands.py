# app/commands.py

from flask.cli import with_appcontext
from app import mongo
from app.auth.models import Persona
import click
import pymongo
import secrets
import string
from datetime import datetime

@click.command("init-db-data")
@with_appcontext
def init_db_data_command():
    """Inicializa la base de datos con datos básicos (roles, estados, categorías y usuarios de ejemplo)."""
    print("Iniciando carga de datos iniciales para MongoDB...")
    
    try:
        # --- Cargar Roles ---
        if mongo.db.roles.count_documents({}) == 0:
            print("Cargando roles iniciales...")
            roles_data = [
                {'name': 'Administrador', 'value': 'admin'},
                {'name': 'Supervisor', 'value': 'supervisor'},
                {'name': 'Operador', 'value': 'operador'},
                {'name': 'Cliente', 'value': 'cliente'},
            ]
            mongo.db.roles.insert_many(roles_data)
            print("Roles cargados.")
        else:
            print("Los Roles ya existen.")

        # --- Cargar Status ---
        if mongo.db.statuses.count_documents({}) == 0:
            print("Cargando estados iniciales...")
            statuses_data = [
                {'name': 'Pendiente', 'value': 'pending'},
                {'name': 'En Progreso', 'value': 'in_progress'},
                {'name': 'Completado', 'value': 'completed'},
                {'name': 'Cerrado', 'value': 'closed'},
                {'name': 'Cancelado', 'value': 'cancelled'},
                {'name': 'Rechazado', 'value': 'rejected'},
            ]
            mongo.db.statuses.insert_many(statuses_data)
            print("Estados cargados.")
        else:
            print("Los Estados ya existen.")

        # --- Cargar Categorías (Originales) ---
        if mongo.db.categories.count_documents({}) == 0:
            print("Cargando categorías iniciales...")
            categories_data = [
                {'name': 'General', 'value': 'general'},
                {'name': 'Mantenimiento', 'value': 'mantenimiento'},
                {'name': 'Redes', 'value': 'redes'},
                {'name': 'Soporte Técnico', 'value': 'soporte_tecnico'},
                {'name': 'Hardware', 'value': 'hardware'},
                {'name': 'software', 'value': 'software'},
                {'name': 'Delineante', 'value': 'delineante'},
                {'name': 'Periodismo', 'value': 'periodismo'},
            ]
            mongo.db.categories.insert_many(categories_data)
            print("Categorías cargadas.")
        else:
            print("Las Categorías ya existen.")

        # --- Cargar Usuarios de Ejemplo (incluyendo supervisores específicos) ---
        users_to_create_data = [
            {'username': 'admin', 'name': 'Admin', 'firstSurname': 'User', 'email': 'lrguardamagna.etra@grupoetra.com', 'role': 'admin'},
            {'username': 'supervisor_general', 'name': 'Supervisor', 'firstSurname': 'General', 'email': 'supervisor.general@example.com', 'role': 'supervisor'},
            {'username': 'supervisor_delineante', 'name': 'Supervisor', 'firstSurname': 'Delineante', 'email': 'supervisor.delineante@example.com', 'role': 'supervisor'},
            {'username': 'supervisor_ingenieria', 'name': 'Supervisor', 'firstSurname': 'Ingenieria', 'email': 'supervisor.ingenieria@example.com', 'role': 'supervisor'},
            {'username': 'operador', 'name': 'Operador', 'firstSurname': 'Demo', 'email': 'operador@example.com', 'role': 'operador'},
            {'username': 'cliente', 'name': 'Cliente', 'firstSurname': 'Demo', 'email': 'cliente@example.com', 'role': 'cliente'},
        ]

        for user_data_item in users_to_create_data:
            username = user_data_item['username']
            if not mongo.db.personas.find_one({"username": username}):
                print(f"Creando usuario '{username}'...")
                
                alphabet = string.ascii_letters + string.digits + string.punctuation
                password = ''.join(secrets.choice(alphabet) for i in range(12))
                
                user = Persona(
                    username=username,
                    name=user_data_item['name'],
                    firstSurname=user_data_item['firstSurname'],
                    email=user_data_item['email'],
                    role=user_data_item['role'],
                    password=password,
                    password_changed_at=datetime.utcnow(),
                    two_factor_code=None,
                    two_factor_code_expiration=None
                )
                
                user_dict = user.__dict__
                user_dict.pop("id", None)
                mongo.db.personas.insert_one(user_dict)
                
                print(f"Usuario '{username}' creado con éxito.")
                print(f"  -> Contraseña para '{username}': {password}")
            else:
                print(f"El usuario '{username}' ya existe.")

        print("\nCarga de datos iniciales finalizada con éxito.")

    except pymongo.errors.PyMongoError as e:
        print(f"\nERROR: Ocurrió un error de base de datos durante la inicialización: {e}")
    except Exception as e:
        print(f"\nERROR: Ocurrió un error inesperado durante la inicialización: {e}")