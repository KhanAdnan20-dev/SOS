"""
Seed Script — Populates ambulances & hospitals tables with Delhi test data.
──────────────────────────────────────────────────────────────────────────────
Run once:   python seed_data.py
"""

import sqlite3
from config import DB_TYPE, SQLITE_DB_PATH, DB_CONFIG

# ─── Delhi Ambulance Fleet (10 units) ──────────────────────────
AMBULANCES = [
    ("AMB-001", "DL-01-AB-1234", 28.6139, 77.2090, "AVAILABLE", "ALS"),   # Connaught Place
    ("AMB-002", "DL-02-CD-5678", 28.5355, 77.2510, "AVAILABLE", "BLS"),   # Saket
    ("AMB-003", "DL-03-EF-9012", 28.6692, 77.4538, "AVAILABLE", "ALS"),   # Noida Sec 18
    ("AMB-004", "DL-04-GH-3456", 28.7041, 77.1025, "AVAILABLE", "BLS"),   # Rohini
    ("AMB-005", "DL-05-IJ-7890", 28.6315, 77.2167, "AVAILABLE", "ALS"),   # India Gate
    ("AMB-006", "DL-06-KL-2345", 28.5672, 77.3211, "AVAILABLE", "BLS"),   # Mayur Vihar
    ("AMB-007", "DL-07-MN-6789", 28.6862, 77.2217, "AVAILABLE", "ALS"),   # Civil Lines
    ("AMB-008", "DL-08-OP-0123", 28.5494, 77.1855, "AVAILABLE", "BLS"),   # Vasant Kunj
    ("AMB-009", "DL-09-QR-4567", 28.6280, 77.3649, "AVAILABLE", "ALS"),   # Anand Vihar
    ("AMB-010", "DL-10-ST-8901", 28.4595, 77.0266, "AVAILABLE", "BLS"),   # Gurgaon
]

# ─── Delhi Hospitals (8 hospitals) ─────────────────────────────
HOSPITALS = [
    (
        "HOSP-001", "AIIMS New Delhi",
        28.5672, 77.2100,
        "trauma,cardiac,stroke,burn,respiratory,obstetric,poisoning,general",
        15, "AVAILABLE", 0,
    ),
    (
        "HOSP-002", "Safdarjung Hospital",
        28.5685, 77.2066,
        "trauma,cardiac,general,obstetric,respiratory",
        10, "AVAILABLE", 0,
    ),
    (
        "HOSP-003", "Sir Ganga Ram Hospital",
        28.6397, 77.1906,
        "cardiac,stroke,trauma,general",
        8, "AVAILABLE", 0,
    ),
    (
        "HOSP-004", "Max Super Speciality Saket",
        28.5275, 77.2152,
        "cardiac,trauma,stroke,burn,general",
        12, "AVAILABLE", 0,
    ),
    (
        "HOSP-005", "Fortis Escorts Heart Institute",
        28.5501, 77.2226,
        "cardiac,stroke,respiratory",
        6, "AVAILABLE", 0,
    ),
    (
        "HOSP-006", "GTB Hospital (Shahdara)",
        28.6834, 77.3105,
        "trauma,burn,general,obstetric",
        5, "AVAILABLE", 0,
    ),
    (
        "HOSP-007", "Lok Nayak Hospital",
        28.6363, 77.2398,
        "trauma,cardiac,general,poisoning,respiratory",
        9, "UNAVAILABLE", 30,    # ← This one is on OT diversion
    ),
    (
        "HOSP-008", "Apollo Hospital (Jasola)",
        28.5354, 77.2826,
        "cardiac,stroke,trauma,burn,obstetric,general",
        11, "AVAILABLE", 0,
    ),
]


def seed_sqlite_direct(conn: sqlite3.Connection):
    """Directly insert seed data into an open SQLite connection."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dispatches")
    cursor.execute("DELETE FROM incidents")
    cursor.execute("DELETE FROM ambulances")
    for amb in AMBULANCES:
        cursor.execute(
            """
            INSERT INTO ambulances
                (ambulance_id, vehicle_number, amb_latitude, amb_longitude, status, tier)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            amb,
        )
    print(f"[OK] Inserted {len(AMBULANCES)} ambulances into SQLite")

    cursor.execute("DELETE FROM hospitals")
    for hosp in HOSPITALS:
        cursor.execute(
            """
            INSERT INTO hospitals
                (hospital_id, name, latitude, longitude,
                 specialty_tags, icu_beds_available, ot_status, ot_clear_time_mins)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            hosp,
        )
    print(f"[OK] Inserted {len(HOSPITALS)} hospitals into SQLite")
    conn.commit()


def seed():
    if DB_TYPE == "sqlite":
        import os
        os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
        conn = sqlite3.connect(SQLITE_DB_PATH)
        # Ensure schema
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
        seed_sqlite_direct(conn)
        conn.close()
        print("[SUCCESS] SQLite Database seeded successfully!")
    else:
        import mysql.connector
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # ── Insert ambulances ──────────────────────────────────────
        cursor.execute("DELETE FROM dispatches")
        cursor.execute("DELETE FROM incidents")
        cursor.execute("DELETE FROM ambulances")
        for amb in AMBULANCES:
            cursor.execute(
                """
                INSERT INTO ambulances
                    (ambulance_id, vehicle_number, amb_latitude, amb_longitude, status, tier)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                amb,
            )
        print(f"[OK] Inserted {len(AMBULANCES)} ambulances into MySQL")

        # ── Insert hospitals ───────────────────────────────────────
        cursor.execute("DELETE FROM hospitals")
        for hosp in HOSPITALS:
            cursor.execute(
                """
                INSERT INTO hospitals
                    (hospital_id, name, latitude, longitude,
                     specialty_tags, icu_beds_available, ot_status, ot_clear_time_mins)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                hosp,
            )
        print(f"[OK] Inserted {len(HOSPITALS)} hospitals into MySQL")

        conn.commit()
        cursor.close()
        conn.close()
        print("[SUCCESS] MySQL Database seeded successfully!")


if __name__ == "__main__":
    seed()
