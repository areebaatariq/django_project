import math
from decimal import Decimal

from django.conf import settings

from routing.models import FuelStation
from routing.services.routing import haversine_miles


def _simplify_profile(profile: list[dict], max_points: int = 400) -> list[dict]:
    if len(profile) <= max_points:
        return profile
    step = max(1, len(profile) // max_points)
    simplified = [profile[i] for i in range(0, len(profile), step)]
    if simplified[-1] is not profile[-1]:
        simplified.append(profile[-1])
    return simplified


def _load_corridor_stations(profile: list[dict], corridor_radius: float) -> list[FuelStation]:
    min_lat = min(point["lat"] for point in profile)
    max_lat = max(point["lat"] for point in profile)
    min_lon = min(point["lon"] for point in profile)
    max_lon = max(point["lon"] for point in profile)

    lat_delta = corridor_radius / 69.0
    mid_lat = (min_lat + max_lat) / 2
    lon_delta = corridor_radius / max(abs(math.cos(math.radians(mid_lat))) * 69.0, 1.0)

    return list(
        FuelStation.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            latitude__gte=min_lat - lat_delta,
            latitude__lte=max_lat + lat_delta,
            longitude__gte=min_lon - lon_delta,
            longitude__lte=max_lon + lon_delta,
        )
    )


def _index_stations_on_route(
    stations: list[FuelStation],
    profile: list[dict],
    sample_every: int = 2,
) -> list[dict]:
    indexed = []
    profile_points = profile[::sample_every] or profile

    for station in stations:
        min_off_route = float("inf")
        closest_route_distance = profile[0]["distance_miles"]
        for point in profile_points:
            off_route = haversine_miles(point["lat"], point["lon"], station.latitude, station.longitude)
            if off_route < min_off_route:
                min_off_route = off_route
                closest_route_distance = point["distance_miles"]
        indexed.append(
            {
                "station": station,
                "route_distance": closest_route_distance,
                "off_route_miles": min_off_route,
                "price": float(station.price),
            }
        )
    return indexed


def _find_reachable(
    indexed_stations: list[dict],
    current_distance: float,
    fuel_remaining_miles: float,
    corridor_radius: float,
) -> list[dict]:
    return [
        entry
        for entry in indexed_stations
        if entry["off_route_miles"] <= corridor_radius
        and 0 < entry["route_distance"] - current_distance <= fuel_remaining_miles
    ]


def optimize_fuel_stops(route_profile: list[dict], total_distance_miles: float) -> dict:
    max_range = settings.VEHICLE_MAX_RANGE_MILES
    mpg = settings.VEHICLE_MPG
    tank_gallons = max_range / mpg
    refuel_at = max_range * 0.9
    corridor_radius = settings.FUEL_SEARCH_RADIUS_MILES

    profile = _simplify_profile(route_profile)
    corridor_stations = _load_corridor_stations(profile, corridor_radius * 2)
    indexed_stations = _index_stations_on_route(corridor_stations, profile)

    fuel_stops = []
    total_fuel_cost = Decimal("0")
    current_distance = 0.0
    fuel_remaining_miles = max_range

    while current_distance < total_distance_miles:
        miles_to_destination = total_distance_miles - current_distance
        if fuel_remaining_miles >= miles_to_destination:
            break

        search_range = min(refuel_at, fuel_remaining_miles)
        reachable = _find_reachable(indexed_stations, current_distance, search_range, corridor_radius)

        if not reachable:
            reachable = _find_reachable(
                indexed_stations,
                current_distance,
                fuel_remaining_miles,
                corridor_radius * 2,
            )

        if not reachable:
            raise ValueError("No fuel stations found within range along the route")

        best = min(reachable, key=lambda entry: entry["price"])
        station = best["station"]
        station_distance = best["route_distance"]

        miles_traveled = max(station_distance - current_distance, 0.1)
        gallons_used = Decimal(str(miles_traveled / mpg))
        gallons_to_buy = max(
            Decimal(str(tank_gallons)) - (Decimal(str(fuel_remaining_miles / mpg)) - gallons_used),
            Decimal("0.1"),
        )
        cost = gallons_to_buy * station.price

        fuel_stops.append(
            {
                "name": station.name,
                "address": station.address,
                "city": station.city,
                "state": station.state,
                "price_per_gallon": float(station.price),
                "latitude": station.latitude,
                "longitude": station.longitude,
                "distance_from_start_miles": round(station_distance, 2),
                "fuel_purchased_gallons": round(float(gallons_to_buy), 2),
                "cost": round(float(cost), 2),
            }
        )

        total_fuel_cost += cost
        current_distance = station_distance
        fuel_remaining_miles = max_range

    total_gallons = Decimal(str(total_distance_miles / mpg))
    if fuel_stops:
        total_fuel_cost = sum(Decimal(str(stop["cost"])) for stop in fuel_stops)
        reference_price = Decimal(str(fuel_stops[-1]["price_per_gallon"]))
    else:
        in_corridor = [s for s in indexed_stations if s["off_route_miles"] <= corridor_radius * 2]
        if not in_corridor:
            raise ValueError("No fuel stations found along the route")
        reference_price = Decimal(str(min(s["price"] for s in in_corridor)))
        total_fuel_cost = total_gallons * reference_price

    return {
        "fuel_stops": fuel_stops,
        "total_fuel_cost": round(float(total_fuel_cost), 2),
        "total_gallons": round(float(total_gallons), 2),
        "average_price_per_gallon": round(float(reference_price), 4),
    }
