from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.dependencies import current_user, require_roles, audit
from app.db.session import get_db
from app.services.weather import latest, sync_weather, sync_forecast, forecast_all
router = APIRouter(prefix="/weather", tags=["weather"])
@router.get("/current")
def current(db: Session = Depends(get_db), _=Depends(current_user)): return latest(db)
@router.post("/sync")
def sync(db: Session = Depends(get_db), u=Depends(require_roles("DATA_ENGINEER", "MINE_MANAGER"))):
    r = sync_weather(db); fc = sync_forecast(db); audit(db, u.id, "weather.sync", updated=r["updated"], failed=r["failed"], forecast_updated=fc["updated"])
    if r["updated"] == 0 and fc["updated"] == 0: raise HTTPException(502, "Could not reach the weather service. Check the server's internet connection.")
    return {**r, "forecast_updated": fc["updated"]}
@router.get("/forecast")
def forecast(db: Session = Depends(get_db), _=Depends(current_user)): return forecast_all(db)
