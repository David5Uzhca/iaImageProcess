import psycopg2

# Configuración de la base de datos
DB_CONFIG = {
    "dbname": "processimage",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": "5432"
}

# Conexión a la base de datos PostgreSQL
def get_db_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except psycopg2.Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        raise

# Crear tabla si no existe
def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id SERIAL PRIMARY KEY,
            file_path TEXT NOT NULL,
            labels TEXT[] NOT NULL
        );
    ''')
    conn.commit()
    cursor.close()
    conn.close()
