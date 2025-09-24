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

## Configuración para Despliegue en Google Cloud Run con MongoDB Atlas

Para desplegar esta aplicación en Google Cloud Run y conectarla a una instancia de MongoDB Atlas (especialmente si usas la capa gratuita M0, que no soporta VPC Peering), necesitarás configurar una red VPC dedicada con Cloud NAT y un conector de acceso a VPC (Serverless VPC Access connector), y luego configurar la lista de acceso IP en MongoDB Atlas.

### 1. Configurar una Red VPC Dedicada con Cloud NAT

Este es el método recomendado para que tu servicio de Cloud Run tenga una IP de salida estática y conocida, que podrás añadir a la lista de acceso IP de MongoDB Atlas.

1.  **Crear una Red VPC:**
    *   Ve a la consola de Google Cloud: `VPC Network` > `VPC networks`.
    *   Haz clic en `CREATE VPC NETWORK`.
    *   Asígnale un **nombre** (ej. `mongo-atlas-connection-nat`).
    *   Crea una **subred** en la región donde desplegarás Cloud Run (ej. `us-central1`).
    *   Deja las demás configuraciones por defecto o según tus necesidades.
2.  **Configurar Cloud Router:**
    *   Ve a `Network services` > `Cloud NAT`.
    *   Haz clic en `CREATE NAT GATEWAY`.
    *   Asígnale un **nombre**.
    *   Selecciona la **región** de tu subred.
    *   Selecciona el **Cloud Router** que se creará automáticamente o uno existente en la misma región.
    *   En `NAT IP addresses`, selecciona `Allocate new public IP address` y asígnale el nombre `static-ip-mongo-gcp` (o selecciona la IP estática ya creada con ese nombre).
    *   En `Network and subnets`, selecciona la **red VPC** (`mongo-atlas-connection-nat`) y la **subred** que creaste.
    *   Haz clic en `CREATE`.
3.  **Anota la IP pública estática** asignada a tu Cloud NAT (la asociada a `static-ip-mongo-gcp`). Esta IP es la que usarás para la lista de acceso IP en MongoDB Atlas.

### 2. Crear un Conector de Acceso a VPC (Serverless VPC Access)

Este conector permitirá que tu servicio de Cloud Run envíe tráfico a través de la red VPC que acabas de configurar, y por lo tanto, a través de la Cloud NAT con la IP estática.

1.  **Ve a la consola de Google Cloud:** Navega a `VPC Network` > `Serverless VPC Access`.
2.  **Crea un conector:**
    *   Haz clic en `CREATE CONNECTOR`.
    *   Asígnale un **nombre** (ej. `mongo-cloud-run-connector`).
    *   Selecciona la **región** donde desplegarás tu servicio de Cloud Run (debe ser la misma, ej. `us-central1`).
    *   Selecciona la **red VPC** que creaste (`mongo-atlas-connection-nat`).
    *   Define un **rango de IP** para el conector (ej. `10.8.0.0/28`). Asegúrate de que este rango no se superponga con ninguna otra subred en tu VPC.
    *   Haz clic en `CREATE`. La creación puede tardar unos minutos.

### 3. Configurar la Lista de Acceso IP en MongoDB Atlas

Ahora, añade la IP pública estática de tu Cloud NAT a la lista de acceso IP de tu clúster de MongoDB Atlas.

1.  **En MongoDB Atlas:**
    *   Navega a tu proyecto y selecciona `Network Access` en el menú lateral.
    *   En la pestaña `IP Access List`, haz clic en `ADD IP ADDRESS`.
    *   Selecciona `Add IP Address` y pega la IP pública estática de tu Cloud NAT (la asociada a `static-ip-mongo-gcp`).
    *   Añade una descripción (ej. "Cloud Run Egress IP via Cloud NAT").
    *   Haz clic en `CONFIRM`.

### 4. Configurar GitHub Secrets y Variables

Como se mencionó anteriormente, para que el workflow de GitHub Actions funcione correctamente, debes configurar los siguientes Secrets y Variables en la configuración de tu repositorio de GitHub (`Settings` > `Secrets and variables` > `Actions`):

**GitHub Secrets:**
*   `GCP_PROJECT_ID`: Tu ID de proyecto de Google Cloud.
*   `GCP_SA_KEY`: La clave JSON de tu cuenta de servicio de Google Cloud con los permisos adecuados (Usuario de cuenta de servicio, Administrador de Cloud Run, Escritor de Artifact Registry, Usuario de red de Compute).
*   `MONGO_URI`: Tu cadena de conexión de MongoDB Atlas.
*   `SECRET_KEY`: Una clave secreta fuerte para tu aplicación.
*   `GCS_BUCKET_NAME`: El nombre de tu Google Cloud Storage bucket (si lo usa la aplicación).

**GitHub Variables:**
*   `MAIL_SERVER`
*   `MAIL_PORT`
*   `MAIL_USE_TLS`
*   `MAIL_USERNAME`
*   `MAIL_PASSWORD`
*   `MAIL_DEFAULT_SENDER`
*   `ADMIN_EMAILS`

### 5. Desplegar en Cloud Run

Una vez que el conector de VPC esté activo y los Secrets/Variables de GitHub estén configurados, puedes subir tus cambios a la rama `main` o `dev` para activar el workflow de CI/CD, que construirá y desplegará automáticamente la aplicación en Cloud Run.

