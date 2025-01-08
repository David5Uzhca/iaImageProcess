from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from tensorflow.keras.models import load_model
import joblib
from PIL import Image
import numpy as np
from database import get_db_connection, initialize_database
import datetime

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Modelos
model = load_model('models/nnModelPrime.h5')
mlb = joblib.load('models/mlb_model.pkl')

IMAGE_SIZE = (128, 128)

@app.route('/')
def index():
    return "Bienvenido a la API de procesamiento de imágenes"

def predict_image(image_path):
    # prepocesamiento
    image = Image.open(image_path).convert('RGB').resize(IMAGE_SIZE)
    image_array = np.expand_dims(np.array(image) / 255.0, axis=0)

    # predicción
    prediction = model.predict(image_array)
    predicted_labels = mlb.inverse_transform(prediction.round())
    
    # Asegúrate de que las etiquetas sean una lista de strings
    return [str(label) for label in predicted_labels[0]]  # Convertir a lista de strings

# Ruta para subir imágenes
@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Predecir etiquetas
        labels = predict_image(file_path)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO images (file_path, labels, upload_time) VALUES (%s, %s, CURRENT_TIMESTAMP) RETURNING id;",
            (file_path, labels)
        )
        image_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()

        # Obtener la fecha de subida en formato ISO
        upload_time = datetime.datetime.now().isoformat()

        return jsonify({"id": image_id, "file_path": file_path, "labels": labels, "upload_time": upload_time})

# Ruta para listar imágenes y etiquetas
@app.route('/images', methods=['GET'])
def list_images():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, file_path, labels, upload_time FROM images;")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify([
        {
            "id": row[0],
            "file_path": row[1],
            "labels": row[2],
            "upload_time": row[3].isoformat()
        } for row in rows
    ])

# Ruta para servir archivos estáticos
@app.route('/uploads/<path:filename>', methods=['GET'])
def serve_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    initialize_database()
    app.run(host='0.0.0.0', port=5000)