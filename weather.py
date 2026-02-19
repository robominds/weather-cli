#!/usr/bin/env python3
"""
Weather CLI - Retrieves current temperature and humidity for a US city.
Data source: National Weather Service API (api.weather.gov)
Geocoding:   Open-Meteo Geocoding API (geocoding-api.open-meteo.com)

Usage:
  python3 weather.py                  # defaults to Maple Valley, WA
  python3 weather.py "Seattle, WA"
  python3 weather.py "Portland, OR"
  python3 weather.py Chicago
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime

DEFAULT_CITY = "Maple Valley, WA"

NWS_BASE = "https://api.weather.gov"
GEOCODE_BASE = "https://geocoding-api.open-meteo.com/v1"

HEADERS = {
    "User-Agent": "(WeatherCLI/1.0, weather-cli@example.com)",
    "Accept": "application/geo+json",
}


def fetch(url: str, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, headers=headers or HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"Error: HTTP {e.code} fetching {url}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Network error - {e.reason}", file=sys.stderr)
        sys.exit(1)


def geocode(city: str) -> tuple[float, float, str]:
    """Return (latitude, longitude, display_name) for a US city."""
    # Strip state suffix for the name query (Open-Meteo searches by city name)
    name = city.split(",")[0].strip()
    params = urllib.parse.urlencode({
        "name": name,
        "count": 10,
        "language": "en",
        "format": "json",
    })
    url = f"{GEOCODE_BASE}/search?{params}"
    data = fetch(url, headers={"User-Agent": "WeatherCLI/1.0", "Accept": "application/json"})
    results = [r for r in data.get("results", []) if r.get("country_code") == "US"]
    if not results:
        print(f"Error: Could not find '{city}' in the United States.", file=sys.stderr)
        sys.exit(1)

    # If a state was provided, narrow to matching admin1 (state name or abbreviation)
    if "," in city:
        state_hint = city.split(",", 1)[1].strip().lower()
        STATE_ABBREVS = {
            "al": "Alabama", "ak": "Alaska", "az": "Arizona", "ar": "Arkansas",
            "ca": "California", "co": "Colorado", "ct": "Connecticut", "de": "Delaware",
            "fl": "Florida", "ga": "Georgia", "hi": "Hawaii", "id": "Idaho",
            "il": "Illinois", "in": "Indiana", "ia": "Iowa", "ks": "Kansas",
            "ky": "Kentucky", "la": "Louisiana", "me": "Maine", "md": "Maryland",
            "ma": "Massachusetts", "mi": "Michigan", "mn": "Minnesota", "ms": "Mississippi",
            "mo": "Missouri", "mt": "Montana", "ne": "Nebraska", "nv": "Nevada",
            "nh": "New Hampshire", "nj": "New Jersey", "nm": "New Mexico", "ny": "New York",
            "nc": "North Carolina", "nd": "North Dakota", "oh": "Ohio", "ok": "Oklahoma",
            "or": "Oregon", "pa": "Pennsylvania", "ri": "Rhode Island", "sc": "South Carolina",
            "sd": "South Dakota", "tn": "Tennessee", "tx": "Texas", "ut": "Utah",
            "vt": "Vermont", "va": "Virginia", "wa": "Washington", "wv": "West Virginia",
            "wi": "Wisconsin", "wy": "Wyoming", "dc": "District of Columbia",
        }
        full_state = STATE_ABBREVS.get(state_hint, state_hint).lower()
        filtered = [r for r in results if r.get("admin1", "").lower() == full_state]
        if filtered:
            results = filtered

    r = results[0]
    parts = [r["name"]]
    if r.get("admin1"):
        parts.append(r["admin1"])
    parts.append("US")
    display = ", ".join(parts)
    return float(r["latitude"]), float(r["longitude"]), display


def get_observation(lat: float, lon: float) -> dict:
    # Step 1: Resolve NWS grid point for the coordinates
    points_data = fetch(f"{NWS_BASE}/points/{lat:.4f},{lon:.4f}")
    stations_url = points_data["properties"]["observationStations"]

    # Step 2: Get nearest observation station (first in the sorted list)
    stations_data = fetch(stations_url)
    features = stations_data.get("features", [])
    if not features:
        print("Error: No observation stations found near this location.", file=sys.stderr)
        sys.exit(1)
    station_id = features[0]["properties"]["stationIdentifier"]
    station_name = features[0]["properties"]["name"]

    # Step 3: Fetch the latest observation from that station
    obs_data = fetch(f"{NWS_BASE}/stations/{station_id}/observations/latest")
    props = obs_data["properties"]

    return {
        "station_id": station_id,
        "station_name": station_name,
        "timestamp": props.get("timestamp"),
        "temperature_c": props["temperature"]["value"],
        "humidity_pct": props["relativeHumidity"]["value"],
    }


def celsius_to_fahrenheit(c: float) -> float:
    return (c * 9 / 5) + 32


def format_timestamp(ts: str) -> str:
    if not ts:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%Y-%m-%d %I:%M %p %Z")
    except ValueError:
        return ts


def main():
    parser = argparse.ArgumentParser(
        description="Get current temperature and humidity for a US city.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  %(prog)s\n"
            "  %(prog)s 'Seattle, WA'\n"
            "  %(prog)s 'Portland, OR'\n"
            "  %(prog)s Chicago\n"
        ),
    )
    parser.add_argument(
        "city",
        nargs="?",
        default=DEFAULT_CITY,
        help=f"US city name (default: {DEFAULT_CITY!r})",
    )
    args = parser.parse_args()

    print(f"Looking up '{args.city}'...")
    lat, lon, display_name = geocode(args.city)

    print(f"Fetching weather data...")
    obs = get_observation(lat, lon)

    temp_c = obs["temperature_c"]
    humidity = obs["humidity_pct"]
    temp_f = celsius_to_fahrenheit(temp_c) if temp_c is not None else None

    print()
    print(f"Location : {display_name}")
    print(f"Station  : {obs['station_name']} ({obs['station_id']})")
    print(f"Observed : {format_timestamp(obs['timestamp'])}")
    print()

    if temp_f is not None:
        print(f"Temperature  : {temp_f:.1f}°F  ({temp_c:.1f}°C)")
    else:
        print("Temperature  : Data unavailable")

    if humidity is not None:
        print(f"Humidity     : {humidity:.1f}%")
    else:
        print("Humidity     : Data unavailable")


if __name__ == "__main__":
    main()
