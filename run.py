# run.py

from app import create_app # Importa tu función de fábrica
import os

# ----------------------------------------------------

# Carga las variables de entorno si usas un archivo .env
# from dotenv import load_dotenv
# load_dotenv()

# Lee la configuración del entorno o usa 'development' por defecto
config_name = os.environ.get('FLASK_CONFIG', 'development')
app = create_app(config_name)

# ----------------------------------------------------------------

if __name__ == '__main__':
    # Puedes obtener el puerto de una variable de entorno o usar un valor por defecto
    port = int(os.environ.get('PORT', 4000))
    app.run(debug=True, port=port)