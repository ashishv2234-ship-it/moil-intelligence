from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from app.core.dependencies import require_roles, audit
from app.db.session import get_db
from app.services import satellite as sat
from app.services.satellite_csv import INDICATORS
router = APIRouter(prefix="/satellite", tags=["satellite"])
READ = ("GEOLOGIST", "EXECUTIVE", "DATA_ENGINEER")  # admin is always allowed
WRITE = ("GEOLOGIST", "DATA_ENGINEER")
MAX_BYTES = 2_000_000
@router.get("/layers")
def layers(db: Session = Depends(get_db), _=Depends(require_roles(*READ))): return sat.summary(db)
@router.get("/layers/{indicator}")
def one_layer(indicator: str, db: Session = Depends(get_db), _=Depends(require_roles(*READ))):
    if indicator not in INDICATORS: raise HTTPException(404, "Unknown layer. Use: " + ", ".join(INDICATORS))
    return sat.layer(db, indicator)
@router.post("/sync")
def sync(db: Session = Depends(get_db), u=Depends(require_roles(*WRITE))):
    """Fetch rainfall, soil moisture and surface temperature for the mining belt (Open-Meteo, no key)."""
    r = sat.sync_open_meteo(db); audit(db, u.id, "satellite.sync", updated=r["updated"], cells=r["cells"])
    if r["updated"] == 0: raise HTTPException(502, "Could not reach the weather service. Check the server's internet connection.")
    return r
@router.post("/upload", status_code=201)
async def upload(request: Request, filename: str = Query("layer.csv"), db: Session = Depends(get_db), u=Depends(require_roles(*WRITE))):
    """Body is the raw CSV file (Content-Type text/csv). Columns: indicator, lat, lng, value (+ optional date, source, cell_deg)."""
    raw = await request.body()
    if not raw: raise HTTPException(422, "The file is empty")
    if len(raw) > MAX_BYTES: raise HTTPException(413, "The file is larger than 2 MB")
    if not filename.lower().endswith(".csv"): raise HTTPException(422, "Only .csv files are accepted")
    try: text = raw.decode("utf-8-sig")
    except UnicodeDecodeError: raise HTTPException(422, "The file must be UTF-8 text. In Excel use Save As, then CSV UTF-8.")
    try: r = sat.import_csv(db, text)
    except ValueError as e: raise HTTPException(422, str(e))
    audit(db, u.id, "satellite.upload", file=filename[:100], imported=r["imported"], rejected=r["rejected"])
    return r
