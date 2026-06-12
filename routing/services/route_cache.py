import hashlib
import json

from routing.models import GeocodeCache


def _route_key(start: str, finish: str) -> str:
    raw = f"{start.strip().lower()}|{finish.strip().lower()}"
    return f"route:{hashlib.md5(raw.encode()).hexdigest()}"


def get_cached_route(start: str, finish: str) -> dict | None:
    key = _route_key(start, finish)
    cached = GeocodeCache.objects.filter(query=key).first()
    if not cached:
        return None
    return json.loads(cached.display_name)


def cache_route(start: str, finish: str, route: dict) -> None:
    key = _route_key(start, finish)
    GeocodeCache.objects.update_or_create(
        query=key,
        defaults={
            "latitude": 0.0,
            "longitude": 0.0,
            "display_name": json.dumps(route),
        },
    )
