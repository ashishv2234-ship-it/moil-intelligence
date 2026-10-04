from datetime import datetime, timedelta, date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from app.core.dependencies import current_user, require_roles, audit
from app.db.session import get_db
from app.models import Mine, ProductionRecord, ShortfallRisk, ActionRecommendation, Equipment, DataSource, AuditLog, User, RiskOwner, StockReading
from app.schemas import MineIn, MineOut, ProductionIn, RiskOut, RecOut, StatusIn, AssignIn
from app.services.forecast import forecast, forecast_with_info, forecast_full
from app.services.risk import run_shortfall
from app.services.period import check_range
router = APIRouter()
def paged(db, q, page, size): total = db.scalar(select(func.count()).select_from(q.subquery())); return {"items": db.scalars(q.limit(size).offset((page - 1) * size)).all(), "total": total, "page": page, "size": size}
P = lambda: (Query(1, ge=1), Query(25, ge=1, le=200))
@router.get("/mines", tags=["mines"])
def mines(page: int = Query(1, ge=1), size: int = Query(25, ge=1, le=200), db: Session = Depends(get_db), _=Depends(current_user)):
    r = paged(db, select(Mine).order_by(Mine.name), page, size); r["items"] = [MineOut.model_validate(m) for m in r["items"]]; return r
@router.post("/mines", response_model=MineOut, status_code=201, tags=["mines"])
def create_mine(b: MineIn, db: Session = Depends(get_db), u=Depends(require_roles("MINE_MANAGER"))):
    m = Mine(**b.model_dump()); db.add(m); db.commit(); audit(db, u.id, "mine.create", name=m.name); return m
@router.post("/production/records", status_code=201, tags=["production"])
def add_record(b: ProductionIn, db: Session = Depends(get_db), u=Depends(require_roles("DATA_ENGINEER", "MINE_MANAGER"))):
    if b.day > datetime.utcnow(): raise HTTPException(422, "Date is in the future")
    if not db.get(Mine, b.mine_id): raise HTTPException(404, "Mine not found")
    db.add(ProductionRecord(mine_id=b.mine_id, day=b.day.date(), planned_t=b.planned_t, actual_t=b.actual_t)); db.commit(); return {"ok": True}
@router.get("/production/forecast", tags=["production"])
def get_forecast(mine_id: int, horizon: int = Query(30, ge=1, le=90), db: Session = Depends(get_db), _=Depends(current_user)):
    rows = db.scalars(select(ProductionRecord).where(ProductionRecord.mine_id == mine_id).order_by(ProductionRecord.day)).all()
    try: res = forecast_full([r.actual_t for r in rows], horizon, [r.day for r in rows])
    except ValueError as e: raise HTTPException(422, str(e))
    return {"mine_id": mine_id, "model": "seasonal-naive+MA baseline" + (" with monthly seasonal adjustment" if res["seasonal"] else ""), "label": "AI-generated forecast", "outliers_replaced": res["capped"], "seasonal_adjusted": res["seasonal"], "points": res["points"]}
@router.post("/risks/shortfall/run", tags=["risks"])
def run_risks(db: Session = Depends(get_db), u=Depends(require_roles("PLANNING_ENGINEER", "MINE_MANAGER"))):
    created = run_shortfall(db); audit(db, u.id, "risk.run", count=len(created)); return {"created": len(created)}
@router.get("/risks/shortfall", response_model=list[RiskOut], tags=["risks"])
def risks(level: str | None = None, db: Session = Depends(get_db), _=Depends(current_user)):
    q = select(ShortfallRisk).order_by(ShortfallRisk.created_at.desc(), ShortfallRisk.id.desc())
    out = []
    owners = {mid: name for mid, name in db.execute(select(RiskOwner.mine_id, User.name).join(User, User.id == RiskOwner.user_id))}  # risk owner per mine
    for r in db.scalars(q.where(ShortfallRisk.level == level) if level else q).all():
        rec = db.scalars(select(ActionRecommendation).where(ActionRecommendation.risk_id == r.id).order_by(ActionRecommendation.recovery_t.desc())).first()
        out.append(RiskOut.model_validate(r).model_copy(update={"action": rec.action_type if rec else None, "owner": owners.get(r.mine_id) or (rec.owner if rec else None)}))
    return out
