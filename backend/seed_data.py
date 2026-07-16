"""
Seed Script — Populates ambulances & hospitals tables with Delhi test data.
──────────────────────────────────────────────────────────────────────────────
Run once:   python seed_data.py
"""

import sqlite3
from config import DB_TYPE, SQLITE_DB_PATH, DB_CONFIG

# ─── Delhi + Mumbai Ambulance Fleet (25 units total) ───────────
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
    # ─── Mumbai Units (15 ambulances) ─────────────────────────────
    ("AMB-MUM-011", "MH-01-AB-1111", 19.0544, 72.8402, "AVAILABLE", "ALS"),  # Bandra
    ("AMB-MUM-012", "MH-01-CD-2222", 19.0178, 72.8478, "AVAILABLE", "ALS"),  # Dadar
    ("AMB-MUM-013", "MH-02-EF-3333", 19.1136, 72.8697, "AVAILABLE", "ALS"),  # Andheri
    ("AMB-MUM-014", "MH-02-GH-4444", 19.1020, 72.8267, "AVAILABLE", "BLS"),  # Juhu
    ("AMB-MUM-015", "MH-03-IJ-5555", 19.0657, 72.8777, "AVAILABLE", "ALS"),  # Kurla
    ("AMB-MUM-016", "MH-01-KL-6666", 18.9400, 72.8353, "AVAILABLE", "ALS"),  # CSMT / Fort
    ("AMB-MUM-017", "MH-03-MN-7777", 19.1197, 72.9051, "AVAILABLE", "BLS"),  # Powai
    ("AMB-MUM-018", "MH-04-OP-8888", 19.2307, 72.8567, "AVAILABLE", "ALS"),  # Borivali
    ("AMB-MUM-019", "MH-04-QR-9999", 19.2183, 72.9781, "AVAILABLE", "ALS"),  # Thane
    ("AMB-MUM-020", "MH-43-ST-0001", 19.0330, 73.0297, "AVAILABLE", "ALS"),  # Navi Mumbai
    ("AMB-MUM-021", "MH-01-UV-0002", 18.9067, 72.8147, "AVAILABLE", "BLS"),  # Colaba
    ("AMB-MUM-022", "MH-01-WX-0003", 19.0180, 72.8181, "AVAILABLE", "ALS"),  # Worli
    ("AMB-MUM-023", "MH-03-YZ-0004", 19.0860, 72.9090, "AVAILABLE", "BLS"),  # Ghatkopar
    ("AMB-MUM-024", "MH-02-AB-0005", 19.1874, 72.8484, "AVAILABLE", "ALS"),  # Malad
    ("AMB-MUM-025", "MH-02-CD-0006", 19.1633, 72.8467, "AVAILABLE", "BLS"),  # Goregaon
]

