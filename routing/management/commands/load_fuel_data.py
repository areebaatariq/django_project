import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand

from routing.models import FuelStation
from routing.services.geocoding import geocode_city_state

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA",
    "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT",
    "VA", "WA", "WV", "WI", "WY", "DC",
}


class Command(BaseCommand):
    help = "Load fuel station data from the assessment CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--skip-geocode", action="store_true")
        parser.add_argument("--clear", action="store_true")
        parser.add_argument("--per-state", type=int, default=None)

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {csv_path}"))
            return

        if options["clear"]:
            deleted, _ = FuelStation.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing fuel stations"))

        stations = [s for s in self._parse_csv(csv_path) if s["state"] in US_STATES]
        if options["per_state"]:
            by_state = defaultdict(list)
            for station in stations:
                by_state[station["state"]].append(station)
            stations = [s for state in sorted(by_state) for s in by_state[state][: options["per_state"]]]
        if options["limit"]:
            stations = stations[: options["limit"]]

        coords_cache = {}
        skipped = 0
        if not options["skip_geocode"]:
            locations = sorted({(s["city"], s["state"]) for s in stations})
            self.stdout.write(f"Geocoding {len(locations)} city/state pairs...")
            for i, (city, state) in enumerate(locations, 1):
                coords_cache[(city, state)] = geocode_city_state(city, state)
                if coords_cache[(city, state)]:
                    self.stdout.write(f"[{i}/{len(locations)}] {city}, {state}")

        records = []
        for station in stations:
            coords = coords_cache.get((station["city"], station["state"])) if not options["skip_geocode"] else None
            station["latitude"], station["longitude"] = coords if coords else (None, None)
            if not coords and not options["skip_geocode"]:
                skipped += 1
            records.append(FuelStation(**station))

        FuelStation.objects.bulk_create(records, batch_size=500)
        self.stdout.write(self.style.SUCCESS(f"Imported {len(records)} fuel stations"))
        if skipped:
            self.stdout.write(self.style.WARNING(f"Skipped geocoding for {skipped} stations"))

    def _parse_csv(self, csv_path: Path) -> list[dict]:
        grouped = {}
        with csv_path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                key = (
                    int(row["OPIS Truckstop ID"]),
                    row["Truckstop Name"].strip(),
                    row["Address"].strip(),
                    row["City"].strip(),
                    row["State"].strip(),
                )
                price = Decimal(row["Retail Price"].strip())
                if key not in grouped or price < grouped[key]["price"]:
                    grouped[key] = {
                        "opis_id": key[0], "name": key[1], "address": key[2],
                        "city": key[3], "state": key[4],
                        "rack_id": int(row["Rack ID"]) if row.get("Rack ID") else None,
                        "price": price,
                    }
        stations = sorted(grouped.values(), key=lambda s: (s["state"], s["city"], s["name"]))
        self.stdout.write(f"Found {len(stations)} unique stations in CSV")
        return stations