@router.post("/risks/shortfall/{risk_id}/acknowledge", response_model=RiskOut, tags=["risks"])
def acknowledge(risk_id: int, db: Session = Depends(get_db), u=Depends(require_roles("MINE_MANAGER", "PLANNING_ENGINEER"))):
    r = db.get(ShortfallRisk, risk_id)
    if not r: raise HTTPException(404, "Risk not found")
    if r.status != "Open": raise HTTPException(409, f"Risk is already {r.status}")
    r.status = "In Progress"; db.commit(); audit(db, u.id, "risk.acknowledge", id=risk_id); return r
@router.post("/risks/shortfall/{risk_id}/resolve", response_model=RiskOut, tags=["risks"])
def resolve(risk_id: int, db: Session = Depends(get_db), u=Depends(require_roles("MINE_MANAGER", "PLANNING_ENGINEER"))):
    r = db.get(ShortfallRisk, risk_id)
    if not r: raise HTTPException(404, "Risk not found")
    if r.status == "Open": raise HTTPException(409, "Acknowledge this risk before resolving it")
    if r.status != "In Progress": raise HTTPException(409, f"Risk is already {r.status}")
    r.status = "Resolved"; db.commit(); audit(db, u.id, "risk.resolve", id=risk_id); return r
@router.get("/production/records", tags=["production"])
def records(mine_id: int, days: int = Query(90, ge=1, le=400), db: Session = Depends(get_db), _=Depends(current_user)):
    rows = db.scalars(select(ProductionRecord).where(ProductionRecord.mine_id == mine_id).order_by(ProductionRecord.day.desc()).limit(days)).all()
    return [{"day": str(r.day), "planned_t": r.planned_t, "actual_t": r.actual_t} for r in reversed(rows)]
@router.get("/actions/recommendations", response_model=list[RecOut], tags=["actions"])
def recs(db: Session = Depends(get_db), _=Depends(current_user)): return db.scalars(select(ActionRecommendation)).all()
def _rec(db, id):
    r = db.get(ActionRecommendation, id)
    if not r: raise HTTPException(404, "Recommendation not found")
    return r
FLOW = {"Proposed": {"Approved", "Rejected"}, "Approved": {"In Progress"}, "In Progress": {"Completed"}}
@router.post("/actions/recommendations/{id}/approve", response_model=RecOut, tags=["actions"])
def approve(id: int, db: Session = Depends(get_db), u=Depends(require_roles("MINE_MANAGER"))): return _move(db, u, id, "Approved")
@router.post("/actions/recommendations/{id}/reject", response_model=RecOut, tags=["actions"])
def reject(id: int, db: Session = Depends(get_db), u=Depends(require_roles("MINE_MANAGER"))): return _move(db, u, id, "Rejected")
@router.patch("/actions/recommendations/{id}/status", response_model=RecOut, tags=["actions"])
def status(id: int, b: StatusIn, db: Session = Depends(get_db), u=Depends(require_roles("MINE_MANAGER", "PLANNING_ENGINEER"))): return _move(db, u, id, b.status)
@router.post("/actions/recommendations/{id}/assign", response_model=RecOut, tags=["actions"])
def assign(id: int, b: AssignIn, db: Session = Depends(get_db), u=Depends(require_roles("MINE_MANAGER"))):
    r = _rec(db, id); r.owner = b.owner; db.commit(); audit(db, u.id, "action.assign", id=id, owner=b.owner); return r
def _move(db, u, id, to):
    r = _rec(db, id)
    if to not in FLOW.get(r.status, set()): raise HTTPException(409, f"Cannot move from {r.status} to {to}")
    r.status = to; db.commit(); audit(db, u.id, "action.status", id=id, to=to); return r
@router.get("/equipment", tags=["equipment"])
def equipment(mine_id: int | None = None, page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), _=Depends(current_user)):
    q = select(Equipment); q = q.where(Equipment.mine_id == mine_id) if mine_id else q; return paged(db, q, page, size)
