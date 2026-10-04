"""Open-Meteo grid adapter: free, no API key, standard library only.
Gives three layers over the mining belt: rainfall (last 30 days), soil moisture and surface temperature.
These are model/reanalysis values (not raw satellite pixels). NDVI has no key-free source, so it comes from a CSV file."""
import json, urllib.parse, urllib.request
URL = "https://api.open-meteo.com/v1/forecast"
CELL_DEG = 0.25
# Cell centres covering the Nagpur-Balaghat-Chhindwara manganese belt (6 x 8 = 48 points).
POINTS = [(round(21.0 + 0.25 * i, 2), round(79.0 + 0.25 * j, 2)) for i in range(6) for j in range(8)]

def parse(data, points) -> list[dict]:
    """Turn the API answer into one record per point. A point missing a value simply lacks that key."""
    items = data if isinstance(data, list) else [data]
    if len(items) != len(points): raise ValueError("Unexpected answer from the weather service")
    out = []
    for (lat, lng), d in zip(points, items):
        rec = {"lat": lat, "lng": lng}
        daily = d.get("daily") or {}; days = daily.get("time") or []; rain = daily.get("precipitation_sum") or []
        past = [v for v in rain[:-1] if v is not None]          # last entry is today (partly forecast): leave it out
        if len(past) >= 25 and len(days) >= 2:
            rec["rain"] = round(sum(past), 1); rec["as_of"] = days[-2]
        hourly = d.get("hourly") or {}
        for key, name, scale in (("soil_moisture_0_to_7cm", "soil", 100.0), ("soil_temperature_0cm", "lst", 1.0)):
            vals = [v for v in (hourly.get(key) or [])[-48:-24] if v is not None]   # yesterday, a complete past day
            if len(vals) >= 12: rec[name] = round(sum(vals) / len(vals) * scale, 2)
        if len(rec) > 2: out.append(rec)
    return out

def fetch(points=POINTS, timeout: int = 30) -> list[dict]:
    q = urllib.parse.urlencode({"latitude": ",".join(str(p[0]) for p in points), "longitude": ",".join(str(p[1]) for p in points),
                                "hourly": "soil_moisture_0_to_7cm,soil_temperature_0cm", "daily": "precipitation_sum",
                                "past_days": 30, "forecast_days": 1, "timezone": "auto"})
    with urllib.request.urlopen(f"{URL}?{q}", timeout=timeout) as r: return parse(json.load(r), points)
