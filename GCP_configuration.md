# Guía de Despliegue en Google Cloud Platform (GCP)

Esta guía detalla todos los pasos necesarios para configurar un entorno en GCP desde cero y desplegar la aplicación de ticketing.

## 1. Crear un Nuevo Proyecto en GCP

1.  **Ir a la consola de GCP:** Accede a [https://console.cloud.google.com/](https://console.cloud.google.com/).
2.  **Crear un proyecto:**
    *   En la parte superior, haz clic en el selector de proyectos (al lado del logo de Google Cloud).
    *   Haz clic en `PROYECTO NUEVO`.
    *   Asigna un nombre al proyecto (ej. `ticketing-app-project`) y selecciona una organización si es necesario.
    *   Haz clic en `CREAR`.
3.  **Configurar la facturación:** Asegúrate de que el nuevo proyecto esté vinculado a una cuenta de facturación activa.

## 2. Habilitar las APIs Necesarias

Para que los servicios funcionen, debes habilitar las siguientes APIs en tu proyecto:

1.  Ve a `APIs y servicios > Biblioteca`.
2.  Busca y habilita las siguientes APIs, una por una:
    *   **Cloud Run API:** Para desplegar la aplicación.
    *   **Artifact Registry API:** Para almacenar las imágenes de Docker.
    *   **Cloud Build API:** Para construir las imágenes de Docker (usado por Artifact Registry).
    *   **IAM Service Account Credentials API:** Para la gestión de credenciales.
    *   **Compute Engine API:** Necesaria para la configuración de la red VPC.
    *   **Serverless VPC Access API:** Para crear el conector VPC.

## 3. Crear una Cuenta de Servicio (Service Account)

Esta cuenta será utilizada por GitHub Actions para autenticarse y desplegar en tu nombre.

1.  Ve a `IAM y administración > Cuentas de servicio`.
2.  Haz clic en `CREAR CUENTA DE SERVICIO`.
3.  **Nombre de la cuenta:** `github-actions-deployer` (o un nombre descriptivo).
4.  **ID de la cuenta de servicio:** Se generará automáticamente.
5.  Haz clic en `CREAR Y CONTINUAR`.

## 4. Asignar Permisos a la Cuenta de Servicio

Ahora, asigna los roles necesarios a la cuenta que acabas de crear:

1.  En la sección `Otorga a esta cuenta de servicio acceso al proyecto`, haz clic en el campo `Selecciona un rol`.
2.  Busca y añade los siguientes roles, uno por uno:
    *   **Cloud Run Admin (`roles/run.admin`):** Permisos completos para desplegar y gestionar la aplicación en Cloud Run.
    *   **Storage Admin (`roles/storage.admin`):** Necesario para que Artifact Registry gestione los buckets de almacenamiento de imágenes.
    *   **Service Account User (`roles/iam.serviceAccountUser`):** Permite a la cuenta de servicio actuar en nombre de otras para el despliegue.
    *   **Compute Network User (`roles/compute.networkUser`):** Requerido para que Cloud Run use el conector VPC.
3.  Haz clic en `CONTINUAR` y luego en `LISTO`.

## 5. Generar una Clave para la Cuenta de Servicio

Esta clave es un archivo JSON que se usará como secreto en GitHub.

1.  En la lista de cuentas de servicio, busca la que creaste (`github-actions-deployer`).
2.  Haz clic en los tres puntos verticales bajo `Acciones` y selecciona `Administrar claves`.
3.  Haz clic en `AGREGAR CLAVE > Crear clave nueva`.
4.  Selecciona `JSON` como tipo de clave y haz clic en `CREAR`.
5.  Se descargará un archivo JSON. **Guárdalo en un lugar seguro, ya que no podrás volver a descargarlo.** El contenido de este archivo se usará en un secreto de GitHub.

## 6. Configurar la Red y el Acceso a Internet

Estos pasos son cruciales para que Cloud Run tenga una IP de salida estática y pueda conectarse a MongoDB Atlas.

### 6.1. Crear una Red VPC

1.  Ve a `Red de VPC > Redes de VPC`.
2.  Haz clic en `CREAR RED DE VPC`.
3.  **Nombre:** `mongo-atlas-vpc`.
4.  **Modo de creación de subred:** `Personalizado`.
5.  **Nueva subred:**
    *   **Nombre:** `mongo-atlas-subnet`.
    *   **Región:** `us-central1` (o la misma región donde desplegarás Cloud Run).
    *   **Rango de direcciones IP:** `10.8.0.0/28`.
6.  Haz clic en `LISTO` y luego en `CREAR`.

### 6.2. Crear un Conector de Acceso a VPC sin Servidor

1.  Ve a `Red de VPC > Acceso a VPC sin servidor`.
2.  Haz clic en `CREAR CONECTOR`.
3.  **Nombre:** `mongo-cloud-run-connector`.
4.  **Región:** `us-central1` (la misma que tu subred).
5.  **Red:** Selecciona la red que creaste (`mongo-atlas-vpc`).
6.  **Subred:** Selecciona la subred que creaste (`mongo-atlas-subnet`).
7.  Haz clic en `CREAR`. La creación puede tardar unos minutos.

### 6.3. Configurar Cloud NAT y Reservar la IP Estática

1.  **Ir a Cloud NAT:**
    *   Ve a `Servicios de red > Cloud NAT`.
    *   Haz clic en `CREAR PUERTA DE ENLACE NAT`.
2.  **Configurar la puerta de enlace:**
    *   **Nombre:** `mongo-atlas-nat-gateway`.
    *   **Red VPC:** `mongo-atlas-vpc`.
    *   **Región:** `us-central1`.
    *   **Cloud Router:** Haz clic en `Crear nuevo router`, asígnale un nombre (ej. `mongo-atlas-router`) y haz clic en `CREAR`.
3.  **Asignar y reservar la IP:**
    *   En la sección `Asignación de NAT`, selecciona `Manual`.
    *   En `Direcciones IP de NAT`, haz clic en `Crear dirección IP`.
    *   En el modal que aparece, asigna un **nombre** a la nueva IP, por ejemplo: `static-ip-mongo-gcp`.
    *   Haz clic en `RESERVAR`.
4.  **Finalizar:**
    *   Haz clic en `CREAR` en la página principal de Cloud NAT.

## 7. Configurar MongoDB Atlas

1.  **Obtener la IP estática:** Ve a `Red de VPC > Direcciones IP` en GCP y copia la dirección IP externa de `static-ip-mongo-gcp`.
2.  **Añadir IP a la lista de acceso:**
    *   En tu proyecto de MongoDB Atlas, ve a `Network Access`.
    *   Haz clic en `ADD IP ADDRESS`.
    *   Pega la IP estática que copiaste y añade una descripción (ej. `Cloud Run App`).
    *   Haz clic en `CONFIRM`.
3.  **Obtener la cadena de conexión:**
    *   Ve a `Database`, haz clic en `Connect` en tu clúster.
    *   Selecciona `Drivers` y copia la cadena de conexión (Connection String). Asegúrate de reemplazar `<password>` con la contraseña real del usuario de la base de datos.

## 8. Configurar Secretos y Variables en GitHub

En tu repositorio de GitHub, ve a `Settings > Secrets and variables > Actions`.

### 8.1. Secrets

Crea los siguientes `Repository secrets`:

*   `GCP_PROJECT_ID`: El ID de tu proyecto de Google Cloud.
*   `GCP_SA_KEY`: Pega el contenido completo del archivo JSON de la clave de tu cuenta de servicio.
*   `MONGO_URI`: La cadena de conexión de MongoDB Atlas (con la contraseña).
*   `SECRET_KEY`: Una clave secreta segura para Flask.
*   `GCS_BUCKET_NAME`: (Opcional, si tu app lo usa) El nombre de un bucket de Google Cloud Storage.
*   `MAIL_USERNAME`: El usuario de tu servicio de correo.
*   `MAIL_PASSWORD`: La contraseña de tu servicio de correo.
*   `MAIL_DEFAULT_SENDER`: El correo que aparecerá como remitente.
*   `ADMIN_EMAILS`: Correos de los administradores, separados por comas.

### 8.2. Variables

Crea las siguientes `Repository variables`:

*   `MAIL_SERVER`: El host de tu servidor de correo (ej. `smtp.example.com`).
*   `MAIL_PORT`: El puerto del servidor de correo (ej. `587`).
*   `MAIL_USE_TLS`: `True` o `False`, dependiendo de la configuración de tu servidor.

## 9. Desplegar la Aplicación

Una vez que todos los pasos anteriores estén completados, el despliegue se activará automáticamente cada vez que hagas un `push` a las ramas `main` o `dev`. También puedes activarlo manualmente:

1.  Ve a la pestaña `Actions` en tu repositorio de GitHub.
2.  Selecciona el workflow `Deploy MongoDB App to Cloud Run`.
3.  Haz clic en `Run workflow` y selecciona la rama que deseas desplegar.