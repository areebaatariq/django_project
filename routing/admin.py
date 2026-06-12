from django.contrib import admin

from routing.models import FuelStation, GeocodeCache


@admin.register(FuelStation)
class FuelStationAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "state", "price", "latitude", "longitude")
    list_filter = ("state",)
    search_fields = ("name", "city", "address")


@admin.register(GeocodeCache)
class GeocodeCacheAdmin(admin.ModelAdmin):
    list_display = ("query", "latitude", "longitude")
    search_fields = ("query",)
