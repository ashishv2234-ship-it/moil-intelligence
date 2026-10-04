from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.dependencies import current_user, require_roles, audit
from app.db.session import get_db
from app.models import BlastPlan, Mine, WeatherObservation
from app.services.weather_rules import FRESH_HOURS
from app.services.weather import fresh_forecast
router = APIRouter(prefix="/blasting", tags=["blasting"])
class BlastIn(BaseModel): mine_id: int; bench: str = Field(min_length=1, max_length=40); blast_date: date; planned_t: float = Field(gt=0)
class CompleteIn(BaseModel): actual_t: float = Field(ge=0)
class DelayIn(BaseModel): reason: str = Field(min_length=3, max_length=200)
def out(b: BlastPlan, wx: dict | None = None) -> dict:
    return {"weather": wx, "id": b.id, "mine_id": b.mine_id, "bench": b.bench, "blast_date": b.blast_date, "planned_t": b.planned_t,
            "actual_t": b.actual_t, "status": b.status, "delay_reason": b.delay_reason}
def _weather_for(db: Session, blasts: list[BlastPlan]) -> dict[int, dict]:
    """Weather check per blast id, for blasts still Scheduled from today to 7 days ahead.
    Today uses the latest live reading; later days use the stored daily forecast. No fresh data means no entry."""
    today = date.today(); res: dict[int, dict] = {}
    sched = [b for b in blasts if b.status == "Scheduled" and today <= b.blast_date <= today + timedelta(days=7)]
    for mid in {b.mine_id for b in sched}:
        w = db.scalar(select(WeatherObservation).where(WeatherObservation.mine_id == mid).order_by(WeatherObservation.id.desc()).limit(1))
        cur = w if w and (datetime.utcnow() - w.observed_at).total_seconds() <= FRESH_HOURS * 3600 else None
        fc = {x.day: x for x in fresh_forecast(db, mid)}
        for b in (x for x in sched if x.mine_id == mid):
            if b.blast_date == today and cur: info = {"kind": "current", "status": cur.blasting, "observed_at": cur.observed_at}
            elif b.blast_date > today and b.blast_date in fc:
                x = fc[b.blast_date]; info = {"kind": "forecast", "status": x.blasting, "observed_at": x.fetched_at, "rain_mm": x.rain_mm, "wind_kmh": x.wind_kmh}
            else: continue
            info["next_suitable"] = None if info["status"] == "Suitable" else next((d for d in sorted(fc) if d > b.blast_date and fc[d].blasting == "Suitable"), None)
            res[b.id] = info
    return res
def _get(db: Session, id: int) -> BlastPlan:
    b = db.get(BlastPlan, id)
    if not b: raise HTTPException(404, "Blast not found")
    return b
@router.get("")
def list_blasts(mine_id: int | None = None, status: str | None = None, db: Session = Depends(get_db), _=Depends(current_user)):
    q = select(BlastPlan).order_by(BlastPlan.blast_date.desc(), BlastPlan.id.desc()).limit(200)
    if mine_id: q = q.where(BlastPlan.mine_id == mine_id)
    if status: q = q.where(BlastPlan.status == status)
    rows = list(db.scalars(q)); wx = _weather_for(db, rows)
    return [out(b, wx.get(b.id)) for b in rows]
@router.post("", status_code=201)
def schedule(b: BlastIn, db: Session = Depends(get_db), u=Depends(require_roles("MINE_MANAGER"))):
    if not db.get(Mine, b.mine_id): raise HTTPException(404, "Mine not found")
    row = BlastPlan(**b.model_dump()); db.add(row); db.commit()
    audit(db, u.id, "blast.schedule", id=row.id, mine_id=b.mine_id); return out(row)
@router.post("/{id}/complete")
def complete(id: int, b: CompleteIn, db: Session = Depends(get_db), u=Depends(require_roles("MINE_MANAGER"))):
    row = _get(db, id)
    if row.status == "Completed": raise HTTPException(409, "This blast is already completed")
    row.status = "Completed"; row.actual_t = b.actual_t; row.delay_reason = None; db.commit()
    audit(db, u.id, "blast.complete", id=id, actual_t=b.actual_t); return out(row)
@router.post("/{id}/delay")
def delay(id: int, b: DelayIn, db: Session = Depends(get_db), u=Depends(require_roles("MINE_MANAGER"))):
    row = _get(db, id)
    if row.status != "Scheduled": raise HTTPException(409, f"Cannot delay a blast that is {row.status}")
    row.status = "Delayed"; row.delay_reason = b.reason; db.commit()
    audit(db, u.id, "blast.delay", id=id, reason=b.reason); return out(row)
