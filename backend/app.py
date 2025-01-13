from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from PIL import Image
import torch
from database import get_db_connection, initialize_database
import datetime
import logging
from werkzeug.utils import secure_filename
import json

# Configuración
UPLOAD_FOLDER = "uploads"
MODEL_PATH = os.path.join("models", "yolov5s.pt")
LOGGING_LEVEL = logging.INFO

# Crear carpetas necesarias
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Inicialización de Flask
app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configuración del registro de logs
logging.basicConfig(level=LOGGING_LEVEL)
logger = logging.getLogger(__name__)

# Cargar el modelo YOLOv5
try:
    model = torch.hub.load('ultralytics/yolov5', 'custom', path=MODEL_PATH)
    logger.info("Modelo YOLOv5 cargado exitosamente.")
except Exception as e:
    logger.error(f"Error al cargar el modelo YOLOv5: {e}")
    raise

@app.route('/')
def index():
    return "Bienvenido a la API de procesamiento de imágenes con YOLOv5"

# Método para predecir etiquetas usando YOLOv5
def predict_image(image_path):
    try:
        # Abrir la imagen y hacer predicción
        results = model(image_path)

        # Extraer etiquetas y confidencias
        predictions = results.pandas().xyxy[0]
        predictions = predictions[['name', 'confidence']]
        predictions['confidence'] = (predictions['confidence'] * 100).round(2)

        # Agrupar por etiquetas únicas con máxima confianza
        unique_labels = predictions.groupby('name', as_index=False).max()
        return unique_labels.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error al predecir la imagen: {e}")
        raise

# Ruta para subir imágenes
@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        conn = get_db_connection()  # Obtener la conexión a la base de datos
        cursor = conn.cursor()  # Crear un cursor para ejecutar consultas

        # Guardar el archivo subido
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        # Guardar en el servidor
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        # Realizar predicciones con YOLOv5
        results = model(file_path)
        predictions = results.pandas().xyxy[0][['confidence', 'name']].to_dict(orient='records')

        # Convertir a JSON
        predictions_json = json.dumps(predictions)  # Convertir a cadena JSON

        # Guardar en la base de datos
        query = """
        INSERT INTO images (file_path, labels, upload_time)
        VALUES (%s, %s::JSONB, CURRENT_TIMESTAMP)
        RETURNING id;
        """
        cursor.execute(query, (file_path, predictions_json))
        conn.commit()

        return jsonify({'message': 'Image uploaded successfully', 'predictions': predictions}), 200

    except Exception as e:
        print(f"Error al procesar la solicitud de subida: {e}")
        return jsonify({'error': 'Error uploading image. Try again.'}), 500
    finally:
        cursor.close()  # Asegurarse de cerrar el cursor
        conn.close()  # Asegurarse de cerrar la conexión

# Ruta para listar imágenes y etiquetas
@app.route('/images', methods=['GET'])
def list_images():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, file_path, labels, upload_time FROM images;")
            rows = cursor.fetchall()

        return jsonify([
            {
                "id": row[0],
                "file_path": row[1],
                "labels": row[2],
                "upload_time": row[3].isoformat()
            } for row in rows
        ])
    except Exception as e:
        logger.error(f"Error al listar imágenes: {e}")
        return jsonify({"error": str(e)}), 500

# Ruta para servir archivos estáticos
@app.route('/uploads/<path:filename>', methods=['GET'])
def serve_uploaded_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        logger.error(f"Error al servir archivo {filename}: {e}")
        return jsonify({"error": str(e)}), 404

if __name__ == '__main__':
    try:
        initialize_database()
        logger.info("Base de datos inicializada correctamente.")
        app.run(host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Error al iniciar la aplicación: {e}")
