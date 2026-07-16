import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─── Google Maps ────────────────────────────────────────────────
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# ─── Firebase (bridge to Kaggle GPU / Qwen model) ──────────────
FIREBASE_URL = os.getenv("FIREBASE_URL", "https://hackproj-58daf-default-rtdb.firebaseio.com/")
AI_POLLING_TIMEOUT = int(os.getenv("AI_POLLING_TIMEOUT", 60))  # seconds to wait for Kaggle

# ─── Database Configuration ─────────────────────────────────────
# 'sqlite' (zero configuration, works out of the box) or 'mysql'
DB_TYPE = os.getenv("DB_TYPE", "sqlite")
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", os.path.join(os.path.dirname(__file__), "db", "hospitals.db"))

# ─── MySQL Database ──────────────────────────────────────────────
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "hospitals"),
}

# ─── Server ─────────────────────────────────────────────────────
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", 8000))

# ─── Simulation ─────────────────────────────────────────────────
# How often the simulator emits a new position (seconds)
SIMULATION_TICK_INTERVAL = 2.0

# Fallback ambulance speed (km/h) when Google Maps API is unavailable
FALLBACK_SPEED_KMH = 40.0
