import folium


def generate_route_map(
    coordinates: list[list[float]],
    start_label: str,
    finish_label: str,
    fuel_stops: list[dict],
) -> str:
    if not coordinates:
        raise ValueError("Route coordinates are required to generate a map")

    start_lon, start_lat = coordinates[0]
    route_points = [(lat, lon) for lon, lat in coordinates]

    route_map = folium.Map(location=[start_lat, start_lon], zoom_start=5)
    folium.PolyLine(route_points, color="blue", weight=4, opacity=0.8, tooltip="Route").add_to(route_map)

    folium.Marker(
        [start_lat, start_lon],
        popup=start_label,
        tooltip="Start",
        icon=folium.Icon(color="green", icon="play"),
    ).add_to(route_map)

    finish_lon, finish_lat = coordinates[-1]
    folium.Marker(
        [finish_lat, finish_lon],
        popup=finish_label,
        tooltip="Finish",
        icon=folium.Icon(color="red", icon="stop"),
    ).add_to(route_map)

    for index, stop in enumerate(fuel_stops, start=1):
        folium.Marker(
            [stop["latitude"], stop["longitude"]],
            popup=(
                f"<b>{stop['name']}</b><br>"
                f"${stop['price_per_gallon']:.3f}/gal<br>"
                f"{stop['distance_from_start_miles']} mi from start"
            ),
            tooltip=f"Fuel stop {index}: ${stop['price_per_gallon']:.3f}/gal",
            icon=folium.Icon(color="orange", icon="info-sign"),
        ).add_to(route_map)

    return route_map._repr_html_()
