# weather-cli

A command-line tool that retrieves current temperature and humidity for any US city using the National Weather Service API.

## Requirements

- Python 3.10+
- No third-party packages — uses only the standard library

## Usage

```bash
# Default: Maple Valley, WA
python3 weather.py

# Specify a city with optional state
python3 weather.py "Seattle, WA"
python3 weather.py "Portland, OR"
python3 weather.py Chicago
```

## Example Output

```
Looking up 'Maple Valley, WA'...
Fetching weather data...

Location : Maple Valley, Washington, US
Station  : EW6690 Maple Valley (E6690)
Observed : 2026-02-18 10:19 PM PST

Temperature  : 32.0°F  (0.0°C)
Humidity     : 95.9%
```

## How It Works

1. **Geocoding** — The city name is resolved to latitude/longitude via the [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api). If a state abbreviation is provided (e.g. `WA`), it is used to disambiguate cities that appear in multiple states.

2. **Grid lookup** — The coordinates are sent to the [NWS Points API](https://www.weather.gov/documentation/services-web-api) (`/points/{lat},{lon}`) to identify the nearest forecast office and observation station list.

3. **Observation** — The latest observation is fetched from the nearest station and the temperature (°F/°C) and relative humidity are displayed.

## Data Sources

| Source | Purpose | Cost |
|--------|---------|------|
| [api.weather.gov](https://www.weather.gov/documentation/services-web-api) | Current weather observations | Free, no key |
| [geocoding-api.open-meteo.com](https://open-meteo.com/en/docs/geocoding-api) | City name → coordinates | Free, no key |

## Author

Mark Castelluccio
