"""
Script to initialize the PostgreSQL database schema using the raw SQL file.
This is the most reliable method when relying on a fixed schema definition.
"""
import os
import sys

# Ensure the project root is in the path for modular imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Assuming db_connection.py is in the same directory and exports get_db()
try:
    from backend.database.db_connection import get_db
except ImportError:
    print("Error: Could not import get_db(). Make sure backend/database/db_connection.py exists.")
    sys.exit(1)

SCHEMA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), 'schema.sql'))

def initialize_database():
    print(f"--- Database Schema Initialization ---")
    print(f"Reading schema from: {SCHEMA_FILE}")

    try:
        # 1. Read the SQL file content
        with open(SCHEMA_FILE, 'r') as f:
            # PostgreSQL can execute multiple statements separated by ';'
            sql_script = f.read()

    except FileNotFoundError:
        print(f"Error: Schema file not found at {SCHEMA_FILE}")
        sys.exit(1)

    conn = None
    cur = None
    try:
        # 2. Connect to the database
        conn = get_db()
        cur = conn.cursor()
        print("Successfully connected to the PostgreSQL database.")

        # 3. Execute the full SQL script
        # The script contains DROP and CREATE TABLE statements
        # We need to execute the full script as a single string
        cur.execute(sql_script)
        
        # 4. Commit the changes
        conn.commit()
        print("SUCCESS: All tables defined in schema.sql have been created (or dropped and recreated).")

    except Exception as e:
        print("\nFATAL ERROR during database initialization:")
        print(f"Error: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
        
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    initialize_database()
