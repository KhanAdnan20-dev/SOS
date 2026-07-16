"""
Real-Time Ambulance Movement Simulator
────────────────────────────────────────
Takes a Route (from routing.py) and "drives" the ambulance along it,
emitting Socket.IO events at every tick so the frontend can animate
the marker.

Traffic-aware: each RouteStep has its own speed derived from
Google Maps duration_in_traffic, so the marker naturally slows
in congested segments and speeds up on clear roads.
"""

import asyncio
import math
import time
from services.routing import Route, RouteStep
from db.fleet_db import update_ambulance_position, update_ambulance_status
from config import SIMULATION_TICK_INTERVAL


def _bearing(lat1, lng1, lat2, lng2) -> float:
    """Compute bearing (heading) from point 1 to point 2 in degrees."""
    φ1 = math.radians(lat1)
    φ2 = math.radians(lat2)
    Δλ = math.radians(lng2 - lng1)
    x = math.sin(Δλ) * math.cos(φ2)
    y = math.cos(φ1) * math.sin(φ2) - math.sin(φ1) * math.cos(φ2) * math.cos(Δλ)
    θ = math.atan2(x, y)
    return (math.degrees(θ) + 360) % 360


def _distance_between(p1: list[float], p2: list[float]) -> float:
    """Quick haversine in metres between two [lat, lng] points."""
    R = 6_371_000
    lat1, lng1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lng2 = math.radians(p2[0]), math.radians(p2[1])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _interpolate(p1: list[float], p2: list[float], fraction: float) -> list[float]:
    """Linearly interpolate between two [lat, lng] points."""
    return [
        p1[0] + fraction * (p2[0] - p1[0]),
        p1[1] + fraction * (p2[1] - p1[1]),
    ]


async def simulate_movement(
    sio,                    # python-socketio.AsyncServer
    dispatch_id: str,
    ambulance_id: str,
    route: Route,
    phase: str = "TO_PATIENT",   # 'TO_PATIENT' or 'TO_HOSPITAL'
    speed_multiplier: float = 5.0,   # >1 = faster simulation for demo
):
    """
    Async generator-style loop that:
      1. Walks through each RouteStep
      2. Within each step, advances position based on step's speed
      3. Emits a 'ambulance_location_update' event every tick
      4. Updates the DB position

    speed_multiplier lets you fast-forward the simulation for demos
    (e.g., 5× means a 10-min route plays out in 2 minutes).
    """
    total_points = sum(len(s.points) for s in route.steps)
    points_emitted = 0

    for step in route.steps:
        if len(step.points) < 2:
            points_emitted += len(step.points)
            continue

        # How fast do we traverse this step's points?
        # Total real-world time for this step = step.duration_s
        # We compress it by speed_multiplier for the demo
        sim_duration = step.duration_s / speed_multiplier
        num_segments = len(step.points) - 1
        time_per_segment = sim_duration / num_segments if num_segments > 0 else SIMULATION_TICK_INTERVAL

        for i in range(num_segments):
            p_start = step.points[i]
            p_end = step.points[i + 1]

            # If the segment takes longer than our tick interval,
            # interpolate sub-positions within the segment
            ticks_in_segment = max(1, int(time_per_segment / SIMULATION_TICK_INTERVAL))
            for t in range(ticks_in_segment):
                fraction = (t + 1) / ticks_in_segment
                pos = _interpolate(p_start, p_end, fraction)
                heading = _bearing(p_start[0], p_start[1], p_end[0], p_end[1])
                speed_kmh = (step.speed_mps * 3.6) if step.speed_mps else 0

                points_emitted += (1 if t == ticks_in_segment - 1 else 0)
                progress = points_emitted / total_points if total_points else 0

                payload = {
                    "dispatch_id": dispatch_id,
                    "ambulance_id": ambulance_id,
                    "latitude": round(pos[0], 6),
                    "longitude": round(pos[1], 6),
                    "heading": round(heading, 1),
                    "speed_kmh": round(speed_kmh, 1),
                    "progress_pct": round(progress, 3),
                    "phase": phase,
                }

                # Emit to all clients in the dispatch's room
                await sio.emit(
                    "ambulance_location_update",
                    payload,
                    room=dispatch_id,
                )

                # Also update the DB so REST polling clients get fresh accurate status & data
                db_status = "EN_ROUTE_TO_PATIENT" if phase == "TO_PATIENT" else "EN_ROUTE_TO_HOSPITAL"
                update_ambulance_position(ambulance_id, pos[0], pos[1], status=db_status)

                await asyncio.sleep(SIMULATION_TICK_INTERVAL)

    # Final event: ambulance has arrived at phase target
    if phase == "TO_PATIENT":
        update_ambulance_status(ambulance_id, "AT_SCENE")

    await sio.emit(
        "ambulance_arrived",
        {
            "dispatch_id": dispatch_id,
            "ambulance_id": ambulance_id,
            "phase": phase,
            "message": f"Ambulance arrived at {'patient' if phase == 'TO_PATIENT' else 'hospital'}!",
        },
        room=dispatch_id,
    )
