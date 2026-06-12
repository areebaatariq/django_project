import time

import requests
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from routing.serializers import RouteRequestSerializer
from routing.services.geocoding import geocode_location
from routing.services.map_generator import generate_route_map
from routing.services.optimizer import optimize_fuel_stops
from routing.services.route_cache import cache_route, get_cached_route
from routing.services.routing import build_route_profile, get_route


def _resolve_route(start: str, finish: str) -> tuple[dict, int]:
    cached = get_cached_route(start, finish)
    if cached:
        return cached, 0

    start_lat, start_lon = geocode_location(start)
    finish_lat, finish_lon = geocode_location(finish)
    route = get_route(start_lon, start_lat, finish_lon, finish_lat)
    cache_route(start, finish, route)
    return route, 3


class HealthView(APIView):
    def get(self, request):
        return Response({"status": "ok"})


class RouteView(APIView):
    def post(self, request):
        serializer = RouteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        start = serializer.validated_data["start"]
        finish = serializer.validated_data["finish"]
        started_at = time.perf_counter()

        try:
            route, external_calls = _resolve_route(start, finish)
            profile = build_route_profile(route["coordinates"])
            optimization = optimize_fuel_stops(profile, route["distance_miles"])
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except requests.RequestException:
            return Response(
                {"error": "External routing/geocoding service is unavailable. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return Response(
            {
                "start": start,
                "finish": finish,
                "total_distance_miles": round(route["distance_miles"], 2),
                "duration_hours": round(route["duration_hours"], 2),
                "total_fuel_cost": optimization["total_fuel_cost"],
                "total_gallons": optimization["total_gallons"],
                "fuel_stops": optimization["fuel_stops"],
                "map_url": "/api/route/map/",
                "response_time_ms": elapsed_ms,
                "external_api_calls": external_calls,
            }
        )


class RouteMapView(APIView):
    def post(self, request):
        serializer = RouteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        start = serializer.validated_data["start"]
        finish = serializer.validated_data["finish"]

        try:
            route, _external_calls = _resolve_route(start, finish)
            profile = build_route_profile(route["coordinates"])
            optimization = optimize_fuel_stops(profile, route["distance_miles"])
            html = generate_route_map(route["coordinates"], start, finish, optimization["fuel_stops"])
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except requests.RequestException:
            return Response(
                {"error": "External routing/geocoding service is unavailable. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return HttpResponse(html)
