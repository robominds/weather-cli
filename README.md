# weather-cli

A command-line tool that retrieves current weather data for any US city using the National Weather Service API. Temperature and humidity are shown by default; any combination of available properties can be requested via the `-p` flag.

## Requirements

- Python 3.10+
- No third-party packages — uses only the standard library

## Usage

```bash
# Default: Maple Valley, WA — shows temperature and humidity
python3 weather.py

# Specify a city with optional state
python3 weather.py "Seattle, WA"
python3 weather.py "Portland, OR"
python3 weather.py Chicago

# Request specific properties with -p / --properties
python3 weather.py "Seattle, WA" -p wind wind-direction pressure visibility
python3 weather.py "Denver, CO" -p temperature humidity dewpoint wind wind-chill

# List all available properties
python3 weather.py --list
```

## Available Properties

| Property | Description |
|----------|-------------|
| `temperature` | Temperature °F / °C *(default)* |
| `humidity` | Relative humidity % *(default)* |
| `dewpoint` | Dewpoint °F / °C |
| `wind-chill` | Wind chill °F / °C |
| `heat-index` | Heat index °F / °C |
| `wind` | Wind speed mph / km/h |
| `wind-direction` | Wind direction (compass + degrees) |
| `wind-gust` | Wind gust mph / km/h |
| `pressure` | Barometric pressure inHg / hPa |
| `sea-pressure` | Sea level pressure inHg / hPa |
| `visibility` | Visibility mi / km |
| `max-temp` | Max temperature last 24h |
| `min-temp` | Min temperature last 24h |
| `precipitation` | Precipitation last 3h in / mm |

## Example Output

```
Looking up 'Denver, CO'...
Fetching weather data...

Location : Denver, Colorado, US
Station  : Buckley Space Force Base (KBKF)
Observed : 2026-02-19 07:58 AM PST

Temperature  :  25.0°F  (-3.9°C)
Humidity     :  70.9%
Dewpoint     :  16.9°F  (-8.4°C)
Wind Speed   :  11.4 mph  (18.4 km/h)
Wind Chill   :  14.3°F  (-9.9°C)
```

## How It Works

1. **Geocoding** — The city name is resolved to latitude/longitude via the [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api). If a state abbreviation is provided (e.g. `WA`), it is used to disambiguate cities that appear in multiple states.

2. **Grid lookup** — The coordinates are sent to the [NWS Points API](https://www.weather.gov/documentation/services-web-api) (`/points/{lat},{lon}`) to identify the nearest forecast office and observation station list.

3. **Observation** — The latest observation is fetched from the nearest station and the requested properties are displayed.

## Data Sources

| Source | Purpose | Cost |
|--------|---------|------|
| [api.weather.gov](https://www.weather.gov/documentation/services-web-api) | Current weather observations | Free, no key |
| [geocoding-api.open-meteo.com](https://open-meteo.com/en/docs/geocoding-api) | City name → coordinates | Free, no key |

## Authors

- Mark Castelluccio
- [Claude Sonnet 4.6](https://www.anthropic.com/claude) (Anthropic) — AI pair programmer
