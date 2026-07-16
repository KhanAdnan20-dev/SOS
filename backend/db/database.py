"""
Database connection pool and helper utilities supporting both SQLite and MySQL.
"""

import os
import sqlite3
from config import DB_TYPE, SQLITE_DB_PATH, DB_CONFIG

# Optional MySQL import if DB_TYPE is mysql
_pool = None
if DB_TYPE == "mysql":
    try:
        import mysql.connector
        from mysql.connector import pooling
        _pool = pooling.MySQLConnectionPool(
            pool_name="sos_pool",
            pool_size=5,
            pool_reset_session=True,
            **DB_CONFIG,
        )
    except Exception as e:
        print(f"[database] [WARN] Could not initialize MySQL pool ({e}). Falling back to sqlite.")
        DB_TYPE = "sqlite"


def _init_sqlite_schema(conn: sqlite3.Connection):
    """Ensure SQLite tables exist and seed initial data if empty."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ambulances (
            ambulance_id TEXT PRIMARY KEY,
            vehicle_number TEXT,
            amb_latitude REAL,
            amb_longitude REAL,
            status TEXT,
            tier TEXT
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hospitals (
            hospital_id TEXT PRIMARY KEY,
            name TEXT,
            latitude REAL,
            longitude REAL,
            specialty_tags TEXT,
            icu_beds_available INTEGER,
            ot_status TEXT,
            ot_clear_time_mins INTEGER
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            incident_id TEXT PRIMARY KEY,
            patient_name TEXT,
            raw_transcript TEXT,
            ai_urgency_tier TEXT,
            ai_medical_tag TEXT,
            user_latitude REAL,
            user_longitude REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dispatches (
            dispatch_id TEXT PRIMARY KEY,
            incident_id TEXT,
            ambulance_id TEXT,
            hospital_id TEXT,
            estimated_arrival_mins INTEGER,
            dispatch_status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()

    # Check if we need to seed initial data or upgrade to 52 hospitals
    cursor.execute("SELECT COUNT(*) as cnt FROM hospitals")
    row = cursor.fetchone()
    if not row or row[0] < 50:
        from seed_data import seed_sqlite_direct
        seed_sqlite_direct(conn)


def get_connection():
    """Get a connection to either SQLite or MySQL."""
    global DB_TYPE
    if DB_TYPE == "sqlite":
        os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
        conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
        _init_sqlite_schema(conn)
        return conn
    else:
        return _pool.get_connection()


def fetch_all(query: str, params: tuple = ()):
    """Execute a SELECT and return all rows as list of dicts."""
    conn = get_connection()
    try:
        if DB_TYPE == "sqlite":
            sqlite_query = query.replace("%s", "?")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sqlite_query, params)
            rows = [dict(row) for row in cursor.fetchall()]
            return rows
        else:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return rows
    finally:
        cursor.close()
        conn.close()


def fetch_one(query: str, params: tuple = ()):
    """Execute a SELECT and return a single row as dict (or None)."""
    conn = get_connection()
    try:
        if DB_TYPE == "sqlite":
            sqlite_query = query.replace("%s", "?")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sqlite_query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        else:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            row = cursor.fetchone()
            return row
    finally:
        cursor.close()
        conn.close()


def execute(query: str, params: tuple = ()):
    """Execute an INSERT / UPDATE / DELETE and commit."""
    conn = get_connection()
    try:
        if DB_TYPE == "sqlite":
            sqlite_query = query.replace("%s", "?")
            cursor = conn.cursor()
            cursor.execute(sqlite_query, params)
            conn.commit()
            return cursor.lastrowid
        else:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()
