import folium
from branca.element import MacroElement
from jinja2 import Template
from folium.plugins import Fullscreen


class _MapResizeFix(MacroElement):
    """Keep Leaflet layout stable when zooming or resizing the window."""

    _template = Template(
        """
        {% macro script(this, kwargs) %}
            var map = {{ this._parent.get_name() }};
            function refreshMapSize() {
                map.invalidateSize({pan: false});
            }
            setTimeout(refreshMapSize, 100);
            setTimeout(refreshMapSize, 500);
            window.addEventListener("resize", refreshMapSize);
        {% endmacro %}
        """
    )


def _numbered_icon(number: int) -> folium.DivIcon:
    return folium.DivIcon(
        html=(
            f'<div style="background:#e67e22;color:#fff;border:2px solid #fff;'
            f'border-radius:50%;width:26px;height:26px;display:flex;'
            f'align-items:center;justify-content:center;font:bold 12px Arial;">'
            f"{number}</div>"
        ),
        icon_size=(26, 26),
        icon_anchor=(13, 13),
    )


def generate_route_map(
    coordinates: list[list[float]],
    start_label: str,
    finish_label: str,
    fuel_stops: list[dict],
    total_distance_miles: float | None = None,
    total_fuel_cost: float | None = None,
) -> str:
    if not coordinates:
        raise ValueError("Route coordinates are required to generate a map")

    start_lon, start_lat = coordinates[0]
    finish_lon, finish_lat = coordinates[-1]
    route_points = [(lat, lon) for lon, lat in coordinates]

    center_lat = (start_lat + finish_lat) / 2
    center_lon = (start_lon + finish_lon) / 2

    route_map = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=5,
        tiles="CartoDB positron",
        control_scale=True,
        prefer_canvas=True,
    )

    folium.PolyLine(
        route_points,
        color="#2563eb",
        weight=5,
        opacity=0.85,
        tooltip="Driving route",
    ).add_to(route_map)

    folium.Marker(
        [start_lat, start_lon],
        popup=folium.Popup(f"<b>Start</b><br>{start_label}", max_width=280),
        tooltip="Start",
        icon=folium.Icon(color="green", icon="ok-sign"),
    ).add_to(route_map)

    folium.Marker(
        [finish_lat, finish_lon],
        popup=folium.Popup(f"<b>Finish</b><br>{finish_label}", max_width=280),
        tooltip="Finish",
        icon=folium.Icon(color="red", icon="remove-sign"),
    ).add_to(route_map)

    for index, stop in enumerate(fuel_stops, start=1):
        folium.Marker(
            [stop["latitude"], stop["longitude"]],
            popup=folium.Popup(
                (
                    f"<b>Stop {index}: {stop['name']}</b><br>"
                    f"{stop['address']}<br>"
                    f"{stop['city']}, {stop['state']}<br>"
                    f"<b>${stop['price_per_gallon']:.3f}/gal</b><br>"
                    f"{stop['distance_from_start_miles']} mi from start"
                ),
                max_width=320,
            ),
            tooltip=f"Stop {index}: ${stop['price_per_gallon']:.3f}/gal",
            icon=_numbered_icon(index),
        ).add_to(route_map)

    route_map.fit_bounds(route_points, padding=(80, 80))
    Fullscreen(position="topright").add_to(route_map)
    _MapResizeFix().add_to(route_map)

    map_html = route_map.get_root().render()

    distance_line = (
        f"<p><b>Distance:</b> {total_distance_miles:.1f} mi</p>"
        if total_distance_miles is not None
        else ""
    )
    cost_line = (
        f"<p><b>Est. fuel cost:</b> ${total_fuel_cost:.2f}</p>"
        if total_fuel_cost is not None
        else ""
    )
    stops_line = f"<p><b>Fuel stops:</b> {len(fuel_stops)}</p>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Fuel Route Map</title>
    <style>
        * {{ box-sizing: border-box; }}
        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            font-family: Arial, Helvetica, sans-serif;
        }}
        #layout {{
            display: flex;
            flex-direction: column;
            width: 100%;
            height: 100vh;
        }}
        #header {{
            flex: 0 0 auto;
            padding: 12px 16px;
            background: #1e293b;
            color: #f8fafc;
            border-bottom: 1px solid #334155;
        }}
        #header h1 {{
            margin: 0 0 6px 0;
            font-size: 18px;
        }}
        #header p {{
            margin: 2px 0;
            font-size: 13px;
            color: #cbd5e1;
        }}
        #map-wrap {{
            flex: 1 1 auto;
            min-height: 0;
            position: relative;
        }}
        #map-wrap .folium-map,
        #map-wrap .leaflet-container {{
            width: 100% !important;
            height: 100% !important;
        }}
    </style>
</head>
<body>
    <div id="layout">
        <div id="header">
            <h1>Fuel Route Map</h1>
            <p><b>From:</b> {start_label} &nbsp;|&nbsp; <b>To:</b> {finish_label}</p>
            {distance_line}{cost_line}{stops_line}
        </div>
        <div id="map-wrap">
            {map_html}
        </div>
    </div>
</body>
</html>"""
