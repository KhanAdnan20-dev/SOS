"""
Core Dispatch Logic
────────────────────
Orchestrates the full pipeline:
  Distress → Classify (AI Model) → Find ambulance → Find hospital → Route → Record → Simulate
"""

import uuid
from geopy.distance import geodesic

from services.classifier import classify, required_ambulance_tier
from services.routing import get_route, Route
from db.fleet_db import get_available_ambulances, lock_ambulance
from db.hospital_db import find_capable_hospitals, find_all_available_hospitals
from db.database import execute, fetch_one


def _find_closest_ambulance(
    user_lat: float,
    user_lng: float,
    tier: str | None = None,
) -> dict | None:
    """
    From all AVAILABLE ambulances (optionally filtered by tier),
    return the one closest to the user's location.
    """
    ambulances = get_available_ambulances(tier=tier)
    if not ambulances:
        # If no ALS available, fall back to any available ambulance
        if tier:
            ambulances = get_available_ambulances(tier=None)
        if not ambulances:
            return None

    user_pos = (user_lat, user_lng)
    closest = None
    min_dist = float("inf")

    for amb in ambulances:
        amb_pos = (amb["amb_latitude"], amb["amb_longitude"])
        dist = geodesic(user_pos, amb_pos).km
        if dist < min_dist:
            min_dist = dist
            closest = amb

    return closest


def _find_best_hospital(
    medical_tag: str,
    user_lat: float,
    user_lng: float,
) -> dict | None:
    """
    Find the closest hospital that can handle this emergency type,
    has ICU beds, and is not on OT diversion.
    """
    hospitals = find_capable_hospitals(medical_tag)
    if not hospitals:
        # Fallback: any available hospital
        hospitals = find_all_available_hospitals()
    if not hospitals:
        return None

    user_pos = (user_lat, user_lng)
    closest = None
    min_dist = float("inf")

    for hosp in hospitals:
        hosp_pos = (hosp["latitude"], hosp["longitude"])
        dist = geodesic(user_pos, hosp_pos).km
        if dist < min_dist:
            min_dist = dist
            closest = hosp

    return closest


def dispatch(
    patient_name: str,
    raw_transcript: str,
    user_lat: float,
    user_lng: float,
) -> dict:
    """
    Full dispatch pipeline. Returns a dict with everything the
    frontend needs (IDs, ambulance, hospital, route, ETA, AI analysis).

    Raises ValueError if no ambulance or hospital is available.
    """

    # ── Step 1: Classify the distress via AI Model ─────────────
    ai_result = classify(raw_transcript)

    urgency = ai_result["urgency_tier"]
    medical_tag = ai_result["medical_tag"]
    required_tier = required_ambulance_tier(urgency)

    # ── Check if ambulance is actually required ────────────────
    # Even if AI says ambulance not required, we still proceed
    # (better safe than sorry), but log it
    if not ai_result.get("ambulance_required", True):
        print(f"[dispatch] [INFO] AI suggests ambulance may not be required "
              f"(confidence: {ai_result['confidence']}), dispatching anyway.")

    # ── Step 2: Find closest available ambulance ───────────────
    ambulance = _find_closest_ambulance(user_lat, user_lng, tier=required_tier)
    if not ambulance:
        raise ValueError("No ambulances available right now.")

    # ── Step 3: Find best hospital ─────────────────────────────
    hospital = _find_best_hospital(medical_tag, user_lat, user_lng)
    if not hospital:
        raise ValueError("No suitable hospitals available right now.")

    # ── Step 4: Get traffic-aware route (ambulance → user) ─────
    route_to_patient: Route = get_route(
        ambulance["amb_latitude"], ambulance["amb_longitude"],
        user_lat, user_lng,
    )

    # ── Step 5: Get route (user → hospital) for later phase ────
    route_to_hospital: Route = get_route(
        user_lat, user_lng,
        hospital["latitude"], hospital["longitude"],
    )

    # ── Step 6: Lock ambulance ─────────────────────────────────
    lock_ambulance(ambulance["ambulance_id"])

    # ── Step 7: Create incident record ─────────────────────────
    incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
    execute(
        """
        INSERT INTO incidents
            (incident_id, patient_name, raw_transcript,
             ai_urgency_tier, ai_medical_tag,
             user_latitude, user_longitude)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (incident_id, patient_name, raw_transcript,
         urgency, medical_tag, user_lat, user_lng),
    )

    # ── Step 8: Create dispatch record ─────────────────────────
    dispatch_id = f"DSP-{uuid.uuid4().hex[:8].upper()}"
    execute(
        """
        INSERT INTO dispatches
            (dispatch_id, incident_id, ambulance_id,
             hospital_id, estimated_arrival_mins, dispatch_status)
        VALUES (%s, %s, %s, %s, %s, 'EN_ROUTE_TO_PATIENT')
        """,
        (dispatch_id, incident_id, ambulance["ambulance_id"],
         hospital["hospital_id"], route_to_patient.eta_minutes),
    )

    # ── Return everything the app layer needs ──────────────────
    return {
        "dispatch_id": dispatch_id,
        "incident_id": incident_id,
        "ambulance": ambulance,
        "hospital": hospital,
        "urgency": urgency,
        "medical_tag": medical_tag,
        "eta_minutes": route_to_patient.eta_minutes,
        "route_to_patient": route_to_patient,
        "route_to_hospital": route_to_hospital,

        # ── Rich AI analysis (passed through to the frontend) ──
        "ai_analysis": {
            "severity":               ai_result["severity"],
            "priority":               ai_result["priority"],
            "ambulance_required":     ai_result["ambulance_required"],
            "suspected_conditions":   ai_result["suspected_conditions"],
            "recommended_department": ai_result["recommended_department"],
            "recommended_specialist": ai_result["recommended_specialist"],
            "confidence":             ai_result["confidence"],
            "first_aid":              ai_result["first_aid"],
            "reasoning":              ai_result["reasoning"],
            "trauma_type":            ai_result["trauma_type"],
        },
    }