# ─── Delhi/NCR + Mumbai Hospitals (52 hospitals total) ──────────
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
        9, "UNAVAILABLE", 30,    # ← On OT diversion
    ),
    (
        "HOSP-008", "Apollo Hospital (Jasola)",
        28.5354, 77.2826,
        "cardiac,stroke,trauma,burn,obstetric,general",
        11, "AVAILABLE", 0,
    ),
    (
        "HOSP-009", "BLK-Max Super Speciality Hospital",
        28.6432, 77.1785,
        "trauma,cardiac,stroke,burn,general",
        14, "AVAILABLE", 0,
    ),
    (
        "HOSP-010", "Fortis Memorial Research Gurgaon",
        28.4582, 77.0726,
        "cardiac,stroke,trauma,general,obstetric",
        18, "AVAILABLE", 0,
    ),
    (
        "HOSP-011", "Medanta - The Medicity Gurgaon",
        28.4385, 77.0425,
        "cardiac,trauma,stroke,burn,poisoning,general",
        25, "AVAILABLE", 0,
    ),
    (
        "HOSP-012", "Indraprastha Apollo Sarita Vihar",
        28.5323, 77.2882,
        "trauma,cardiac,stroke,burn,general",
        12, "AVAILABLE", 0,
    ),
    (
        "HOSP-013", "Artemis Hospital Gurgaon",
        28.4326, 77.0689,
        "cardiac,trauma,stroke,respiratory,general",
        10, "AVAILABLE", 0,
    ),
    (
        "HOSP-014", "Max Super Speciality Patparganj",
        28.6295, 77.3065,
        "cardiac,trauma,general,respiratory",
        9, "AVAILABLE", 0,
    ),
    (
        "HOSP-015", "Jaypee Hospital Noida",
        28.5085, 77.3712,
        "trauma,cardiac,burn,general,obstetric",
        16, "AVAILABLE", 0,
    ),
    (
        "HOSP-016", "Kailash Hospital Noida Sec 27",
        28.5796, 77.3274,
        "cardiac,trauma,general,respiratory",
        8, "UNAVAILABLE", 25,
    ),
    (
        "HOSP-017", "Amrita Hospital Faridabad",
        28.4116, 77.3375,
        "trauma,cardiac,stroke,burn,poisoning,obstetric,general",
        30, "AVAILABLE", 0,
    ),
    (
        "HOSP-018", "Holy Family Hospital Okhla",
        28.5601, 77.2798,
        "trauma,general,obstetric,respiratory",
        7, "AVAILABLE", 0,
    ),
    (
        "HOSP-019", "Moolchand Medcity",
        28.5668, 77.2343,
        "cardiac,general,obstetric,stroke",
        6, "AVAILABLE", 0,
    ),
    (
        "HOSP-020", "RML Hospital (Ram Manohar Lohia)",
        28.6262, 77.2001,
        "trauma,cardiac,burn,poisoning,general",
        11, "AVAILABLE", 0,
    ),
    (
        "HOSP-021", "Rajiv Gandhi Super Speciality",
        28.6948, 77.3142,
        "cardiac,respiratory,general",
        15, "AVAILABLE", 0,
    ),
    (
        "HOSP-022", "Venkateshwar Hospital Dwarka",
        28.5878, 77.0423,
        "cardiac,trauma,stroke,general",
        13, "AVAILABLE", 0,
    ),
    # ─── Mumbai Hospitals (30 hospitals) ──────────────────────────
    (
        "HOSP-023", "Lilavati Hospital Bandra West",
        19.0510, 72.8290,
        "trauma,cardiac,stroke,burn,general,obstetric",
        18, "AVAILABLE", 0,
    ),
    (
        "HOSP-024", "P. D. Hinduja Hospital Mahim",
        19.0345, 72.8386,
        "cardiac,stroke,trauma,general,respiratory",
        15, "AVAILABLE", 0,
    ),
    (
        "HOSP-025", "Kokilaben Ambani Hospital Andheri",
        19.1315, 72.8250,
        "trauma,cardiac,stroke,burn,poisoning,general",
        25, "AVAILABLE", 0,
    ),
    (
        "HOSP-026", "Nanavati Max Super Speciality Vile Parle",
        19.0965, 72.8402,
        "cardiac,trauma,stroke,general,obstetric",
        20, "AVAILABLE", 0,
    ),
    (
        "HOSP-027", "Saifee Hospital Charni Road",
        18.9517, 72.8183,
        "cardiac,trauma,general,respiratory",
        12, "AVAILABLE", 0,
    ),
    (
        "HOSP-028", "Sir H. N. Reliance Hospital Girgaon",
        18.9585, 72.8195,
        "trauma,cardiac,stroke,burn,general,poisoning",
        22, "AVAILABLE", 0,
    ),
    (
        "HOSP-029", "Breach Candy Hospital Cumballa Hill",
        18.9719, 72.8051,
        "cardiac,stroke,general,obstetric",
        14, "AVAILABLE", 0,
    ),
    (
        "HOSP-030", "Sir J. J. Hospital Byculla",
        18.9634, 72.8339,
        "trauma,burn,general,poisoning,respiratory,obstetric",
        30, "AVAILABLE", 0,
    ),
    (
        "HOSP-031", "KEM Hospital Parel",
        19.0025, 72.8424,
        "trauma,cardiac,stroke,burn,poisoning,general",
        35, "AVAILABLE", 0,
    ),
    (
        "HOSP-032", "Tata Memorial Hospital Parel",
        19.0048, 72.8428,
        "general,respiratory,trauma",
        16, "AVAILABLE", 0,
    ),
    (
        "HOSP-033", "Jaslok Hospital Pedder Road",
        18.9715, 72.8089,
        "cardiac,stroke,trauma,general",
        14, "AVAILABLE", 0,
    ),
    (
        "HOSP-034", "Bombay Hospital Marine Lines",
        18.9405, 72.8298,
        "trauma,cardiac,general,respiratory",
        18, "AVAILABLE", 0,
    ),
    (
        "HOSP-035", "Wockhardt Hospital Mumbai Central",
        18.9740, 72.8226,
        "cardiac,stroke,trauma,burn,general",
        20, "AVAILABLE", 0,
    ),
    (
        "HOSP-036", "Fortis Hospital Mulund",
        19.1663, 72.9430,
        "cardiac,trauma,stroke,general,respiratory",
        22, "AVAILABLE", 0,
    ),
    (
        "HOSP-037", "Dr. L. H. Hiranandani Hospital Powai",
        19.1197, 72.9154,
        "cardiac,trauma,general,obstetric",
        16, "AVAILABLE", 0,
    ),
    (
        "HOSP-038", "Holy Family Hospital Bandra West",
        19.0566, 72.8248,
        "general,cardiac,obstetric,respiratory",
        10, "AVAILABLE", 0,
    ),
    (
        "HOSP-039", "SL Raheja Hospital Mahim",
        19.0435, 72.8430,
        "cardiac,trauma,general,burn",
        12, "AVAILABLE", 0,
    ),
    (
        "HOSP-040", "Global Hospital Parel",
        18.9972, 72.8390,
        "cardiac,stroke,trauma,general",
        15, "AVAILABLE", 0,
    ),
    (
        "HOSP-041", "Bhaktivedanta Hospital Mira Road",
        19.2805, 72.8682,
        "trauma,general,cardiac,obstetric",
        14, "AVAILABLE", 0,
    ),
    (
        "HOSP-042", "Jupiter Hospital Thane",
        19.2136, 72.9734,
        "cardiac,stroke,trauma,burn,general",
        24, "AVAILABLE", 0,
    ),
    (
        "HOSP-043", "Apollo Hospital CBD Belapur Navi Mumbai",
        19.0169, 73.0406,
        "trauma,cardiac,stroke,burn,general,poisoning",
        20, "AVAILABLE", 0,
    ),
    (
        "HOSP-044", "Fortis Hiranandani Hospital Vashi",
        19.0715, 72.9984,
        "cardiac,trauma,general,respiratory",
        14, "AVAILABLE", 0,
    ),
    (
        "HOSP-045", "MGM Hospital Vashi",
        19.0768, 73.0034,
        "trauma,general,obstetric,burn",
        18, "AVAILABLE", 0,
    ),
    (
        "HOSP-046", "S. L. Nairs Hospital Mumbai Central",
        18.9745, 72.8235,
        "trauma,general,poisoning,respiratory",
        16, "UNAVAILABLE", 35,   # ← On OT diversion
    ),
    (
        "HOSP-047", "Sion Hospital (LTMGH) Sion",
        19.0360, 72.8601,
        "trauma,cardiac,burn,general,obstetric",
        32, "AVAILABLE", 0,
    ),
    (
        "HOSP-048", "Cooper Hospital Juhu",
        19.1085, 72.8368,
        "trauma,general,poisoning,obstetric",
        20, "AVAILABLE", 0,
    ),
    (
        "HOSP-049", "Rajawadi Hospital Ghatkopar",
        19.0833, 72.9067,
        "trauma,general,burn,respiratory",
        15, "AVAILABLE", 0,
    ),
    (
        "HOSP-050", "Bhabha Hospital Bandra West",
        19.0612, 72.8324,
        "trauma,general,obstetric",
        12, "AVAILABLE", 0,
    ),
    (
        "HOSP-051", "Karuna Hospital Borivali",
        19.2372, 72.8533,
        "cardiac,trauma,general",
        11, "AVAILABLE", 0,
    ),
    (
        "HOSP-052", "Apex Multispeciality Hospital Borivali",
        19.2312, 72.8590,
        "general,cardiac,trauma",
        10, "AVAILABLE", 0,
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
