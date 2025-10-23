# Guía para Agentes de IA

Este documento contiene directrices técnicas para la colaboración en este proyecto de gestión de tickets.

## 1. Perfil del Proyecto

*   **Tipo de Aplicación:** Aplicación Web (Full-Stack)
*   **Dominio Principal:** Gestión de Tickets / Incidencias
*   **Funcionalidades Clave:**
    *   Autenticación de usuarios (basada en sesión) con 2FA.
    *   Control de Acceso Basado en Roles (RBAC) para Clientes, Operadores, Supervisores y Administradores.
    *   Creación, asignación, resolución y cierre de tickets.
    *   Historial detallado de cambios por ticket.
    *   Notificaciones automáticas por correo electrónico.
    *   Filtrado y exportación de tickets a Excel.
    *   **Seguridad Reforzada:** Autenticación de Dos Factores (2FA), Expiración de Contraseña (45 días), Política de Contraseña Robusta, Límite de Tasa (Rate Limiting) en el login.
*   **Objetivo del Agente:** Asistir en el desarrollo, la corrección de errores y el refuerzo de la seguridad, adhiriéndose estrictamente a los patrones y tecnologías existentes.

## 2. Stack Tecnológico

El agente debe adherirse estrictamente a las tecnologías y librerías ya presentes en el proyecto.

*   **Backend:** Python, Flask
*   **Base de Datos:** MongoDB (interacción a través de `Flask-PyMongo`)
*   **Frontend:** HTML, CSS, JavaScript, Jinja2 (motor de plantillas de Flask)
*   **Contenerización:** Docker, Docker Compose
*   **Librerías Python Clave:**
    *   `Flask-Login`: Manejo de sesiones de usuario.
    *   `Flask-WTF`: Creación y validación de formularios, protección CSRF.
    *   `Flask-PyMongo`: Interacción con la base de datos MongoDB.
    *   `Flask-Mail`: Envío de correos electrónicos.
    *   `Flask-Limiter`: Límite de peticiones (Rate Limiting).
    *   `openpyxl`: Generación de reportes en formato `.xlsx`.
    *   `itsdangerous`: Generación de tokens (para restablecimiento de contraseña).
    *   `werkzeug.security`: Hashing de contraseñas.
    *   `pytest`: Testing.
    *   `ruff`: Linter y formateador de código.

**Directiva para el Agente:** Antes de proponer o añadir una nueva dependencia, verifica si una librería existente ya puede realizar la tarea. Para una lista exhaustiva de las dependencias y sus versiones, consulta `requirements.txt`.

## 3. Infraestructura y Despliegue

Esta sección describe el entorno de producción y el ciclo de vida del despliegue.

*   **Control de Versiones:** El código fuente está gestionado con `git` y alojado en GitHub.
*   **Integración y Despliegue Continuo (CI/CD):**
    *   **Herramienta:** Se utiliza **GitHub Actions**. La configuración se encuentra en `.github/workflows/`.
    *   **Flujo:** El pipeline se activa con cada `push` a las ramas `main` y `dev`. Realiza tareas como verificación de código, ejecución de tests, construcción y publicación de imagen Docker, y despliegue en Google Cloud Run.
*   **Plataforma de Despliegue:** La aplicación se ejecuta como un contenedor en **Google Cloud Run**.
*   **Base de Datos (Producción):** La base de datos de producción es una instancia de **MongoDB Atlas**.
*   **Conectividad a DB:** Se utiliza una red VPC dedicada con Cloud NAT y un conector de acceso a VPC (Serverless VPC Access Connector) para una conexión segura y estática a MongoDB Atlas.

**Directiva para el Agente:** No modifiques los archivos del workflow de CI/CD (`.github/workflows/*.yml`) sin una solicitud explícita. Ten en cuenta que cualquier cambio en las dependencias o en la configuración debe ser compatible con un entorno contenerizado (Docker).

## 4. Estructura del Proyecto

El código está organizado en módulos utilizando Blueprints de Flask para separar las distintas áreas de la aplicación.

*   `run.py`: Punto de entrada principal para ejecutar la aplicación Flask.
*   `config.py`: Define las clases de configuración para los diferentes entornos (producción, desarrollo, testing).
*   `app/`: Directorio raíz que contiene toda la lógica de la aplicación.
    *   `__init__.py`: Contiene la función de fábrica `create_app`, donde se inicializan las extensiones (BD, Login, etc.) y se registran los Blueprints.
    *   `templates/`: Plantillas HTML base y de errores (`404.html`, `500.html`, etc.).
    *   `static/`: Archivos estáticos como CSS, JavaScript e imágenes.
    *   `commands.py`: Define comandos de CLI personalizados para Flask (ej: `flask init-db-data`).
    *   `auth/`, `main/`, `client/`, `operator/`, `admin/`, `supervisor/`: Cada uno de estos directorios es un **Blueprint** que encapsula una funcionalidad específica. Contienen sus propias rutas (`routes.py`), formularios (`forms.py`) y modelos (`models.py`) si es necesario.
*   `test/`: Contiene todos los tests automatizados.
    *   `conftest.py`: Archivo de configuración de `pytest` que define fixtures globales para los tests (ej: `app`, `client`, `db`).
