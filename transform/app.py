import os
import psycopg2
import time
import socket
from urllib.parse import urlparse

def wait_for_postgres(host, port, timeout=30):
    """Wait for the PostgreSQL database to be ready."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (socket.error, ConnectionRefusedError):
            time.sleep(1)
    raise TimeoutError(f"Cannot connect to PostgreSQL at {host}:{port}")

# Get environment variables
url = os.getenv("POSTGRES_URL")

# Ensure the URL is set
if not url:
    raise ValueError("Missing POSTGRES_URL environment variable")

# Parse URL for connection details
parsed = urlparse(url)
host = parsed.hostname
port = parsed.port or 5432
user = parsed.username
password = parsed.password
dbname = parsed.path.strip("/")

# Initialize conn to None to prevent NameError in the finally block
conn = None

try:
    print(f"Waiting for PostgreSQL at {host}:{port}...")
    wait_for_postgres(host, port)
    print("PostgreSQL is ready.")

    # Connect to the database
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname
    )
    cursor = conn.cursor()
    print("Connected to PostgreSQL successfully.")

    # Create table and hypertable if they don't exist
    print("Creating table and hypertable...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mem (
            time TIMESTAMPTZ NOT NULL,
            host TEXT NOT NULL,
            used_percent DOUBLE PRECISION
        );
    """)
    cursor.execute("SELECT create_hypertable('mem', 'time', if_not_exists => TRUE);")
    conn.commit()
    print("Table and hypertable are ready.")

    # Insert a data point
    used_percent = 23.43
    host_name = "server1"
    
    print("Writing data point...")
    cursor.execute(
        "INSERT INTO mem (time, host, used_percent) VALUES (NOW(), %s, %s);",
        (host_name, used_percent)
    )
    conn.commit()
    print("Data point written successfully.")

    # Query the data
    sql_query = "SELECT time, host, used_percent FROM mem WHERE time >= NOW() - INTERVAL '1 hour' ORDER BY time DESC;"
    print("Querying data with SQL...")
    cursor.execute(sql_query)
    
    # Print results
    for row in cursor.fetchall():
        print(row)
    print("Query finished.")

except psycopg2.OperationalError as e:
    print(f"Error connecting to the database: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    # Close the connection
    if conn:
        conn.close()
        print("Database connection closed.")