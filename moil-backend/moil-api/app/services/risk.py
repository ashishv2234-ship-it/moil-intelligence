from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import Mine, ProductionRecord, Equipment, ShortfallRisk, ActionRecommendation, WeatherObservation, RiskFactor, StockReading
from app.services.forecast import forecast
from app.services.weather_rules import weather_effect, weather_is_cause
from app.services.rain_rules import rain_effect, rain_is_cause
from app.services.satellite import rain_for_mine
from app.services.forecast_rules import forecast_effect
from app.services.weather import fresh_forecast
from app.services.stock_rules import cover_days, stock_effect, FRESH_DAYS
def level(pct: float) -> str: return "Critical" if pct > 12 else "High" if pct > 7 else "Medium" if pct > 3 else "Low"
def _fresh_weather(db: Session, mine_id: int) -> tuple[str | None, float | None]:
    """Latest weather observation for a mine: (blasting status, age in hours), or (None, None) if there is none."""
    w = db.scalar(select(WeatherObservation).where(WeatherObservation.mine_id == mine_id).order_by(WeatherObservation.id.desc()).limit(1))
    if not w: return None, None
    return w.blasting, max((datetime.utcnow() - w.observed_at).total_seconds() / 3600, 0)
def _coming_week(db: Session, mine_id: int) -> list[str]:
    """Blasting suitability for tomorrow to today+7 from the stored forecast (empty if there is no fresh forecast). Today is the live reading's job."""
    today = date.today()
    return [w.blasting for w in fresh_forecast(db, mine_id) if today < w.day <= today + timedelta(days=7)]
def _stock_cover(db: Session, m: Mine) -> tuple[float | None, int | None]:
    """Days of cover from the mine's newest stockpile reading and that reading's age in days, or (None, None) if there is none."""
    s = db.scalar(select(StockReading).where(StockReading.mine_id == m.id).order_by(StockReading.day.desc()).limit(1))
    if not s: return None, None
    return cover_days(s.closing_t, m.daily_target_t), (date.today() - s.day).days
def run_shortfall(db: Session, horizon: int = 30) -> list[ShortfallRisk]:
    created = []
    for m in db.scalars(select(Mine)):
        rows = db.scalars(select(ProductionRecord).where(ProductionRecord.mine_id == m.id).order_by(ProductionRecord.day)).all()
        if len(rows) < 28: continue
        fc = forecast([r.actual_t for r in rows], horizon, [r.day for r in rows])
        gap = sum(max(m.daily_target_t - f["forecast_t"], 0) for f in fc)
        pct = gap / (m.daily_target_t * horizon) * 100
        eq = db.scalars(select(Equipment).where(Equipment.mine_id == m.id)).all()
        avail = sum(e.availability_pct for e in eq) / len(eq) if eq else 90
        wx, age = _fresh_weather(db, m.id)
        rain_mm, rain_age = rain_for_mine(db, m.lat, m.lng)
        cause = "Equipment downtime" if avail < 82 else "Weather: blasting unsuitable" if weather_is_cause(wx, age, pct) else "Wet ground: heavy recent rain" if rain_is_cause(rain_mm, rain_age, pct) else "Production trend below plan"
        wx_pts, rain_pts, wk_pts = weather_effect(wx, age), rain_effect(rain_mm, rain_age), forecast_effect(_coming_week(db, m.id))
        cover, stock_age = _stock_cover(db, m); stock_pts = stock_effect(cover, stock_age)
        parts = [("Base", 35), ("Forecast shortfall", round(pct * 5)), ("Equipment availability", round(90 - avail)), ("Live weather", wx_pts), ("Recent rainfall", rain_pts), ("Coming week's weather", wk_pts), ("Low stockpile cover", stock_pts)]
        prob = max(min(97, round(35 + pct * 5 + (90 - avail) + wx_pts + rain_pts + wk_pts + stock_pts)), 5)
        r = ShortfallRisk(mine_id=m.id, level=level(pct), probability=prob, expected_shortfall_t=round(gap), main_cause=cause, confidence=round(max(60, 90 - abs(rows[-1].actual_t - fc[0]["forecast_t"]) / m.daily_target_t * 100)))
        db.add(r); db.flush(); created.append(r)
        extra = prob - sum(p for _, p in parts)  # rounding or the 5..97 limits
        db.add_all(RiskFactor(risk_id=r.id, label=l, points=p) for l, p in parts + ([("Rounding and limits (5 to 97)", extra)] if extra else []) if p or l == "Base")
        if r.level in ("High", "Critical"): db.add_all(recommend(r, m, avail, rain_mm, cover if stock_age is not None and 0 <= stock_age <= FRESH_DAYS else None))
    db.commit(); return created
def recommend(r: ShortfallRisk, m: Mine, avail: float, rain_mm: float | None = None, cover: float | None = None) -> list[ActionRecommendation]:
    """Transparent rule-based engine. Each rule states why it fired."""
    until = datetime.utcnow() + timedelta(days=7); recs = []
    if "downtime" in r.main_cause.lower():
        recs.append(ActionRecommendation(risk_id=r.id, action_type="Expedite maintenance", explanation=f"Fleet availability is {avail:.0f}%, below the 82% threshold.", recovery_t=round(r.expected_shortfall_t * .5), cost_inr_lakh=12, feasibility=.8, confidence=r.confidence - 5, valid_until=until))
        recs.append(ActionRecommendation(risk_id=r.id, action_type="Redeploy equipment", explanation="Move idle loaders or dumpers from mines with surplus availability.", recovery_t=round(r.expected_shortfall_t * .3), cost_inr_lakh=6, feasibility=.7, confidence=r.confidence - 10, valid_until=until))
    if "weather" in r.main_cause.lower():
        recs.append(ActionRecommendation(risk_id=r.id, action_type="Reschedule blasts to a dry window", explanation="Latest weather reading makes blasting unsuitable (heavy rain or strong wind). Move planned blasts to the next suitable day.", recovery_t=round(r.expected_shortfall_t * .4), cost_inr_lakh=2, feasibility=.7, confidence=r.confidence - 10, valid_until=until))
    if "wet ground" in r.main_cause.lower():
        recs.append(ActionRecommendation(risk_id=r.id, action_type="Pump out pits and service haul roads", explanation=f"About {rain_mm:.0f} mm of rain fell in the last 30 days at this mine (model data). Drain waterlogged benches and repair haul roads to restore loading and hauling rates.", recovery_t=round(r.expected_shortfall_t * .3), cost_inr_lakh=5, feasibility=.75, confidence=r.confidence - 10, valid_until=until))
    recs.append(ActionRecommendation(risk_id=r.id, action_type="Pre-build stockpile", explanation="Dispatch from stockpile to protect customer commitments while output recovers." + (f" The latest stockpile reading covers about {cover:.1f} days of target output." if cover is not None else ""), recovery_t=round(r.expected_shortfall_t * .25), cost_inr_lakh=4, feasibility=.9, confidence=r.confidence - 8, valid_until=until))
    return recs
