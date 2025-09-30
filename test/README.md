# Pruebas del Proyecto de Ticketing

Este directorio contiene las pruebas automatizadas para la aplicación de ticketing. El objetivo es asegurar la calidad, el correcto funcionamiento de los componentes y prevenir regresiones.

## Requisitos

- **Python y Pip:** Para ejecutar el entorno y las dependencias.
- **Dependencias de Python:** Todas las dependencias de desarrollo deben estar instaladas.

**No se requiere una instancia de MongoDB en ejecución.** Las pruebas utilizan `mongomock` para simular la base de datos en memoria.

## Instalación

Para instalar todas las dependencias necesarias, ejecuta el siguiente comando desde el directorio raíz del proyecto:

```bash
pip install -r requirements.txt
```

## Ejecución de Pruebas

Este proyecto utiliza `pytest` como framework de pruebas.

### Ejecutar toda la suite de pruebas

Para ejecutar todos los tests del proyecto, simplemente corre el siguiente comando en el directorio raíz:

```bash
pytest
```

### Opciones útiles

-   **Modo Verboso (`-v`):** Para obtener un desglose detallado de cada test ejecutado.
-   **Captura de Salida (`-s`):** Para mostrar los `print()` y logs en la consola durante la ejecución.

```bash
pytest -v -s
```

## Configuración de Pruebas (`conftest.py`)

El archivo `conftest.py` es una pieza central de la configuración de `pytest`. Proporciona *fixtures* que están disponibles para todos los tests:

-   **`app`**: Una instancia de la aplicación Flask configurada para el entorno de `testing`.
-   **`client`**: Un cliente de pruebas de Flask para realizar solicitudes HTTP.
-   **`db`**: Una fixture que proporciona una **base de datos simulada (`mongomock`)** para cada función de prueba, garantizando el aislamiento de las pruebas.
-   **Fixtures de autenticación**: Clientes pre-autenticados con roles como `cliente` (`logged_in_client`) y `operador` (`logged_in_operator_client`).

---

## Resumen de Pruebas Unitarias

### Módulo Testeado: `app.client.routes`

#### Ruta: `/create_ticket`

**Casos de Prueba Cubiertos:**

-   **Acceso a la página (GET):**
    -   Un usuario `cliente` puede acceder al formulario de creación.
    -   Un usuario no autenticado es redirigido al login.
    -   Un usuario con otro rol (ej. `operador`) recibe un error 403 (Prohibido).

-   **Envío del formulario (POST) - Éxito:**
    -   Se crea un nuevo ticket en la base de datos con los datos correctos.
    -   El ticket se asigna a un supervisor según las reglas.
    -   Se envía una notificación por correo al supervisor.
    -   Se muestra un mensaje flash de éxito.

-   **Envío del formulario (POST) - Errores:**
    -   Si el formulario tiene datos inválidos (ej. título vacío), se muestran los errores de validación.
    -   Si el estado "Pendiente" no existe en la BBDD, se muestra un error crítico.
    -   En casos de error, no se crea ningún ticket.

#### Ruta: `/client_tickets`

**Casos de Prueba Cubiertos:**

-   **Acceso a la página (GET):**
    -   Un usuario `cliente` puede acceder a su listado de tickets.
    -   Un usuario no autenticado es redirigido al login.
    -   Un usuario con otro rol (ej. `operador`) recibe un error 403 (Prohibido).

-   **Contenido de la página:**
    -   Un cliente solo ve los tickets creados por él.
    -   Se muestran los detalles clave del ticket (título, estado, categoría).
    -   Se muestra un mensaje apropiado si el cliente no tiene ningún ticket creado.
