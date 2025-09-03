# === FASE DE CONSTRUCCIÓN (BUILDER STAGE) ===
# Se utiliza una imagen de Python completa para instalar dependencias.
FROM python:3.10.11-slim-buster as builder

# Establece el directorio de trabajo para la fase de construcción.
WORKDIR /app

# Copia los archivos de requisitos.txt para aprovechar la caché de Docker.
COPY requirements.txt .

# Instala las dependencias de Python.
# pip freeze > requirements.txt crea un archivo que contiene todas las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# === FASE DE PRODUCCIÓN (PRODUCTION STAGE) ===
# Usamos una imagen de Python mucho más ligera, sin las herramientas de construcción.
FROM python:3.10.11-slim-buster

# Establece el directorio de trabajo para la aplicación.
WORKDIR /app

# Copia los paquetes de Python instalados desde la fase de construcción.
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copia el resto del código de la aplicación.
COPY . .

# Expone el puerto 5000.
EXPOSE 5000

# Variables de entorno para producción.
# FLASK_APP es la única variable esencial aquí.
# Las credenciales de la BBDD se pasarán a través de la consola de Cloud Run.
ENV FLASK_APP=app
ENV PYTHONUNBUFFERED=1

# Comando de inicio para Gunicorn.
# Este comando ejecuta las migraciones de la base de datos (flask db upgrade)
# y luego inicia el servidor Gunicorn en un solo comando.
CMD ["/bin/bash", "-c", "until flask db upgrade; do echo 'Waiting for database...'; sleep 5; done && flask init-db-data && gunicorn --workers=3 --threads=2 --bind 0.0.0.0:5000 run:app"]
