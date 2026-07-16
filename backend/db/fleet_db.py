"""
Fleet DB operations — queries the `ambulances` table in MySQL.
"""

from db.database import fetch_all, fetch_one, execute


def get_all_ambulances() -> list[dict]:
    """Return every ambulance and its current state."""
    return fetch_all("SELECT * FROM ambulances")


def get_available_ambulances(tier: str = None) -> list[dict]:
    """
    Return ambulances with status = 'AVAILABLE'.
    Optionally filter by tier ('ALS' or 'BLS').
    """
    if tier:
        return fetch_all(
            "SELECT * FROM ambulances WHERE status = 'AVAILABLE' AND tier = %s",
            (tier,),
        )
    return fetch_all("SELECT * FROM ambulances WHERE status = 'AVAILABLE'")


def get_ambulance(ambulance_id: str) -> dict | None:
    """Get a single ambulance by ID."""
    return fetch_one(
        "SELECT * FROM ambulances WHERE ambulance_id = %s",
        (ambulance_id,),
    )


def lock_ambulance(ambulance_id: str) -> None:
    """Set ambulance status to DISPATCHED (no longer available)."""
    execute(
        "UPDATE ambulances SET status = 'DISPATCHED' WHERE ambulance_id = %s",
        (ambulance_id,),
    )


def release_ambulance(ambulance_id: str) -> None:
    """Set ambulance status back to AVAILABLE after a trip completes."""
    execute(
        "UPDATE ambulances SET status = 'AVAILABLE' WHERE ambulance_id = %s",
        (ambulance_id,),
    )


def update_ambulance_position(ambulance_id: str, lat: float, lng: float, status: str = None) -> None:
    """Update the live position and optional status of an ambulance in the DB."""
    if status:
        execute(
            "UPDATE ambulances SET amb_latitude = %s, amb_longitude = %s, status = %s WHERE ambulance_id = %s",
            (lat, lng, status, ambulance_id),
        )
    else:
        execute(
            "UPDATE ambulances SET amb_latitude = %s, amb_longitude = %s WHERE ambulance_id = %s",
            (lat, lng, ambulance_id),
        )


def update_ambulance_status(ambulance_id: str, status: str) -> None:
    """Update the clinical state/status of an ambulance in the DB."""
    execute(
        "UPDATE ambulances SET status = %s WHERE ambulance_id = %s",
        (status, ambulance_id),
    )
