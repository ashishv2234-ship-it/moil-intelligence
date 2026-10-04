"""Open-Meteo adapter: free, no API key. Uses only the standard library."""
import json, urllib.parse, urllib.request
URL = "https://api.open-meteo.com/v1/forecast"
def parse(d: dict) -> dict:
    c = d["current"]; day = (d.get("daily") or {}).get("precipitation_sum") or [0]
    return {"temp_c": float(c["temperature_2m"]), "humidity_pct": float(c["relative_humidity_2m"]), "wind_kmh": float(c["wind_speed_10m"]),
            "rain_now_mm": float(c["precipitation"]), "rain_today_mm": float(day[0] or 0)}
def fetch(lat: float, lng: float, timeout: int = 8) -> dict:
    q = urllib.parse.urlencode({"latitude": lat, "longitude": lng, "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
                                "daily": "precipitation_sum", "forecast_days": 1, "timezone": "auto"})
    with urllib.request.urlopen(f"{URL}?{q}", timeout=timeout) as r: return parse(json.load(r))

def parse_forecast(d: dict) -> list[dict]:
    """Daily forecast -> [{day, rain_mm, wind_kmh}]. Days with a missing value are skipped."""
    daily = d["daily"]; out = []
    for t, r, w in zip(daily.get("time") or [], daily.get("precipitation_sum") or [], daily.get("wind_speed_10m_max") or []):
        if r is None or w is None: continue
        out.append({"day": t, "rain_mm": float(r), "wind_kmh": float(w)})
    return out
def fetch_forecast(lat: float, lng: float, days: int = 8, timeout: int = 8) -> list[dict]:
    q = urllib.parse.urlencode({"latitude": lat, "longitude": lng, "daily": "precipitation_sum,wind_speed_10m_max", "forecast_days": days, "timezone": "auto"})
    with urllib.request.urlopen(f"{URL}?{q}", timeout=timeout) as r: return parse_forecast(json.load(r))
