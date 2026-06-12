import time

import requests
from django.conf import settings

from routing.models import GeocodeCache

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "FuelRouteOptimizer/1.0"


def _request_geocode(query: str) -> tuple[float, float, str]:
    response = requests.get(
        NOMINATIM_URL,
        params={"q": query, "format": "json", "countrycodes": "us", "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=settings.GEOCODING_TIMEOUT,
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        raise ValueError(f"Location not found: {query}")
    result = results[0]
    return float(result["lat"]), float(result["lon"]), result.get("display_name", query)


def geocode_location(location: str, use_cache: bool = True) -> tuple[float, float]:
    query = location.strip()
    if not query:
        raise ValueError("Location cannot be empty")

    if use_cache:
        cached = GeocodeCache.objects.filter(query__iexact=query).first()
        if cached:
            return cached.latitude, cached.longitude

    lat, lon, display_name = _request_geocode(f"{query}, USA")
    GeocodeCache.objects.update_or_create(
        query=query,
        defaults={"latitude": lat, "longitude": lon, "display_name": display_name},
    )
    return lat, lon


def geocode_city_state(city: str, state: str, delay: float = 1.0) -> tuple[float, float] | None:
    city = city.strip()
    state = state.strip()
    query = f"{city}, {state}, USA"

    cached = GeocodeCache.objects.filter(query__iexact=query).first()
    if cached:
        return cached.latitude, cached.longitude

    for attempt in (query, f"{city}, {state}"):
        try:
            lat, lon, display_name = _request_geocode(attempt)
            GeocodeCache.objects.update_or_create(
                query=query,
                defaults={"latitude": lat, "longitude": lon, "display_name": display_name},
            )
            if delay:
                time.sleep(delay)
            return lat, lon
        except (ValueError, requests.RequestException):
            continue
    return None
