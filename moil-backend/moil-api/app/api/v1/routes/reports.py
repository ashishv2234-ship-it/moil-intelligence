from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from app.core.dependencies import current_user, audit
from app.db.session import get_db
from app.services.reports import dataset, ALLOWED
from app.services.report_export import to_csv, to_xlsx
from app.services.period import check_range
router = APIRouter(prefix="/reports", tags=["reports"])
@router.get("/{kind}")
def report(kind: str, format: str = Query("json", pattern="^(json|csv|xlsx)$"), days: int = Query(30, ge=1, le=365), date_from: date | None = None, date_to: date | None = None,
           db: Session = Depends(get_db), u=Depends(current_user)):
    """format=json gives a preview (used for the on-screen table and PDF print); csv and xlsx are downloads."""
    if kind not in ALLOWED: raise HTTPException(404, "Unknown report")
    if u.role != "ADMIN" and u.role not in ALLOWED[kind]: raise HTTPException(403, "Your role cannot view this report")
    try: rng = check_range(date_from, date_to)
    except ValueError as e: raise HTTPException(422, str(e))
    ds = dataset(db, kind, days, *(rng or (None, None))); ds["generated_at"] = datetime.utcnow().isoformat() + "Z"
    if format == "json": return ds
    audit(db, u.id, "report.download", kind=kind, format=format)
    if format == "csv": return Response(to_csv(ds), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="moil-{kind}.csv"'})
    return Response(to_xlsx(ds), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="moil-{kind}.xlsx"'})
