"""
SOS Ambulance Dispatch — FastAPI + Socket.IO Server
─────────────────────────────────────────────────────
REST endpoints for dispatch, fleet, and hospital queries.
WebSocket (Socket.IO) for real-time ambulance tracking.
"""

import asyncio
import uvicorn
import socketio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import SERVER_HOST, SERVER_PORT
from models.schemas import DistressRequest, DispatchResponse, AmbulanceOut, HospitalOut, AIAnalysis
from services.dispatch import dispatch as run_dispatch
from services.simulator import simulate_movement
from db.fleet_db import get_all_ambulances, get_ambulance, release_ambulance
from db.hospital_db import get_all_hospitals
from db.database import fetch_all

# ────────────────────────────────────────────────────────────────
#  App Setup
# ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SOS Ambulance Dispatch",
    description="AI-powered ambulance dispatch and live tracking system",
    version="1.0.0",
)

# Allow all origins for hackathon ease (tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Socket.IO (async mode, mounted on the same ASGI app) ──────
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
sio_app = socketio.ASGIApp(sio, other_asgi_app=app)

# Track active simulations so we can cancel if needed
_active_simulations: dict[str, asyncio.Task] = {}


# ────────────────────────────────────────────────────────────────
#  REST Endpoints
# ────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "SOS Ambulance Dispatch",
        "status": "running",
        "docs": "/docs",
    }


@app.post("/api/dispatch", response_model=DispatchResponse)
async def dispatch_endpoint(req: DistressRequest):
    """
    Accept a distress call and run the full dispatch pipeline:
    classify → find ambulance → find hospital → route → simulate.
    """
    try:
        result = run_dispatch(
            patient_name=req.patient_name or "Unknown",
            raw_transcript=req.raw_transcript,
            user_lat=req.user_latitude,
            user_lng=req.user_longitude,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    route_to_patient = result["route_to_patient"]
    route_to_hospital = result["route_to_hospital"]
    ambulance = result["ambulance"]
    hospital = result["hospital"]
    dispatch_id = result["dispatch_id"]

    # ── Kick off the movement simulation in the background ─────
    async def full_simulation():
        # Phase 1: Ambulance → Patient
        await simulate_movement(
            sio=sio,
            dispatch_id=dispatch_id,
            ambulance_id=ambulance["ambulance_id"],
            route=route_to_patient,
            phase="TO_PATIENT",
            speed_multiplier=5.0,   # 5× speed for demo
        )
        # Small pause at pickup
        await asyncio.sleep(3)
        # Phase 2: Patient → Hospital
        await simulate_movement(
            sio=sio,
            dispatch_id=dispatch_id,
            ambulance_id=ambulance["ambulance_id"],
            route=route_to_hospital,
            phase="TO_HOSPITAL",
            speed_multiplier=5.0,
        )
        # Mark ambulance available again after trip
        release_ambulance(ambulance["ambulance_id"])
        _active_simulations.pop(dispatch_id, None)

    task = asyncio.create_task(full_simulation())
    _active_simulations[dispatch_id] = task

    # ── Build the response ─────────────────────────────────────
    return DispatchResponse(
        dispatch_id=dispatch_id,
        incident_id=result["incident_id"],
        ambulance=AmbulanceOut(**ambulance),
        hospital=HospitalOut(**hospital),
        ai_urgency_tier=result["urgency"],
        ai_medical_tag=result["medical_tag"],
        estimated_arrival_mins=result["eta_minutes"],
        route_polyline=route_to_patient.encoded_polyline,
        route_points=route_to_patient.all_points,
        route_to_hospital_points=route_to_hospital.all_points,
        ai_analysis=AIAnalysis(**result["ai_analysis"]),
        message=(
            f"🚑 Ambulance {ambulance['vehicle_number']} dispatched! "
            f"ETA: {result['eta_minutes']} min | "
            f"Urgency: {result['urgency']} | "
            f"Heading to: {hospital['name']}"
        ),
    )


@app.get("/api/fleet", response_model=list[AmbulanceOut])
async def fleet_endpoint():
    """Return all ambulances with their current status and position."""
    rows = get_all_ambulances()
    return [AmbulanceOut(**r) for r in rows]


@app.get("/api/fleet/{ambulance_id}", response_model=AmbulanceOut)
async def fleet_single_endpoint(ambulance_id: str):
    """Get a single ambulance's current state."""
    row = get_ambulance(ambulance_id)
    if not row:
        raise HTTPException(status_code=404, detail="Ambulance not found")
    return AmbulanceOut(**row)


@app.get("/api/hospitals", response_model=list[HospitalOut])
async def hospitals_endpoint():
    """Return all hospitals."""
    rows = get_all_hospitals()
    return [HospitalOut(**r) for r in rows]


@app.get("/api/dispatches")
async def dispatches_endpoint():
    """Return all active dispatches."""
    return fetch_all(
        """
        SELECT d.*, i.ai_urgency_tier, i.ai_medical_tag,
               i.user_latitude, i.user_longitude
        FROM dispatches d
        JOIN incidents i ON d.incident_id = i.incident_id
        ORDER BY d.updated_at DESC
        LIMIT 50
        """
    )


# ────────────────────────────────────────────────────────────────
#  Socket.IO Events
# ────────────────────────────────────────────────────────────────

@sio.event
async def connect(sid, environ):
    print(f"[ws] Client connected: {sid}")


@sio.event
async def disconnect(sid):
    print(f"[ws] Client disconnected: {sid}")


@sio.event
async def track_ambulance(sid, data):
    """
    Client sends: { "dispatch_id": "DSP-XXXXXXXX" }
    We add them to a Socket.IO room so they receive location updates.
    """
    dispatch_id = data.get("dispatch_id")
    if dispatch_id:
        await sio.enter_room(sid, dispatch_id)
        await sio.emit("tracking_started", {
            "dispatch_id": dispatch_id,
            "message": f"Now tracking dispatch {dispatch_id}",
        }, to=sid)
        print(f"[ws] {sid} now tracking {dispatch_id}")


@sio.event
async def stop_tracking(sid, data):
    """Client wants to stop receiving updates for a dispatch."""
    dispatch_id = data.get("dispatch_id")
    if dispatch_id:
        await sio.leave_room(sid, dispatch_id)


# ────────────────────────────────────────────────────────────────
#  Entry Point
# ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  [SOS] SOS Ambulance Dispatch Server")
    print(f"  [API] http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"  [DOCS] http://localhost:{SERVER_PORT}/docs")
    print("=" * 60)
    # NOTE: We run `sio_app` (the Socket.IO ASGI wrapper) not `app`
    uvicorn.run(sio_app, host=SERVER_HOST, port=SERVER_PORT)
