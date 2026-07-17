"""
Hospital DB operations — queries the `hospitals` table in MySQL.
"""

from db.database import fetch_all, fetch_one


def get_all_hospitals() -> list[dict]:
    """Return every hospital."""
    return fetch_all("SELECT * FROM hospitals")


def get_hospital(hospital_id: str) -> dict | None:
    """Get a single hospital by ID."""
    return fetch_one(
        "SELECT * FROM hospitals WHERE hospital_id = %s",
        (hospital_id,),
    )


def find_capable_hospitals(medical_tag: str) -> list[dict]:
    """
    Find hospitals whose specialty_tags contain the given medical tag
    AND are not on OT diversion (ot_status = 'AVAILABLE')
    AND have at least 1 ICU bed available.
    """
    return fetch_all(
        """
        SELECT * FROM hospitals
        WHERE specialty_tags LIKE %s
          AND ot_status = 'AVAILABLE'
          AND icu_beds_available > 0
        """,
        (f"%{medical_tag}%",),
    )


def find_all_available_hospitals() -> list[dict]:
    """Return hospitals that are available and have beds."""
    return fetch_all(
        """
        SELECT * FROM hospitals
        WHERE ot_status = 'AVAILABLE'
          AND icu_beds_available > 0
        """
    )


def update_hospital_capacity(hospital_id: str, icu_beds: int, ot_status: str) -> None:
    """Update ICU beds and OT diversion status dynamically in real-time."""
    from db.database import execute
    execute(
        "UPDATE hospitals SET icu_beds_available = %s, ot_status = %s WHERE hospital_id = %s",
        (icu_beds, ot_status, hospital_id),
    )

