"""
PostgreSQL connection helper.
Provides get_db() for use by services.
"""

import os
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

# Load .env variables from the project root
load_dotenv()

# Get the database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Please set the environment variable.")

def get_db():
    """
    Returns a new psycopg2 connection with dictionary-based row access.

    This utility ensures consistent connection parameters across services.
    
    Usage:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(...)
    
    Returns:
        psycopg2.extensions.connection: A connection object with DictCursor factory.
    
    Raises:
        psycopg2.Error: If connection fails.
    """
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(DATABASE_URL)
        
        # Set the cursor factory to return rows as dictionaries 
        # (e.g., {"user_id": 1, "email": "..."})
        conn.cursor_factory = DictCursor
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        # Re-raise the exception so the caller knows the connection failed
        raise