*   `requirements.txt`: Lista de dependencias de Python para producción.
*   `ruff.toml`: Archivo de configuración para el linter y formateador `Ruff`.
*   `.github/workflows/`: Define los pipelines de CI/CD con GitHub Actions.

## 5. Patrones de Arquitectura Clave

Para mantener la consistencia del código, es fundamental que cualquier modificación o nueva funcionalidad respete los siguientes patrones de diseño establecidos en el proyecto.

### 5.1. Control de Acceso Basado en Roles (RBAC)

*   **Descripción:** El acceso a las funcionalidades está estrictamente controlado por roles (`admin`, `supervisor`, `operador`, `cliente`).
*   **Ubicación:** La lógica principal se encuentra en `app/auth/models.py` (clase `Persona` con el atributo `role`) y `app/auth/decorators.py` (decorador `role_required` y sus variantes específicas).
*   **Directiva para el Agente:** Al implementar nuevas rutas o funcionalidades, utiliza los decoradores de rol (`@login_required`, `@admin_required`, `@client_required`, etc.) para asegurar que solo los usuarios autorizados puedan acceder.

### 5.2. Flujo de Autenticación de Dos Factores (2FA)

*   **Descripción:** Para reforzar la seguridad, el inicio de sesión no es inmediato tras validar la contraseña. Se ha implementado un segundo factor de autenticación por correo electrónico.
*   **Flujo:**
    1.  El usuario introduce credenciales válidas (usuario/contraseña) en la ruta `auth.login`.
    2.  El sistema genera un código numérico de 6 dígitos, lo almacena en el documento del usuario en la base de datos junto con una fecha de expiración (10 minutos) y lo envía al correo del usuario.
    3.  Se redirige al usuario a una página de verificación (`auth.verify_2fa`).
    4.  El usuario introduce el código recibido. El sistema valida que el código sea correcto y no haya expirado.
    5.  Si la validación es exitosa, se completa el inicio de sesión con `Flask-Login` y se limpia el código de la base de datos.
*   **Ubicación:** La lógica se reparte entre `app/auth/routes.py` (rutas `login` y `verify_2fa`), `app/auth/models.py` (métodos `generate_2fa_code` y `check_2fa_code` en la clase `Persona`) y `app/email.py`.
*   **Directiva para el Agente:** Cualquier modificación en el flujo de login debe tener en cuenta este paso intermedio de 2FA. Los tests que requieran un usuario logueado deben simular este flujo completo.

### 5.3. Expiración Forzada de Contraseña

*   **Descripción:** Por motivos de seguridad, se fuerza a los usuarios a cambiar su contraseña cada 45 días.
*   **Flujo:**
    1.  Al iniciar sesión, el decorador `check_password_expiration` verifica la fecha del último cambio de contraseña (`password_changed_at`).
    2.  Si la contraseña ha expirado, se redirige al usuario a la página de cambio de contraseña (`auth.change_password`) con un mensaje de advertencia.
*   **Ubicación:** Implementado en `app/auth/decorators.py` (`check_password_expiration`) y `app/__init__.py` (donde se registra como un `before_request` handler).
*   **Directiva para el Agente:** Ten en cuenta esta política al gestionar usuarios o al implementar funcionalidades relacionadas con la autenticación.

### 5.4. Patrón de Fábrica de Aplicación (`create_app`)

*   **Descripción:** La aplicación se instancia a través de la función `create_app` en `app/__init__.py`. Esto facilita la creación de múltiples instancias de la app con diferentes configuraciones (esencial para los tests).
*   **Directiva para el Agente:** No inicialices extensiones de Flask de forma global. Cualquier nueva extensión o Blueprint debe ser registrado dentro de la función `create_app` para garantizar que se cargue correctamente en todos los entornos.

## 6. Directivas Generales para el Agente

*   **Idioma:** Todo el código nuevo, comentarios y mensajes de commit deben estar en español para mantener la consistencia.
*   **Calidad de Código:** Antes de finalizar cualquier tarea, es obligatorio ejecutar `ruff check .` y `ruff format .` para asegurar que el código cumple con los estándares del proyecto.
*   **Testing:** Es un requisito indispensable. Por cada nueva funcionalidad que se cree, se deben crear los tests correspondientes. Por cada modificación a una funcionalidad existente, se deben revisar y actualizar los tests existentes para que reflejen los cambios.
*   **Seguridad:** Es indispensable que cualquier nueva funcionalidad o modificación sea revisada para cumplir con los 10 mandatos de OWASP. No introduzcas nuevas dependencias sin verificar su seguridad. No guardes secretos (claves, contraseñas) directamente en el código; utiliza siempre variables de entorno.
*   **Commits:** Escribe mensajes de commit claros y descriptivos. Si es posible, sigue un formato convencional (ej: `feat(auth): ...`, `fix(leaves): ...`).
*   **Documentación:** Tras cualquier cambio funcional o de dependencias, es **mandatorio** revisar y actualizar `README.md`, `AGENTS.md` y `CONTRIBUTING.md` para que reflejen el estado actual del proyecto.