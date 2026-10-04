from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.dependencies import require_roles, audit
from app.db.session import get_db
from app.models import Upload, DataQualityIssue
from app.services.ingest import process_production, process_telematics, process_stockpile
router = APIRouter(prefix="/ingestion", tags=["ingestion"])
MAX_BYTES = 2_000_000
def out(u: Upload) -> dict:
    return {"id": u.id, "kind": u.kind, "filename": u.filename, "status": u.status, "dry_run": u.dry_run, "rows_total": u.rows_total,
            "rows_ok": u.rows_ok, "rows_rejected": u.rows_rejected, "rows_warning": u.rows_warning, "issues_total": u.issues_total,
            "quality_pct": round(u.rows_ok / u.rows_total * 100) if u.rows_total else 0, "created_at": u.created_at}
def issue(i: DataQualityIssue) -> dict: return {"row": i.row_no, "field": i.field, "severity": i.severity, "message": i.message}
async def _read_csv(request: Request, filename: str) -> str:
    raw = await request.body()
    if not raw: raise HTTPException(422, "The file is empty")
    if len(raw) > MAX_BYTES: raise HTTPException(413, "The file is larger than 2 MB")
    if not filename.lower().endswith(".csv"): raise HTTPException(422, "Only .csv files are accepted")
    try: return raw.decode("utf-8-sig")
    except UnicodeDecodeError: raise HTTPException(422, "The file must be UTF-8 text. In Excel use Save As, then CSV UTF-8.")
def _result(up, issues): return {"upload": out(up), "issues": [{"row": r, "field": f, "severity": s, "message": m} for r, f, s, m in issues]}
@router.post("/production", status_code=201)
async def upload_production(request: Request, filename: str = Query("upload.csv"), dry_run: bool = False,
                            db: Session = Depends(get_db), u=Depends(require_roles("DATA_ENGINEER"))):
    """Body is the raw CSV file (Content-Type text/csv). Columns: mine, date, planned_t, actual_t."""
    text = await _read_csv(request, filename)
    up, issues = process_production(db, text, filename, u.id, dry_run)
    audit(db, u.id, "ingest.production", file=up.filename, ok=up.rows_ok, rejected=up.rows_rejected, dry_run=dry_run)
    return _result(up, issues)
@router.post("/telematics", status_code=201)
async def upload_telematics(request: Request, filename: str = Query("telematics.csv"), dry_run: bool = False,
                            db: Session = Depends(get_db), u=Depends(require_roles("DATA_ENGINEER"))):
    """Body is the raw CSV file (Content-Type text/csv). Columns: code, status (+ optional availability_pct, health_score, downtime_hrs)."""
    text = await _read_csv(request, filename)
    up, issues = process_telematics(db, text, filename, u.id, dry_run)
    audit(db, u.id, "ingest.telematics", file=up.filename, ok=up.rows_ok, rejected=up.rows_rejected, dry_run=dry_run)
    return _result(up, issues)
@router.post("/sap", status_code=201)
async def upload_sap(request: Request, filename: str = Query("sap-export.csv"), dry_run: bool = False,
                     db: Session = Depends(get_db), u=Depends(require_roles("DATA_ENGINEER"))):
    """Body is the raw CSV file. SAP-style columns: Plant, Posting Date, Target Qty, Confirmed Qty (+ optional Unit: TO, T, MT or KG)."""
    text = await _read_csv(request, filename)
    up, issues = process_production(db, text, filename, u.id, dry_run, kind="sap")
    audit(db, u.id, "ingest.sap", file=up.filename, ok=up.rows_ok, rejected=up.rows_rejected, dry_run=dry_run)
    return _result(up, issues)
@router.get("/uploads")
def uploads(db: Session = Depends(get_db), _=Depends(require_roles("DATA_ENGINEER", "GEOLOGIST"))):
    return [out(x) for x in db.scalars(select(Upload).order_by(Upload.id.desc()).limit(50))]
@router.get("/uploads/{upload_id}/issues")
def upload_issues(upload_id: int, db: Session = Depends(get_db), _=Depends(require_roles("DATA_ENGINEER", "GEOLOGIST"))):
    if not db.get(Upload, upload_id): raise HTTPException(404, "Upload not found")
    return [issue(i) for i in db.scalars(select(DataQualityIssue).where(DataQualityIssue.upload_id == upload_id).order_by(DataQualityIssue.id))]
@router.post("/stockpile", status_code=201)
async def upload_stockpile(request: Request, filename: str = Query("stockpile.csv"), dry_run: bool = False,
                           db: Session = Depends(get_db), u=Depends(require_roles("DATA_ENGINEER"))):
    """Body is the raw CSV file. Columns: mine, date, stockpile_t (closing stockpile in tonnes)."""
    text = await _read_csv(request, filename)
    up, issues = process_stockpile(db, text, filename, u.id, dry_run)
    audit(db, u.id, "ingest.stockpile", file=up.filename, ok=up.rows_ok, rejected=up.rows_rejected, dry_run=dry_run)
    return _result(up, issues)

