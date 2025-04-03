# utils/database.py
import sqlite3
from sqlite3 import Error

def create_connection():
    """Create a database connection to SQLite database"""
    conn = None
    try:
        conn = sqlite3.connect('data/issues.db')  # This will create the file if not exists
        print(f"Connected to SQLite version {sqlite3.version}")
        return conn
    except Error as e:
        print(e)
    
def initialize_database():
    schema = """
    -- Your complete schema from previous message here --
    """
    
    conn = create_connection()
    try:
        c = conn.cursor()
        c.executescript(schema)
        conn.commit()
        print("Database initialized successfully")
    except Error as e:
        print(f"Error initializing database: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    initialize_database()