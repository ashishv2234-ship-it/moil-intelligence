"""Report datasets. Every report returns {title, columns, rows, note}; exporters turn that into CSV/Excel, the UI prints it as PDF."""
from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models import Mine, ProductionRecord, ShortfallRisk, ActionRecommendation, Equipment, BlastPlan

_PLAN = {"MINE_MANAGER", "PLANNING_ENGINEER", "EXECUTIVE"}
ALLOWED = {"production": _PLAN, "risks": _PLAN, "actions": _PLAN,
           "equipment": {"MINE_MANAGER", "MAINTENANCE_ENGINEER", "EXECUTIVE"}, "blasting": {"MINE_MANAGER", "EXECUTIVE"}}  # ADMIN can read all

def dataset(db: Session, kind: str, days: int = 30, date_from: date | None = None, date_to: date | None = None) -> dict:
    names = {m.id: m.name for m in db.scalars(select(Mine))}
    nm = lambda i: names.get(i, f"Mine {i}")
    if kind == "production":
        since = date_from or date.today() - timedelta(days=days)
        until = [ProductionRecord.day <= date_to] if date_to else []
        q = select(ProductionRecord.mine_id, func.sum(ProductionRecord.planned_t), func.sum(ProductionRecord.actual_t)).where(ProductionRecord.day >= since, *until).group_by(ProductionRecord.mine_id)
        rows = sorted([[nm(m), round(p), round(a), round(a - p), round(a / p * 100, 1) if p else 0] for m, p, a in db.execute(q)], key=lambda r: r[0])
        return {"title": f"Production summary, {date_from} to {date_to}" if date_from and date_to else f"Production summary, last {days} days", "columns": ["Mine", "Planned (t)", "Actual (t)", "Gap (t)", "Achievement (%)"], "rows": rows, "note": None}
    if kind == "risks":
        latest: dict[int, ShortfallRisk] = {}
        for r in db.scalars(select(ShortfallRisk).order_by(ShortfallRisk.id)): latest[r.mine_id] = r
        rows = [[nm(r.mine_id), r.level, round(r.probability), round(r.expected_shortfall_t), r.main_cause, round(r.confidence), r.status] for r in latest.values()]
        rows.sort(key=lambda r: -r[3])
        return {"title": "Shortfall risk by mine, next 30 days", "columns": ["Mine", "Risk level", "Probability (%)", "Expected shortfall (t)", "Main cause", "Confidence (%)", "Status"],
                "rows": rows, "note": "AI-generated forecast. Confidence is shown for each row."}
    if kind == "actions":
        mine_of = {r.id: r.mine_id for r in db.scalars(select(ShortfallRisk))}
        rows = [[a.action_type, nm(mine_of.get(a.risk_id, 0)), round(a.recovery_t), round(a.cost_inr_lakh, 1), round(a.feasibility * 100), round(a.confidence), a.owner or "Unassigned", a.status, a.valid_until.date().isoformat()]
                for a in db.scalars(select(ActionRecommendation).order_by(ActionRecommendation.id))]
        return {"title": "Corrective action recommendations", "columns": ["Action", "Mine", "Recovery (t)", "Cost (INR lakh)", "Feasibility (%)", "Confidence (%)", "Owner", "Status", "Valid until"],
                "rows": rows, "note": "AI-generated recommendation. Confidence is shown for each row."}
    if kind == "equipment":
        rows = [[e.code, e.type, nm(e.mine_id), e.status, round(e.availability_pct), round(e.health_score), round(e.downtime_hrs)] for e in db.scalars(select(Equipment).order_by(Equipment.mine_id, Equipment.code))]
        return {"title": "Equipment status", "columns": ["Code", "Type", "Mine", "Status", "Availability (%)", "Health score", "Downtime (hrs)"], "rows": rows, "note": None}
    if kind == "blasting":
        since = date_from or date.today() - timedelta(days=days)  # no end date unless a custom range is set, so upcoming scheduled blasts stay visible
        until = [BlastPlan.blast_date <= date_to] if date_to else []
        rows = [[b.blast_date.isoformat(), nm(b.mine_id), b.bench, round(b.planned_t), round(b.actual_t) if b.actual_t is not None else "", b.status, b.delay_reason or ""]
                for b in db.scalars(select(BlastPlan).where(BlastPlan.blast_date >= since, *until).order_by(BlastPlan.blast_date.desc(), BlastPlan.id.desc()).limit(500))]
        return {"title": f"Blasting log, {date_from} to {date_to}" if date_from and date_to else f"Blasting log, last {days} days and upcoming", "columns": ["Date", "Mine", "Bench", "Planned (t)", "Actual (t)", "Status", "Note"], "rows": rows, "note": None}
    raise KeyError(kind)
