from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.dependencies import require_roles, audit
from app.db.session import get_db
from app.models import DrillHole, ReserveZone
from app.services.prospectivity import run_model, MODEL_VERSION, ASSUMPTIONS
router = APIRouter(prefix="/geology", tags=["geology"])
READ = ("GEOLOGIST", "EXECUTIVE")  # admin is always allowed


def zone_out(z: ReserveZone) -> dict:
    return {"id": z.id, "cell_key": z.cell_key, "lat": z.lat, "lng": z.lng, "probability": z.probability, "tonnage_t": z.tonnage_t,
            "grade_mn_pct": z.grade_mn_pct, "confidence_pct": z.confidence_pct, "holes_nearby": z.holes_nearby,
            "nearest_mine_km": z.nearest_mine_km, "drill_suggested": z.drill_suggested, "drill_recommended": z.drill_recommended,
            "model_version": z.model_version, "run_at": z.run_at}


@router.get("/zones")
def zones(db: Session = Depends(get_db), _=Depends(require_roles(*READ))):
    return [zone_out(z) for z in db.scalars(select(ReserveZone).order_by(ReserveZone.probability.desc()))]


@router.get("/drill-holes")
def drill_holes(db: Session = Depends(get_db), _=Depends(require_roles(*READ))):
    return [{"id": h.code, "lat": h.lat, "lng": h.lng, "depth_m": h.depth_m, "mn_pct": h.mn_pct, "source": h.source}
            for h in db.scalars(select(DrillHole).order_by(DrillHole.code))]


@router.get("/model")
def model_info(_=Depends(require_roles(*READ))):
    return {"version": MODEL_VERSION, "type": "Weighted-evidence scoring (expert weights, not machine-learned)", "assumptions": ASSUMPTIONS}


@router.post("/prospectivity/run")
def run(db: Session = Depends(get_db), u=Depends(require_roles("GEOLOGIST"))):
    try: res = run_model(db)
    except ValueError as e: raise HTTPException(422, str(e))
    audit(db, u.id, "geology.prospectivity_run", zones=res["zones"], holes=res["holes_used"], version=res["model_version"])
    return res


@router.post("/zones/{zone_id}/drilling")
def recommend_drilling(zone_id: int, db: Session = Depends(get_db), u=Depends(require_roles("GEOLOGIST"))):
    z = db.get(ReserveZone, zone_id)
    if not z: raise HTTPException(404, "Zone not found")
    z.drill_recommended = True; db.commit()
    audit(db, u.id, "geology.recommend_drilling", zone=z.cell_key, probability=z.probability)
    return zone_out(z)
