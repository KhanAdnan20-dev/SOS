"""
Google Maps Directions API integration.
──────────────────────────────────────────
Fetches a route between two points, decodes the polyline,
and extracts per-step timing for traffic-aware simulation.

Falls back to straight-line interpolation if the API key is missing
or the request fails.
"""

import math
import time
import requests
import polyline as pl
from config import GOOGLE_MAPS_API_KEY, FALLBACK_SPEED_KMH

DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"


# ────────────────────────────────────────────────────────────────
#  Data Structures
# ────────────────────────────────────────────────────────────────

class RouteStep:
    """A single road segment with distance, duration, and coordinates."""

    def __init__(self, distance_m: float, duration_s: float, points: list[list[float]]):
        self.distance_m = distance_m      # metres
        self.duration_s = duration_s       # seconds (traffic-aware)
        self.points = points              # [[lat, lng], …]
        # Speed for this segment in m/s
        self.speed_mps = distance_m / duration_s if duration_s > 0 else 10.0


class Route:
    """Full route object returned to the dispatcher."""

    def __init__(
        self,
        steps: list[RouteStep],
        total_distance_m: float,
        total_duration_s: float,
        encoded_polyline: str | None,
        all_points: list[list[float]],
    ):
        self.steps = steps
        self.total_distance_m = total_distance_m
        self.total_duration_s = total_duration_s
        self.encoded_polyline = encoded_polyline
        self.all_points = all_points          # Flat list of all coordinates
        self.eta_minutes = math.ceil(total_duration_s / 60)


# ────────────────────────────────────────────────────────────────
#  Google Maps Directions
# ────────────────────────────────────────────────────────────────

def get_route(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> Route:
    """
    Get a traffic-aware route from origin to destination.
    Uses Google Maps if API key exists, otherwise falls back to free OSRM routing.
    If both fail, uses straight-line interpolation.
    """
    if GOOGLE_MAPS_API_KEY:
        try:
            return _fetch_google_route(origin_lat, origin_lng, dest_lat, dest_lng)
        except Exception as e:
            print(f"[routing] Google Maps API failed, trying OSRM: {e}")

    try:
        return _fetch_osrm_route(origin_lat, origin_lng, dest_lat, dest_lng)
    except Exception as e:
        print(f"[routing] OSRM API failed, using straight-line fallback: {e}")
        return _fallback_straight_line(origin_lat, origin_lng, dest_lat, dest_lng)


# ────────────────────────────────────────────────────────────────
#  OSRM Free Routing API (No API Key Required)
# ────────────────────────────────────────────────────────────────

def _fetch_osrm_route(
    origin_lat: float, origin_lng: float,
    dest_lat: float, dest_lng: float,
) -> Route:
    """Call the public OSRM routing machine for free road polylines."""
    # OSRM format: {longitude},{latitude}
    url = f"http://router.project-osrm.org/route/v1/driving/{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
    params = {
        "overview": "full",
        "geometries": "polyline",
        "steps": "true"
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != "Ok":
        raise RuntimeError(f"OSRM API status: {data.get('code')}")

    route_data = data["routes"][0]
    leg = route_data["legs"][0]
    encoded_poly = route_data["geometry"]

    steps: list[RouteStep] = []
    all_points: list[list[float]] = []

    for step in leg["steps"]:
        dist_m = step["distance"]
        dur_s = step["duration"]
        # OSRM steps contain their own polyline geometry
        step_poly = step["geometry"]
        decoded = pl.decode(step_poly)
        pts = [[lat, lng] for lat, lng in decoded]
        steps.append(RouteStep(dist_m, dur_s, pts))
        all_points.extend(pts)

    total_dist = route_data["distance"]
    total_dur = route_data["duration"]

    return Route(
        steps=steps,
        total_distance_m=total_dist,
        total_duration_s=total_dur,
        encoded_polyline=encoded_poly,
        all_points=all_points,
    )


# ────────────────────────────────────────────────────────────────
#  Google Maps Directions
# ────────────────────────────────────────────────────────────────

def _fetch_google_route(
    origin_lat: float, origin_lng: float,
    dest_lat: float, dest_lng: float,
) -> Route:
    """Call Google Maps Directions API with departure_time=now."""
    params = {
        "origin": f"{origin_lat},{origin_lng}",
        "destination": f"{dest_lat},{dest_lng}",
        "departure_time": "now",               # ← enables traffic data
        "key": GOOGLE_MAPS_API_KEY,
    }
    resp = requests.get(DIRECTIONS_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data["status"] != "OK":
        raise RuntimeError(f"Directions API status: {data['status']}")

    leg = data["routes"][0]["legs"][0]
    encoded_poly = data["routes"][0]["overview_polyline"]["points"]

    steps: list[RouteStep] = []
    all_points: list[list[float]] = []

    for step in leg["steps"]:
        dist_m = step["distance"]["value"]
        # Use duration_in_traffic if available, else duration
        dur_s = step.get("duration_in_traffic", step["duration"])["value"]
        decoded = pl.decode(step["polyline"]["points"])
        pts = [[lat, lng] for lat, lng in decoded]
        steps.append(RouteStep(dist_m, dur_s, pts))
        all_points.extend(pts)

    total_dist = leg["distance"]["value"]
    # traffic-aware total
    total_dur = leg.get("duration_in_traffic", leg["duration"])["value"]

    return Route(
        steps=steps,
        total_distance_m=total_dist,
        total_duration_s=total_dur,
        encoded_polyline=encoded_poly,
        all_points=all_points,
    )


# ────────────────────────────────────────────────────────────────
#  Fallback: straight-line interpolation
# ────────────────────────────────────────────────────────────────

def _haversine_m(lat1, lng1, lat2, lng2) -> float:
    """Haversine distance in metres."""
    R = 6_371_000
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lng2 - lng1)
    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _interpolate_points(
    lat1: float, lng1: float,
    lat2: float, lng2: float,
    num_points: int = 80,
) -> list[list[float]]:
    """Generate `num_points` evenly-spaced coordinates on a straight line."""
    points = []
    for i in range(num_points + 1):
        t = i / num_points
        lat = lat1 + t * (lat2 - lat1)
        lng = lng1 + t * (lng2 - lng1)
        points.append([round(lat, 6), round(lng, 6)])
    return points


def _fallback_straight_line(
    origin_lat: float, origin_lng: float,
    dest_lat: float, dest_lng: float,
) -> Route:
    """
    When no API key is available, interpolate a straight line
    and estimate duration using FALLBACK_SPEED_KMH.
    """
    dist_m = _haversine_m(origin_lat, origin_lng, dest_lat, dest_lng)
    # Multiply by 1.3 to roughly account for real road distance
    road_dist_m = dist_m * 1.3
    speed_mps = FALLBACK_SPEED_KMH * 1000 / 3600
    duration_s = road_dist_m / speed_mps

    points = _interpolate_points(origin_lat, origin_lng, dest_lat, dest_lng)
    step = RouteStep(distance_m=road_dist_m, duration_s=duration_s, points=points)

    return Route(
        steps=[step],
        total_distance_m=road_dist_m,
        total_duration_s=duration_s,
        encoded_polyline=None,
        all_points=points,
    )
