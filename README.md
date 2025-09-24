# Sistema de Gestión de Tickets

Este proyecto es una aplicación web full-stack desarrollada en Flask para la gestión de tickets de soporte o incidencias. Permite a los usuarios crear tickets, a los supervisores asignarlos y a los operadores resolverlos, manteniendo un historial completo de cada acción.

## Características Principales

- **Autenticación y Roles de Usuario:** Sistema de inicio de sesión seguro con diferentes niveles de permiso:
    - **Cliente:** Puede crear nuevos tickets, ver el estado de sus tickets, añadir comentarios y cerrar tickets resueltos.
    - **Operador:** Puede ver y gestionar los tickets que le han sido asignados, cambiar su estado y añadir notas.
    - **Supervisor:** Tiene una vista general de todos los tickets. Puede asignar tickets a los operadores, editar cualquier ticket y filtrar el listado.
    - **Administrador:** Tiene control total sobre el sistema, incluyendo la gestión de usuarios y categorías de tickets.
- **Gestión de Tickets:** Flujo de trabajo completo desde la creación hasta el cierre del ticket, pasando por estados como "Pendiente", "En Progreso", "Completado", "Rechazado" y "Cerrado".
- **Historial de Cambios:** Cada ticket registra un historial detallado de todas las modificaciones, incluyendo cambios de estado, asignaciones y notas, indicando qué usuario realizó el cambio y cuándo.
- **Notificaciones por Correo:** Envío automático de correos electrónicos para notificar eventos clave, como la creación de un ticket, la asignación a un operador o la actualización de su estado.
- **Filtro y Exportación:** Los supervisores y administradores pueden filtrar la lista de tickets por múltiples criterios (estado, categoría, fecha, etc.) y exportar los resultados a un archivo Excel (.xlsx).
- **Despliegue con Docker:** El proyecto está completamente configurado para ser desplegado fácilmente usando Docker y Docker Compose, aislando la aplicación y su base de datos.

## Stack Tecnológico

- **Backend:** Python, Flask
- **Base de Datos:** MongoDB (con Flask-PyMongo)
- **Frontend:** HTML, CSS, JavaScript, Jinja2 (motor de plantillas de Flask)
- **Contenerización:** Docker, Docker Compose
- **Librerías Python Clave:**
    - `Flask-Login`: Manejo de sesiones de usuario.
    - `Flask-WTF`: Creación y validación de formularios.
    - `Flask-PyMongo`: Interacción con la base de datos MongoDB.
    - `Flask-Mail`: Envío de correos electrónicos.
    - `openpyxl`: Generación de reportes en formato `.xlsx`.

---

## Instalación y Ejecución

### Opción 1: Usando Docker (Recomendado)

Este es el método más sencillo para levantar todo el entorno, incluyendo la base de datos.

**Requisitos:**
- Docker
- Docker Compose

**Pasos:**

1.  **Clonar el repositorio:**
    ```bash
    git clone <URL-DEL-REPOSITORIO>
    cd ticketing
    ```

2.  **Configurar variables de entorno (opcional):**
    Si necesitas configurar variables de entorno adicionales (ej. para correo electrónico), crea un archivo `.env` en la raíz del proyecto. Para la base de datos, la `MONGO_URI` ya está configurada en `docker-compose.yml` para desarrollo.

3.  **Construir y ejecutar los contenedores:**
    Desde la raíz del proyecto, ejecuta:
    ```bash
    docker-compose up --build
    ```
    Este comando construirá la imagen de la aplicación Flask, iniciará un contenedor para la base de datos MongoDB y otro para la aplicación. La aplicación será accesible en `http://localhost:5000`.

4.  **Inicializar la base de datos (solo la primera vez):**
    El comando `docker-compose up` ya ejecuta `flask init-db-data` automáticamente al iniciar el contenedor `tickets_web`, lo que se encarga de la inicialización de la base de datos y la creación de datos iniciales. No se requieren pasos manuales adicionales para la base de datos.

### Opción 2: Ejecución Local (Sin Docker)

**Requisitos:**
- Python 3.8+
- Un servidor de MongoDB instalado y en ejecución.

**Pasos:**

1.  **Clonar el repositorio e instalar dependencias:**
    ```bash
    git clone <URL-DEL-REPOSITORIO>
    cd ticketing
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

2.  **Configurar variables de entorno:**
    Crea un archivo `.env` en la raíz del proyecto y configúralo para que apunte a tu base de datos local de MongoDB.
    ```env
    # .env
    SECRET_KEY=un-secreto-muy-fuerte

    # Configuración de MongoDB
    MONGO_URI="mongodb://localhost:27017/ticketing_db" # Ajusta según tu configuración local

    # Configuración de email (ejemplo para Gmail)
    MAIL_SERVER=smtp.googlemail.com
    MAIL_PORT=587
    MAIL_USE_TLS=True
    MAIL_USERNAME=tu_correo@gmail.com
    MAIL_PASSWORD=tu_contraseña_de_aplicacion
    ```

3.  **Inicializar la base de datos (solo la primera vez):**
    ```bash
    flask init-db-data  # Para crear colecciones y datos iniciales
    ```

4.  **Ejecutar la aplicación:**
    ```bash
    flask run
    ```
    La aplicación estará disponible en `http://localhost:5000`.

## Ejecución de Pruebas

Para ejecutar el conjunto de pruebas unitarias, utiliza `pytest`:
```bash
pytest
```
