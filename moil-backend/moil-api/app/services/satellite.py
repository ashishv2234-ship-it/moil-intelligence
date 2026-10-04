"""Satellite layers: stored grid cells per indicator (ndvi, soil, lst, rain). One dataset per indicator: a new sync or upload replaces it."""
from datetime import datetime, date
from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session
from app.integrations.satellite.openmeteo_grid import fetch as grid_fetch, CELL_DEG
from app.models import SatelliteCell, DataSource
from app.services.satellite_csv import INDICATORS, parse_csv

OM_SOURCE = "Open-Meteo (model)"
OM_SOURCE_NAME, CSV_SOURCE_NAME = "Satellite grid (Open-Meteo)", "Satellite CSV upload"

def _touch(db: Session, name: str, n: int, ok: bool = True):
    s = db.scalar(select(DataSource).where(DataSource.name == name))
    if not s: s = DataSource(name=name, records=0); db.add(s)
    s.status = "Success" if ok else "Failed"; s.last_sync = datetime.utcnow(); s.records = (s.records or 0) + n

def _replace(db: Session, rows: list[dict]):
    for ind in {r["indicator"] for r in rows}: db.execute(delete(SatelliteCell).where(SatelliteCell.indicator == ind))
    for r in rows: db.add(SatelliteCell(**r))

def sync_open_meteo(db: Session, fetch=grid_fetch) -> dict:
    try: recs = fetch()
    except Exception:  # offline, timeout or odd answer: report it, never crash
        _touch(db, OM_SOURCE_NAME, 0, ok=False); db.commit(); return {"updated": 0, "cells": 0}
    rows = []
    for rec in recs:
        d = date.fromisoformat(rec["as_of"]) if rec.get("as_of") else date.today()
        for ind in ("rain", "soil", "lst"):
            if ind in rec: rows.append({"indicator": ind, "lat": rec["lat"], "lng": rec["lng"], "value": rec[ind], "observed_on": d, "cell_deg": CELL_DEG, "source": OM_SOURCE})
    if not rows: _touch(db, OM_SOURCE_NAME, 0, ok=False); db.commit(); return {"updated": 0, "cells": 0}
    _replace(db, rows); _touch(db, OM_SOURCE_NAME, len(rows)); db.commit()
    return {"updated": len({r["indicator"] for r in rows}), "cells": len(rows)}

def import_csv(db: Session, text: str) -> dict:
    rows, problems = parse_csv(text)  # ValueError (bad header) is turned into a 422 by the route
    if not rows:
        first = f" First problem: row {problems[0][0]}: {problems[0][1]}" if problems else ""
        raise ValueError("No valid rows to import." + first)
    _replace(db, rows); _touch(db, CSV_SOURCE_NAME, len(rows)); db.commit()
    return {"imported": len(rows), "rejected": len(problems), "indicators": sorted({r["indicator"] for r in rows}),
            "issues": [{"row": n, "message": m} for n, m in problems[:20]]}

def summary(db: Session) -> list[dict]:
    out = []
    for k, (label, unit, _, _) in INDICATORS.items():
        n, d, s = db.execute(select(func.count(SatelliteCell.id), func.max(SatelliteCell.observed_on), func.max(SatelliteCell.source)).where(SatelliteCell.indicator == k)).one()
        out.append({"indicator": k, "label": label, "unit": unit, "count": n, "observed_on": d, "source": s})
    return out

def layer(db: Session, k: str) -> dict:
    cells = db.scalars(select(SatelliteCell).where(SatelliteCell.indicator == k)).all()
    vals = [c.value for c in cells]
    return {"indicator": k, "observed_on": max((c.observed_on for c in cells), default=None), "source": cells[0].source if cells else None,
            "cell_deg": cells[0].cell_deg if cells else CELL_DEG, "min": min(vals) if vals else 0, "max": max(vals) if vals else 0,
            "cells": [{"lat": c.lat, "lng": c.lng, "value": c.value} for c in cells]}


def rain_for_mine(db: Session, lat: float, lng: float) -> tuple[float | None, int | None]:
    """(30-day rainfall in mm, age of the data in days) from the grid cell holding this mine, or (None, None).
    A cell only counts if the mine lies inside it (within about 0.75 of a cell width from its centre)."""
    best, dist = None, None
    for c in db.scalars(select(SatelliteCell).where(SatelliteCell.indicator == "rain")):
        d = ((c.lat - lat) ** 2 + (c.lng - lng) ** 2) ** 0.5
        if d <= c.cell_deg * 0.75 and (dist is None or d < dist): best, dist = c, d
    if best is None: return None, None
    return best.value, max((date.today() - best.observed_on).days, 0)
