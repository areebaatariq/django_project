import math

import requests
from django.conf import settings

OSRM_URL = "http://router.project-osrm.org/route/v1/driving"


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_miles = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius_miles * math.asin(math.sqrt(a))


def get_route(start_lon: float, start_lat: float, end_lon: float, end_lat: float) -> dict:
    url = f"{OSRM_URL}/{start_lon},{start_lat};{end_lon},{end_lat}"
    response = requests.get(
        url,
        params={"overview": "simplified", "geometries": "geojson"},
        timeout=settings.ROUTING_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise ValueError("Unable to calculate route between the provided locations")

    route = data["routes"][0]
    coordinates = route["geometry"]["coordinates"]
    return {
        "coordinates": coordinates,
        "distance_miles": route["distance"] / 1609.344,
        "duration_hours": route["duration"] / 3600,
    }


def build_route_profile(coordinates: list[list[float]]) -> list[dict]:
    profile = []
    cumulative = 0.0
    for index, (lon, lat) in enumerate(coordinates):
        if index > 0:
            prev_lon, prev_lat = coordinates[index - 1]
            cumulative += haversine_miles(prev_lat, prev_lon, lat, lon)
        profile.append({"lon": lon, "lat": lat, "distance_miles": cumulative})
    return profile
