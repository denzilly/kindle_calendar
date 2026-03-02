import json
import os
import urllib.request


def fetch_weather():
    """Fetch current temperature and today's max precipitation probability.

    Returns a dict with keys 'temp_c' (int) and 'precip_pct' (int),
    or None if LATITUDE/LONGITUDE are not configured or the request fails.
    """
    lat = os.environ.get("LATITUDE")
    lon = os.environ.get("LONGITUDE")
    if not lat or not lon:
        return None

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m"
        "&daily=precipitation_probability_max"
        "&forecast_days=1"
        "&timezone=auto"
    )

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        temp = data["current"]["temperature_2m"]
        precip = data["daily"]["precipitation_probability_max"][0]
        return {"temp_c": round(temp), "precip_pct": int(precip)}
    except Exception:
        return None
