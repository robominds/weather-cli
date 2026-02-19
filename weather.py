#!/usr/bin/env python3
"""
Weather CLI - Retrieves current weather data for a US city.
Data source: National Weather Service API (api.weather.gov)
Geocoding:   Open-Meteo Geocoding API (geocoding-api.open-meteo.com)

Usage:
  python3 weather.py                              # defaults to Maple Valley, WA
  python3 weather.py "Seattle, WA"
  python3 weather.py Chicago -p wind pressure
  python3 weather.py --list                       # show available properties
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime

DEFAULT_CITY = "Maple Valley, WA"
DEFAULT_PROPERTIES = ["temperature", "humidity"]

NWS_BASE = "https://api.weather.gov"
GEOCODE_BASE = "https://geocoding-api.open-meteo.com/v1"

HEADERS = {
    "User-Agent": "(WeatherCLI/1.0, weather-cli@example.com)",
    "Accept": "application/geo+json",
}

# ---------------------------------------------------------------------------
# Unit conversions
# ---------------------------------------------------------------------------

def _c_to_f(c):
    return (c * 9 / 5) + 32

def _kmh_to_mph(kmh):
    return kmh * 0.621371

def _pa_to_inhg(pa):
    return pa * 0.000295299

def _m_to_mi(m):
    return m * 0.000621371

def _degrees_to_compass(deg):
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return directions[round(deg / 22.5) % 16]

# ---------------------------------------------------------------------------
# Property registry
# Each entry: api_key, label, format_fn, json_fn
# ---------------------------------------------------------------------------

def _temp_fmt(v):
    return f"{_c_to_f(v):.1f}°F  ({v:.1f}°C)"

def _wind_speed_fmt(v):
    return f"{_kmh_to_mph(v):.1f} mph  ({v:.1f} km/h)"

def _pressure_fmt(v):
    return f"{_pa_to_inhg(v):.2f} inHg  ({v / 100:.1f} hPa)"

def _temp_json(v):
    return {"fahrenheit": round(_c_to_f(v), 1), "celsius": round(v, 1)}

def _wind_speed_json(v):
    return {"mph": round(_kmh_to_mph(v), 1), "kmh": round(v, 1)}

def _pressure_json(v):
    return {"inhg": round(_pa_to_inhg(v), 2), "hpa": round(v / 100, 1)}

PROPERTIES = {
    "temperature": {
        "api_key": "temperature",
        "label": "Temperature",
        "format": _temp_fmt,
        "json": _temp_json,
    },
    "humidity": {
        "api_key": "relativeHumidity",
        "label": "Humidity",
        "format": lambda v: f"{v:.1f}%",
        "json": lambda v: {"percent": round(v, 1)},
    },
    "dewpoint": {
        "api_key": "dewpoint",
        "label": "Dewpoint",
        "format": _temp_fmt,
        "json": _temp_json,
    },
    "wind-chill": {
        "api_key": "windChill",
        "label": "Wind Chill",
        "format": _temp_fmt,
        "json": _temp_json,
    },
    "heat-index": {
        "api_key": "heatIndex",
        "label": "Heat Index",
        "format": _temp_fmt,
        "json": _temp_json,
    },
    "wind": {
        "api_key": "windSpeed",
        "label": "Wind Speed",
        "format": _wind_speed_fmt,
        "json": _wind_speed_json,
    },
    "wind-direction": {
        "api_key": "windDirection",
        "label": "Wind Direction",
        "format": lambda v: f"{_degrees_to_compass(v)}  ({v:.0f}°)",
        "json": lambda v: {"compass": _degrees_to_compass(v), "degrees": round(v)},
    },
    "wind-gust": {
        "api_key": "windGust",
        "label": "Wind Gust",
        "format": _wind_speed_fmt,
        "json": _wind_speed_json,
    },
    "pressure": {
        "api_key": "barometricPressure",
        "label": "Pressure",
        "format": _pressure_fmt,
        "json": _pressure_json,
    },
    "sea-pressure": {
        "api_key": "seaLevelPressure",
        "label": "Sea Level Pressure",
        "format": _pressure_fmt,
        "json": _pressure_json,
    },
    "visibility": {
        "api_key": "visibility",
        "label": "Visibility",
        "format": lambda v: f"{_m_to_mi(v):.1f} mi  ({v / 1000:.1f} km)",
        "json": lambda v: {"miles": round(_m_to_mi(v), 1), "km": round(v / 1000, 1)},
    },
    "max-temp": {
        "api_key": "maxTemperatureLast24Hours",
        "label": "Max Temp (24h)",
        "format": _temp_fmt,
        "json": _temp_json,
    },
    "min-temp": {
        "api_key": "minTemperatureLast24Hours",
        "label": "Min Temp (24h)",
        "format": _temp_fmt,
        "json": _temp_json,
    },
    "precipitation": {
        "api_key": "precipitationLast3Hours",
        "label": "Precipitation (3h)",
        "format": lambda v: f"{v * 0.0393701:.2f} in  ({v:.1f} mm)",
        "json": lambda v: {"inches": round(v * 0.0393701, 2), "mm": round(v, 1)},
    },
}

# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------

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


def geocode(city: str) -> tuple[float, float, str]:
    """Return (latitude, longitude, display_name) for a US city."""
    name = city.split(",")[0].strip()
    params = urllib.parse.urlencode({"name": name, "count": 10, "language": "en", "format": "json"})
    url = f"{GEOCODE_BASE}/search?{params}"
    data = fetch(url, headers={"User-Agent": "WeatherCLI/1.0", "Accept": "application/json"})
    results = [r for r in data.get("results", []) if r.get("country_code") == "US"]
    if not results:
        print(f"Error: Could not find '{city}' in the United States.", file=sys.stderr)
        sys.exit(1)

    if "," in city:
        state_hint = city.split(",", 1)[1].strip().lower()
        full_state = STATE_ABBREVS.get(state_hint, state_hint).lower()
        filtered = [r for r in results if r.get("admin1", "").lower() == full_state]
        if filtered:
            results = filtered

    r = results[0]
    parts = [r["name"]]
    if r.get("admin1"):
        parts.append(r["admin1"])
    parts.append("US")
    return float(r["latitude"]), float(r["longitude"]), ", ".join(parts)

# ---------------------------------------------------------------------------
# NWS observations
# ---------------------------------------------------------------------------

def get_observation(lat: float, lon: float) -> tuple[str, str, dict]:
    """Return (station_name, station_id, props dict) for the nearest station."""
    points_data = fetch(f"{NWS_BASE}/points/{lat:.4f},{lon:.4f}")
    stations_url = points_data["properties"]["observationStations"]

    stations_data = fetch(stations_url)
    features = stations_data.get("features", [])
    if not features:
        print("Error: No observation stations found near this location.", file=sys.stderr)
        sys.exit(1)
    station_id = features[0]["properties"]["stationIdentifier"]
    station_name = features[0]["properties"]["name"]

    obs_data = fetch(f"{NWS_BASE}/stations/{station_id}/observations/latest")
    return station_name, station_id, obs_data["properties"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def format_timestamp(ts: str) -> str:
    if not ts:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%Y-%m-%d %I:%M %p %Z")
    except ValueError:
        return ts

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Get current weather data for a US city.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  %(prog)s\n"
            "  %(prog)s 'Seattle, WA'\n"
            "  %(prog)s Chicago -p wind wind-direction pressure\n"
            "  %(prog)s 'Denver, CO' -p temperature humidity dewpoint wind\n"
            "  %(prog)s --list\n"
        ),
    )
    parser.add_argument(
        "city",
        nargs="?",
        default=DEFAULT_CITY,
        help=f"US city name (default: {DEFAULT_CITY!r})",
    )
    parser.add_argument(
        "-p", "--properties",
        nargs="+",
        metavar="PROP",
        default=DEFAULT_PROPERTIES,
        help=(
            f"one or more of: {', '.join(PROPERTIES)}. "
            f"Defaults to: {', '.join(DEFAULT_PROPERTIES)}."
        ),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list all available properties and exit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="output results as JSON (progress messages go to stderr)",
    )
    args = parser.parse_args()

    if args.list:
        if args.json:
            print(json.dumps({
                "default": DEFAULT_PROPERTIES,
                "properties": {
                    name: {"label": meta["label"], "default": name in DEFAULT_PROPERTIES}
                    for name, meta in PROPERTIES.items()
                },
            }, indent=2))
        else:
            max_len = max(len(k) for k in PROPERTIES)
            print("Available properties:")
            for name, meta in PROPERTIES.items():
                marker = " *" if name in DEFAULT_PROPERTIES else ""
                print(f"  {name:<{max_len}}  {meta['label']}{marker}")
            print("\n* default")
        return

    # Validate requested properties
    unknown = [p for p in args.properties if p not in PROPERTIES]
    if unknown:
        print(f"Error: Unknown {'property' if len(unknown) == 1 else 'properties'}: {', '.join(unknown)}", file=sys.stderr)
        print(f"Run with --list to see available properties.", file=sys.stderr)
        sys.exit(1)

    log = (lambda msg: print(msg, file=sys.stderr)) if args.json else print

    log(f"Looking up '{args.city}'...")
    lat, lon, display_name = geocode(args.city)

    log("Fetching weather data...")
    station_name, station_id, obs_props = get_observation(lat, lon)

    # Collect values for all requested properties
    prop_values = {}
    for prop_name in args.properties:
        meta = PROPERTIES[prop_name]
        raw = obs_props.get(meta["api_key"], {})
        prop_values[prop_name] = raw.get("value") if isinstance(raw, dict) else None

    if args.json:
        ts = obs_props.get("timestamp")
        output = {
            "location": display_name,
            "station": {"name": station_name, "id": station_id},
            "observed": ts,
            "properties": {
                name: (PROPERTIES[name]["json"](v) if v is not None else None)
                for name, v in prop_values.items()
            },
        }
        print(json.dumps(output, indent=2))
    else:
        print()
        print(f"Location : {display_name}")
        print(f"Station  : {station_name} ({station_id})")
        print(f"Observed : {format_timestamp(obs_props.get('timestamp'))}")
        print()

        label_width = max(len(PROPERTIES[p]["label"]) for p in args.properties)
        for prop_name in args.properties:
            meta = PROPERTIES[prop_name]
            value = prop_values[prop_name]
            label = meta["label"]
            if value is not None:
                print(f"{label:<{label_width}}  :  {meta['format'](value)}")
            else:
                print(f"{label:<{label_width}}  :  Data unavailable")


if __name__ == "__main__":
    main()
