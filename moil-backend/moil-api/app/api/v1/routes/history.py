"""Shortfall history: every risk run is already saved, so this just reads them back, plus the 'why' behind one run's probability."""
from datetime import date, datetime, time, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.dependencies import current_user
from app.db.session import get_db
from app.models import Mine, ShortfallRisk, RiskFactor, Equipment, EquipmentSnapshot
from app.services.period import check_range
router = APIRouter(tags=["risks"])
@router.get("/risks/history")
def history(mine_id: int, limit: int = Query(30, ge=1, le=200), db: Session = Depends(get_db), _=Depends(current_user)):
    """The last `limit` risk runs for one mine, oldest first (so a chart reads left to right)."""
    if not db.get(Mine, mine_id): raise HTTPException(404, "Mine not found")
    rows = db.scalars(select(ShortfallRisk).where(ShortfallRisk.mine_id == mine_id).order_by(ShortfallRisk.id.desc()).limit(limit)).all()
    return [{"id": r.id, "created_at": r.created_at, "level": r.level, "probability": r.probability, "expected_shortfall_t": r.expected_shortfall_t, "main_cause": r.main_cause} for r in reversed(rows)]
@router.get("/risks/shortfall/{risk_id}/factors")
def factors(risk_id: int, db: Session = Depends(get_db), _=Depends(current_user)):
    """What added to (or took from) this run's probability. Empty for runs made before this was recorded."""
    if not db.get(ShortfallRisk, risk_id): raise HTTPException(404, "Risk not found")
    return [{"label": f.label, "points": f.points} for f in db.scalars(select(RiskFactor).where(RiskFactor.risk_id == risk_id).order_by(RiskFactor.id))]
@router.get("/equipment/history", tags=["equipment"])
def equipment_history(mine_id: int | None = None, days: int = Query(30, ge=1, le=365), date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db), _=Depends(current_user)):
    """One point per real telematics import inside the period: the average of the machines IN THAT FILE (a file may hold only some machines)."""
    try: rng = check_range(date_from, date_to)
    except ValueError as e: raise HTTPException(422, str(e))
    if mine_id and not db.get(Mine, mine_id): raise HTTPException(404, "Mine not found")
    d1 = rng[1] if rng else date.today(); d0 = rng[0] if rng else d1 - timedelta(days=days - 1)
    S = EquipmentSnapshot
    q = select(S).join(Equipment, Equipment.id == S.equipment_id).where(S.taken_at >= datetime.combine(d0, time.min), S.taken_at <= datetime.combine(d1, time.max)).order_by(S.taken_at, S.id).limit(20000)
    if mine_id: q = q.where(Equipment.mine_id == mine_id)
    groups: dict = {}
    for r in db.scalars(q): groups.setdefault(r.upload_id, []).append(r)
    avg = lambda xs: round(sum(xs) / len(xs), 1)
    return {"from": d0, "to": d1, "points": [{"upload_id": k, "taken_at": g[0].taken_at, "machines": len(g), "avg_availability": avg([x.availability_pct for x in g]), "avg_health": avg([x.health_score for x in g]),
                                             "breakdowns": sum(1 for x in g if x.status == "Breakdown"), "downtime_hrs": round(sum(x.downtime_hrs for x in g))} for k, g in groups.items()]}
