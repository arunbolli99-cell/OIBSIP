import sqlite3
import os

DB_NAME = "bmi_tracker.db"

def get_connection():
    """Establish and return an SQLite connection."""
    return sqlite3.connect(DB_NAME)

def init_db():
    """Initialize the database tables and enable foreign key constraints."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Enable foreign keys for cascade deletions
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            age INTEGER,
            gender TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create records table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT NOT NULL,
            weight REAL NOT NULL,
            height REAL NOT NULL,
            bmi REAL NOT NULL,
            category TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

def add_user(name, age=None, gender=None):
    """
    Insert a new user profile.
    Raises ValueError if the username is already taken.
    """
    if not name or not name.strip():
        raise ValueError("User name cannot be empty.")
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, age, gender) VALUES (?, ?, ?)",
            (name.strip(), age, gender)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(f"User with name '{name}' already exists.")
    finally:
        conn.close()

def delete_user(user_id):
    """Delete a user profile and all associated records."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_users():
    """Retrieve all users sorted alphabetically."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, age, gender FROM users ORDER BY name ASC")
    users = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "age": r[2], "gender": r[3]} for r in users]

def add_record(user_id, date, weight, height, bmi, category):
    """Add a new BMI calculation record for a specific user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute(
        "INSERT INTO records (user_id, date, weight, height, bmi, category) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, date, weight, height, bmi, category)
    )
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()
    return record_id

def delete_record(record_id):
    """Delete a specific log entry from the records table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

def get_records(user_id):
    """Retrieve all records for a user, sorted chronologically."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, date, weight, height, bmi, category FROM records WHERE user_id = ? ORDER BY date ASC, id ASC",
        (user_id,)
    )
    records = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "date": r[1], "weight": r[2], "height": r[3], "bmi": r[4], "category": r[5]}
        for r in records
    ]
