from django.db import models


class FuelStation(models.Model):
    opis_id = models.IntegerField()
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    rack_id = models.IntegerField(null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=4)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["state", "price"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.city}, {self.state}) - ${self.price}"


class GeocodeCache(models.Model):
    query = models.CharField(max_length=255, unique=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    display_name = models.CharField(max_length=512, blank=True)

    def __str__(self):
        return self.query
