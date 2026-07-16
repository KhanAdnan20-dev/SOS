"""
Pydantic schemas for request / response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ──────────────────────── Requests ─────────────────────────────

class DistressRequest(BaseModel):
    """Incoming emergency call payload."""
    patient_name: Optional[str] = "Unknown"
    raw_transcript: str = Field(..., description="Raw text/transcript of the distress call")
    user_latitude: float = Field(..., ge=-90, le=90)
    user_longitude: float = Field(..., ge=-180, le=180)


# ──────────────────────── DB Models ────────────────────────────

class AmbulanceOut(BaseModel):
    ambulance_id: str
    vehicle_number: str
    amb_latitude: float
    amb_longitude: float
    status: str
    tier: str


class HospitalOut(BaseModel):
    hospital_id: str
    name: str
    latitude: float
    longitude: float
    specialty_tags: str
    icu_beds_available: int
    ot_status: str
    ot_clear_time_mins: int


class IncidentOut(BaseModel):
    incident_id: str
    patient_name: str
    raw_transcript: str
    ai_urgency_tier: str
    ai_medical_tag: str
    user_latitude: float
    user_longitude: float
    created_at: Optional[datetime] = None


# ──────────────────────── AI Analysis ──────────────────────────

class AIAnalysis(BaseModel):
    """Rich output from the AI triage model."""
    severity: str                                  # Critical / High / Medium / Low
    priority: int                                  # 1-4
    ambulance_required: bool
    suspected_conditions: List[str]                # e.g. ["Acute coronary syndrome"]
    recommended_department: str                    # e.g. "Emergency Medicine"
    recommended_specialist: str                    # e.g. "Cardiology"
    confidence: float = Field(ge=0.0, le=1.0)
    first_aid: List[str]                           # e.g. ["Stay with the patient."]
    reasoning: str
    trauma_type: str                               # e.g. "Cardiac", "Blunt_Trauma"


# ──────────────────────── Responses ────────────────────────────

class DispatchResponse(BaseModel):
    """What the client receives after a dispatch request."""
    dispatch_id: str
    incident_id: str
    ambulance: AmbulanceOut
    hospital: HospitalOut
    ai_urgency_tier: str
    ai_medical_tag: str
    estimated_arrival_mins: int
    route_polyline: Optional[str] = None
    route_points: Optional[List[List[float]]] = None
    route_to_hospital_points: Optional[List[List[float]]] = None
    ai_analysis: AIAnalysis                        # Full AI model output
    message: str


class LocationUpdate(BaseModel):
    """Emitted via WebSocket as the ambulance moves."""
    dispatch_id: str
    ambulance_id: str
    latitude: float
    longitude: float
    heading: Optional[float] = None
    speed_kmh: Optional[float] = None
    progress_pct: float
    phase: str