@router.get("/data-sources", tags=["ingestion"])
def sources(db: Session = Depends(get_db), _=Depends(require_roles("DATA_ENGINEER"))): return db.scalars(select(DataSource)).all()
@router.get("/audit-logs", tags=["admin"])
def logs(page: int = Query(1, ge=1), size: int = Query(50, le=200), db: Session = Depends(get_db), _=Depends(require_roles())): return paged(db, select(AuditLog).order_by(AuditLog.id.desc()), page, size)
@router.get("/system/health", tags=["admin"])
def health(): return {"status": "ok"}
@router.get("/dashboard/summary", tags=["dashboard"])
def dashboard(mine_id: int | None = None, days: int = Query(30, ge=1, le=365), date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db), _=Depends(current_user)):
    R = ProductionRecord; mf = [R.mine_id == mine_id] if mine_id else []
    try: rng = check_range(date_from, date_to)
    except ValueError as e: raise HTTPException(422, str(e))
    last = db.scalar(select(func.max(R.day)).where(*mf))
    if last is None: raise HTTPException(404, "No production data yet")
    def sums(d0, d1=None):
        return db.execute(select(func.coalesce(func.sum(R.actual_t), 0), func.coalesce(func.sum(R.planned_t), 0)).where(R.day >= d0, R.day <= (d1 or last), *mf)).one()
    a_today, p_today = sums(last, last)
    start, end = rng if rng else (last - timedelta(days=days - 1), last)  # a custom range wins over days
    all_mines = db.scalars(select(Mine)).all()
    names = {m.id: m.name for m in all_mines}
    mine_wise = [{"mine": m.name, **dict(zip(("actual", "planned"), map(round, sums_for(db, m.id, start, end))))} for m in all_mines if not mine_id or m.id == mine_id]
    trend = [{"date": str(d), "planned": round(p), "actual": round(a)} for d, p, a in db.execute(select(R.day, func.sum(R.planned_t), func.sum(R.actual_t)).where(R.day >= start, R.day <= end, *mf).group_by(R.day).order_by(R.day))]
    latest, seen = [], set()
    for r in db.scalars(select(ShortfallRisk).order_by(ShortfallRisk.id.desc())):
        if mine_id and r.mine_id != mine_id: continue
        if r.mine_id not in seen: seen.add(r.mine_id); latest.append(r)
    alerts = {k: sum(1 for r in latest if r.level == k) for k in ("Critical", "High", "Medium", "Low")}
    avail = db.scalar(select(func.avg(Equipment.availability_pct)).where(*([Equipment.mine_id == mine_id] if mine_id else []))) or 0
    S = StockReading  # newest closing stockpile per mine, summed; ignores the period (it is a level, not a flow)
    newest = select(S.mine_id.label("m"), func.max(S.day).label("d")).where(*([S.mine_id == mine_id] if mine_id else [])).group_by(S.mine_id).subquery()
    stock = db.execute(select(S.day, S.closing_t).join(newest, and_(S.mine_id == newest.c.m, S.day == newest.c.d))).all()
    return {"today": round(a_today), "todayDeltaPct": round((a_today - p_today) / p_today * 100) if p_today else 0,
            "mtd": round(sums(last.replace(day=1))[0]), "ytd": round(sums(last.replace(month=1, day=1))[0]),
            "mineWise": mine_wise, "trend": trend, "alerts": alerts, "availability": round(avail), "stockpileT": round(sum(x[1] for x in stock)) if stock else None, "stockpileAsOf": str(min(x[0] for x in stock)) if stock else None, "stockpileMines": len(stock), "totalMines": 1 if mine_id else len(all_mines),
            "risks": [{"id": str(r.id), "mineName": names.get(r.mine_id, "?"), "level": r.level, "expectedShortfall": round(r.expected_shortfall_t), "cause": r.main_cause, "confidence": round(r.confidence)} for r in latest]}
def sums_for(db, mine_id, d0, d1):
    R = ProductionRecord
    return db.execute(select(func.coalesce(func.sum(R.actual_t), 0), func.coalesce(func.sum(R.planned_t), 0)).where(R.mine_id == mine_id, R.day >= d0, R.day <= d1)).one()
