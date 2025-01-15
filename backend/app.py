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

UPLOAD_FOLDER = "uploads"
MODEL_PATH = os.path.join("models", "yolov5s.pt")
LOGGING_LEVEL = logging.INFO

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

logging.basicConfig(level=LOGGING_LEVEL)
logger = logging.getLogger(__name__)

try:
    model = torch.hub.load('ultralytics/yolov5', 'custom', path=MODEL_PATH)
    logger.info("Modelo YOLOv5 cargado exitosamente.")
except Exception as e:
    logger.error(f"Error al cargar el modelo YOLOv5: {e}")
    raise

@app.route('/')
def index():
    return "Bienvenido a la API de procesamiento de imágenes con YOLOv5"

def predict_image(image_path):
    try:
        results = model(image_path)

        predictions = results.pandas().xyxy[0]
        predictions = predictions[['name', 'confidence']]
        predictions['confidence'] = (predictions['confidence'] * 100).round(2)

        unique_labels = predictions.groupby('name', as_index=False).max()
        return unique_labels.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error al predecir la imagen: {e}")
        raise

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        conn = get_db_connection() 
        cursor = conn.cursor() 

        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        logger.info(f"Archivo guardado en: {file_path}")

        results = model(file_path)
        predictions = results.pandas().xyxy[0][['confidence', 'name']].to_dict(orient='records')

        predictions_json = json.dumps(predictions)

        query = """
        INSERT INTO images (file_path, labels, upload_time)
        VALUES (%s, %s::JSONB, CURRENT_TIMESTAMP)
        RETURNING id;
        """
        cursor.execute(query, (file_path, predictions_json))
        conn.commit()

        return jsonify({'message': 'Image uploaded successfully', 'predictions': predictions}), 200

    except Exception as e:
        logger.error(f"Error al procesar la solicitud de subida: {e}")
        return jsonify({'error': 'Error uploading image. Try again.'}), 500
    finally:
        cursor.close() 
        conn.close() 

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