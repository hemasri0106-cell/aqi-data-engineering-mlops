import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
db_host = os.environ.get('DB_HOST', 'localhost')
db_port = os.environ.get('DB_PORT', '5432')
db_name = os.environ.get('DB_NAME', 'aqi_db')
db_user = os.environ.get('DB_USER', 'postgres')
db_password = os.environ.get('DB_PASSWORD', 'postgres')

try:
    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        database=db_name,
        user=db_user,
        password=db_password,
        connect_timeout=3
    )
    print("SUCCESS: PostgreSQL connection established!")
    conn.close()
except Exception as e:
    print(f"FAILED: {e}")
