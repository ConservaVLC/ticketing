# Sistema de Gestión de Tickets

Este proyecto es una aplicación web full-stack desarrollada en Flask para la gestión de tickets de soporte o incidencias. Permite a los usuarios crear tickets, a los supervisores asignarlos y a los operadores resolverlos, manteniendo un historial completo de cada acción.

## Características Principales

- **Autenticación y Seguridad Avanzada:** Sistema de inicio de sesión robusto con múltiples capas de seguridad:
    - **Control de Acceso Basado en Roles (RBAC):** Permisos estrictos para Clientes, Operadores, Supervisores y Administradores.
    - **Autenticación de Dos Factores (2FA):** Verificación por correo electrónico como segundo paso obligatorio para iniciar sesión.
    - **Expiración de Contraseña:** Política de seguridad que requiere el cambio de contraseña cada 45 días.
    - **Límite de Tasa (Rate Limiting):** Protección contra ataques de fuerza bruta en la pantalla de login.
- **Gestión de Tickets:** Flujo de trabajo completo desde la creación hasta el cierre del ticket, pasando por estados como "Pendiente", "En Progreso", "Completado", "Rechazado" y "Cerrado".
- **Historial de Cambios:** Cada ticket registra un historial detallado de todas las modificaciones, incluyendo cambios de estado, asignaciones y notas, indicando qué usuario realizó el cambio y cuándo.
- **Notificaciones por Correo:** Envío automático de correos electrónicos para notificar eventos clave (creación, asignación, actualización, etc.).
- **Filtro y Exportación:** Los supervisores y administradores pueden filtrar la lista de tickets por múltiples criterios y exportar los resultados a un archivo Excel (.xlsx).
- **Contenerización:** El proyecto está completamente configurado para ser desplegado fácilmente usando Docker y Docker Compose.

## Stack Tecnológico

- **Backend:** Python, Flask
- **Base de Datos:** MongoDB (con Flask-PyMongo)
- **Frontend:** HTML, CSS, JavaScript, Jinja2 (motor de plantillas de Flask)
- **Contenerización:** Docker, Docker Compose
- **Calidad y Testing:**
    - `pytest`: Framework para pruebas unitarias y de integración.
    - `ruff`: Linter y formateador de código para garantizar un estilo consistente.
- **Librerías Python Clave:**
    - `Flask-Login`: Manejo de sesiones de usuario.
    - `Flask-WTF`: Creación y validación de formularios (incluye protección CSRF).
    - `Flask-PyMongo`: Interacción con la base de datos MongoDB.
    - `Flask-Mail`: Envío de correos electrónicos.
    - `Flask-Limiter`: Límite de peticiones (Rate Limiting) para proteger endpoints.
    - `werkzeug.security`: Hashing y verificación de contraseñas.
    - `itsdangerous`: Generación de tokens seguros para reseteo de contraseña.
    - `openpyxl`: Generación de reportes en formato `.xlsx`.

---

## Despliegue y Ejecución

### Despliegue en Producción (CI/CD con GitHub Actions)

El despliegue en el entorno de producción (Google Cloud Run) está **completamente automatizado** a través de un pipeline de Integración y Despliegue Continuo (CI/CD) utilizando GitHub Actions.

- **Activación:** El pipeline se ejecuta automáticamente con cada `push` a las ramas `main` y `dev`.
- **Proceso:**
    1.  Verificación de calidad de código con `ruff`.
    2.  Ejecución de la suite de tests con `pytest`.
    3.  Construcción y publicación de la imagen Docker en Artifact Registry.
    4.  Despliegue de la nueva versión en Google Cloud Run.

La configuración detallada del pipeline se encuentra en `.github/workflows/main.yml`.

Para la configuración inicial del entorno de GCP desde cero (creación de proyecto, APIs, service accounts, redes, etc.), consulta la guía detallada:

- **[GCP_configuration.md](GCP_configuration.md):** Contiene el paso a paso completo para preparar la infraestructura en Google Cloud antes del primer despliegue.

### Entorno de Desarrollo Local

A continuación se describen los métodos para levantar un entorno de desarrollo local.

**Opción 1: Usando Docker (Recomendado)**

Este es el método más sencillo para replicar el entorno de producción localmente.

- **Requisitos:** Docker, Docker Compose.
- **Pasos:**
    1.  Clona el repositorio: `git clone <URL-DEL-REPOSITORIO> && cd ticketing`
    2.  Construye y ejecuta los contenedores: `docker-compose up --build`

La aplicación estará disponible en `http://localhost:5000`. La base de datos se inicializa automáticamente gracias al comando `flask init-db-data` en el `docker-compose.yml`.

**Opción 2: Ejecución Nativa (Sin Docker)**

- **Requisitos:** Python 3.8+, MongoDB local.
- **Pasos:**
    1.  Crea un entorno virtual y activa: `python -m venv venv && source venv/bin/activate` (o `venv\Scripts\activate` en Windows).
    2.  Instala las dependencias: `pip install -r requirements.txt`.
    3.  Configura tus variables de entorno en un archivo `.env` (ver ejemplo en la sección de configuración).
    4.  Inicializa la base de datos: `flask init-db-data`.
    5.  Ejecuta la aplicación: `flask run`.

## Ejecución de Pruebas

Para ejecutar el conjunto de pruebas unitarias, asegúrate de tener las dependencias de desarrollo instaladas y utiliza `pytest`:
```bash
pytest
```

## Guía para Desarrolladores

Este `README.md` proporciona una visión general del proyecto. Sin embargo, para contribuir al código, es **mandatorio** consultar el siguiente documento:

- **[AGENTS.md](AGENTS.md):** Contiene las directrices técnicas, patrones de arquitectura, flujos de trabajo detallados (como 2FA y RBAC), y las reglas de calidad y seguridad que todo desarrollador debe seguir.

Este documento es la fuente de verdad para la arquitectura y las convenciones del proyecto.

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

