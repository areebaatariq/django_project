from django.urls import path

from routing.views import HealthView, RouteMapView, RouteView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("route/", RouteView.as_view(), name="route"),
    path("route/map/", RouteMapView.as_view(), name="route-map"),
]
