#!/usr/bin/env python3
"""
Weather CLI - Retrieves current temperature and humidity for Maple Valley, WA
Data source: National Weather Service API (api.weather.gov)
"""

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

# Maple Valley, WA coordinates
LATITUDE = 47.3748
LONGITUDE = -122.0450
LOCATION_NAME = "Maple Valley, WA"

BASE_URL = "https://api.weather.gov"
HEADERS = {
    "User-Agent": "(WeatherCLI/1.0, weather-cli@example.com)",
    "Accept": "application/geo+json",
}


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"Error: HTTP {e.code} fetching {url}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Could not connect to api.weather.gov - {e.reason}", file=sys.stderr)
        sys.exit(1)


def celsius_to_fahrenheit(c: float) -> float:
    return (c * 9 / 5) + 32


def get_observation() -> dict:
    # Step 1: Resolve grid point for our coordinates
    points_url = f"{BASE_URL}/points/{LATITUDE},{LONGITUDE}"
    points_data = fetch(points_url)
    stations_url = points_data["properties"]["observationStations"]

    # Step 2: Get nearest observation station (first in list)
    stations_data = fetch(stations_url)
    features = stations_data.get("features", [])
    if not features:
        print("Error: No observation stations found near this location.", file=sys.stderr)
        sys.exit(1)
    station_id = features[0]["properties"]["stationIdentifier"]
    station_name = features[0]["properties"]["name"]

    # Step 3: Get latest observation from that station
    obs_url = f"{BASE_URL}/stations/{station_id}/observations/latest"
    obs_data = fetch(obs_url)
    props = obs_data["properties"]

    return {
        "station_id": station_id,
        "station_name": station_name,
        "timestamp": props.get("timestamp"),
        "temperature_c": props["temperature"]["value"],
        "humidity_pct": props["relativeHumidity"]["value"],
        "temp_qc": props["temperature"]["qualityControl"],
        "humidity_qc": props["relativeHumidity"]["qualityControl"],
    }


def format_timestamp(ts: str) -> str:
    if not ts:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        local_dt = dt.astimezone()  # convert to local system time
        return local_dt.strftime("%Y-%m-%d %I:%M %p %Z")
    except ValueError:
        return ts


def main():
    print(f"Fetching weather for {LOCATION_NAME}...")

    obs = get_observation()

    temp_c = obs["temperature_c"]
    humidity = obs["humidity_pct"]

    temp_f = celsius_to_fahrenheit(temp_c) if temp_c is not None else None
    observed_at = format_timestamp(obs["timestamp"])

    print()
    print(f"Location : {LOCATION_NAME}")
    print(f"Station  : {obs['station_name']} ({obs['station_id']})")
    print(f"Observed : {observed_at}")
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
