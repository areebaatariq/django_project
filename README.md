# Fuel Route Optimizer API

Django REST API that calculates the most cost-effective fuel stops for US driving routes.

## Features

- Accepts US start and finish locations
- Returns optimal fuel stops based on retail prices from the provided CSV
- Assumes a 500-mile vehicle range and 10 MPG fuel efficiency
- Returns total fuel cost and an interactive HTML map
- Uses at most 3 free external API calls per request

## Tech Stack

- Django 5.2
- Django REST Framework
- SQLite
- OSRM for routing
- Nominatim for geocoding
- Folium for map rendering

## Setup (quick start)

The repo includes a pre-loaded `db.sqlite3` with all **6,855** fuel stations already imported and geocoded, so reviewers can run the API immediately without waiting for CSV import.

```bash
cd "django pro"
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Then open Postman and call `POST http://127.0.0.1:8000/api/route/`.

## Re-import from CSV (optional)

Only needed if you want to rebuild the database from scratch:

```bash
python manage.py load_fuel_data fuel-prices-for-be-assessment.csv --clear
python manage.py backfill_geocodes
```

**Note:** Full import geocodes thousands of city/state pairs via Nominatim and can take **1–2 hours** because of rate limits. The included `db.sqlite3` avoids that step.

## API Endpoints

### Health check

`GET /api/health/`

### Route optimization

`POST /api/route/`

```json
{
  "start": "Chicago, IL",
  "finish": "Los Angeles, CA"
}
```

### Route map

`POST /api/route/map/`

Same request body as `/api/route/`, but returns an interactive HTML map.

## External API Usage

Each route request makes:

1. Nominatim geocode for start
2. Nominatim geocode for finish
3. OSRM route lookup

Fuel station coordinates are geocoded once during CSV import and stored in the database.

Route results are cached in the database, so repeat requests for the same start/finish pair skip external API calls entirely.

## Assumptions

- Vehicle range: 500 miles
- Fuel efficiency: 10 MPG
- Tank capacity: 50 gallons
- Greedy optimizer picks the cheapest reachable station near the route
- Duplicate CSV rows for the same station use the lowest price

## Demo

Use Postman to call `POST http://127.0.0.1:8000/api/route/` and then `POST http://127.0.0.1:8000/api/route/map/` with the same JSON body.
