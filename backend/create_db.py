import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

try:
    # Connect to the default 'postgres' database to issue the CREATE DATABASE command
    conn = psycopg2.connect(
        user="postgres",
        password="password",
        host="localhost",
        dbname="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # Check if database exists first
    cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = 'claimsense'")
    exists = cursor.fetchone()
    if not exists:
        cursor.execute("CREATE DATABASE claimsense;")
        print("Database 'claimsense' created successfully.")
    else:
        print("Database 'claimsense' already exists.")
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals() and conn:
        cursor.close()
        conn.close()
