from datetime import datetime, date, timedelta
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from app.integrations.weather.openmeteo import fetch as open_meteo, fetch_forecast as open_meteo_forecast
from app.models import Mine, WeatherObservation, WeatherForecast, DataSource
from app.services.weather_rules import forecast_status, FORECAST_FRESH_HOURS
def blasting_status(w: dict) -> str:
    """Transparent rules. Heavy or current rain and strong wind make blasting unsafe or hard to control."""
    if w["rain_now_mm"] >= 2 or w["rain_today_mm"] >= 10 or w["wind_kmh"] >= 40: return "Unsuitable"
    if w["rain_today_mm"] >= 3 or w["wind_kmh"] >= 25: return "Caution"
    return "Suitable"
def sync_weather(db: Session, fetch=open_meteo) -> dict:
    ok, failed = 0, []
    for m in db.scalars(select(Mine)).all():
        try:
            w = fetch(m.lat, m.lng)
            db.add(WeatherObservation(mine_id=m.id, blasting=blasting_status(w), **w)); ok += 1
        except Exception:  # offline, timeout or an unexpected response: report it, never crash
            failed.append(m.name)
    ds = db.scalar(select(DataSource).where(DataSource.name.ilike("%weather%")))
    if ds:
        ds.last_sync = datetime.utcnow(); ds.records += ok
        ds.status = "Success" if not failed else ("Failed" if ok == 0 else "Warning")
    db.commit(); return {"updated": ok, "failed": failed}
def latest(db: Session) -> list[dict]:
    names = {m.id: m.name for m in db.scalars(select(Mine))}; seen, out = set(), []
    for w in db.scalars(select(WeatherObservation).order_by(WeatherObservation.id.desc())):
        if w.mine_id in seen or w.mine_id not in names: continue
        seen.add(w.mine_id)
        out.append({"mine_id": w.mine_id, "mine_name": names[w.mine_id], "observed_at": w.observed_at, "temp_c": w.temp_c, "humidity_pct": w.humidity_pct,
                    "wind_kmh": w.wind_kmh, "rain_now_mm": w.rain_now_mm, "rain_today_mm": w.rain_today_mm, "blasting": w.blasting})
    return sorted(out, key=lambda r: r["mine_name"])

def sync_forecast(db: Session, fetch=open_meteo_forecast) -> dict:
    """Replace each mine's stored daily forecast. A mine whose request fails keeps its old forecast."""
    ok, failed = 0, []
    for m in db.scalars(select(Mine)).all():
        try: pts = fetch(m.lat, m.lng)
        except Exception: failed.append(m.name); continue
        if not pts: failed.append(m.name); continue
        db.execute(delete(WeatherForecast).where(WeatherForecast.mine_id == m.id))
        for p in pts: db.add(WeatherForecast(mine_id=m.id, day=date.fromisoformat(p["day"]), rain_mm=p["rain_mm"], wind_kmh=p["wind_kmh"], blasting=forecast_status(p["rain_mm"], p["wind_kmh"])))
        ok += 1
    db.commit(); return {"updated": ok, "failed": failed}
def fresh_forecast(db: Session, mine_id: int) -> list[WeatherForecast]:
    """Stored forecast days from today on, only if the forecast was fetched in the last FORECAST_FRESH_HOURS."""
    since = datetime.utcnow() - timedelta(hours=FORECAST_FRESH_HOURS)
    return list(db.scalars(select(WeatherForecast).where(WeatherForecast.mine_id == mine_id, WeatherForecast.day >= date.today(), WeatherForecast.fetched_at >= since).order_by(WeatherForecast.day)))
def forecast_all(db: Session) -> list[dict]:
    out = []
    for m in db.scalars(select(Mine).order_by(Mine.name)):
        rows = fresh_forecast(db, m.id)
        if rows: out.append({"mine_id": m.id, "mine_name": m.name, "fetched_at": rows[0].fetched_at, "days": [{"day": w.day, "rain_mm": w.rain_mm, "wind_kmh": w.wind_kmh, "blasting": w.blasting} for w in rows]})
    return out
