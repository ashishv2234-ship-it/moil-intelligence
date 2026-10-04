"""Reserve prospectivity model v1.

This is a transparent weighted-evidence scoring model, NOT a trained machine-learning model. Weights are set by
expert judgement and are listed below so a geologist can review and change them. Once real drill-hole assays and
labelled outcomes exist, replace score_cell() with a trained model (the rest of the pipeline stays the same).

For each 0.08 degree grid cell (about 9 km) it combines three pieces of evidence:
  1. grade evidence : inverse-distance-weighted Mn grade of the nearest drill holes (within 15 km)
  2. hit rate       : share of those holes at or above the 25% Mn cut-off (scaled down when few holes exist)
  3. mine proximity : closeness to existing mines (known mineralised belt)
Probability = logistic(weighted sum). Tonnage is an indicative potential, not a certified resource estimate.
"""
import math
from datetime import datetime

MODEL_VERSION = "weighted-evidence-v1"
LAT_MIN, LAT_MAX, LNG_MIN, LNG_MAX, STEP = 21.0, 22.1, 79.0, 80.5, 0.08
SEARCH_KM, CUTOFF_MN, MIN_PROB = 15.0, 25.0, 15.0
BIAS, W_GRADE, W_HIT, W_MINE = -3.6, 3.4, 2.0, 1.4
FOOTPRINT, THICKNESS_M, DENSITY = 0.001, 2.5, 3.6  # ore lens = 0.1% of cell area, 2.5 m thick, 3.6 t/m3
ASSUMPTIONS = {"weights": {"bias": BIAS, "grade": W_GRADE, "hit_rate": W_HIT, "mine_proximity": W_MINE},
               "search_radius_km": SEARCH_KM, "cutoff_mn_pct": CUTOFF_MN, "grid_step_deg": STEP,
               "ore_footprint_fraction": FOOTPRINT, "thickness_m": THICKNESS_M, "density_t_m3": DENSITY}


def _km(lat1, lng1, lat2, lng2):
    dy = (lat2 - lat1) * 111.0
    dx = (lng2 - lng1) * 111.0 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dx, dy)


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def score_cell(lat, lng, holes, mines, regional_mean):
    """holes: [(lat, lng, mn_pct)], mines: [(lat, lng)]. Returns a dict of results for one cell."""
    near = sorted((_km(lat, lng, h[0], h[1]), h[2]) for h in holes)
    near = [x for x in near if x[0] <= SEARCH_KM]
    n = len(near)
    if n:
        use = near[:6]
        w = [1 / max(d, 1.0) ** 2 for d, _ in use]
        grade = sum(wi * mn for wi, (_, mn) in zip(w, use)) / sum(w)
        hit = (sum(1 for _, mn in near if mn >= CUTOFF_MN) / n) * min(1.0, n / 3)
        nearest_hole = near[0][0]
    else:
        grade, hit, nearest_hole = None, 0.0, None
    d_mine = min((_km(lat, lng, m[0], m[1]) for m in mines), default=999.0)
    grade_s = 0.0 if grade is None else _clamp((grade - 10) / 30)
    mine_s = math.exp(-d_mine / 20)
    z = BIAS + W_GRADE * grade_s + W_HIT * hit + W_MINE * mine_s
    p = 100 / (1 + math.exp(-z))
    est_grade = _clamp(grade if grade is not None else regional_mean, 15, 48)
    area_m2 = (STEP * 111000) * (STEP * 111000 * math.cos(math.radians(lat)))
    tonnage = p / 100 * area_m2 * FOOTPRINT * THICKNESS_M * DENSITY
    conf = 25.0 if n == 0 else min(95.0, 25 + 8 * min(n, 6) + (10 if nearest_hole <= 6 else 0))
    return {"probability": round(p, 1), "tonnage_t": round(tonnage, -3), "grade_mn_pct": round(est_grade, 1),
            "confidence_pct": round(conf), "holes_nearby": n, "nearest_mine_km": round(d_mine, 1),
            "drill_suggested": p >= 60 and conf < 65}


def score_grid(holes, mines):
    """Scores every grid cell. Returns {cell_key: result with lat/lng}."""
    if not holes:
        raise ValueError("No drill-hole data to score. Load drill holes first.")
    mean = sum(h[2] for h in holes) / len(holes)
    out = {}
    for r in range(int(round((LAT_MAX - LAT_MIN) / STEP))):
        for c in range(int(round((LNG_MAX - LNG_MIN) / STEP))):
            lat, lng = LAT_MIN + (r + .5) * STEP, LNG_MIN + (c + .5) * STEP
            out[f"r{r:02d}c{c:02d}"] = {"lat": round(lat, 4), "lng": round(lng, 4), **score_cell(lat, lng, holes, mines, mean)}
    return out


def run_model(db):
    """Reads drill holes and mines from the database, scores the grid and saves zones. Keeps drilling flags."""
    from sqlalchemy import select
    from app.models import DrillHole, Mine, ReserveZone
    holes = [(h.lat, h.lng, h.mn_pct) for h in db.scalars(select(DrillHole))]
    mines = [(m.lat, m.lng) for m in db.scalars(select(Mine))]
    res = score_grid(holes, mines)
    now = datetime.utcnow()
    existing = {z.cell_key: z for z in db.scalars(select(ReserveZone))}
    for key, r in res.items():
        z = existing.get(key)
        keep = r["probability"] >= MIN_PROB or (z is not None and z.drill_recommended)
        if not keep:
            if z is not None:
                db.delete(z)
            continue
        if z is None:
            z = ReserveZone(cell_key=key)
            db.add(z)
        z.lat, z.lng, z.probability, z.tonnage_t = r["lat"], r["lng"], r["probability"], r["tonnage_t"]
        z.grade_mn_pct, z.confidence_pct, z.holes_nearby = r["grade_mn_pct"], r["confidence_pct"], r["holes_nearby"]
        z.nearest_mine_km, z.drill_suggested = r["nearest_mine_km"], r["drill_suggested"]
        z.model_version, z.run_at = MODEL_VERSION, now
    db.commit()
    return {"zones": db.query(ReserveZone).count(), "holes_used": len(holes), "mines_used": len(mines),
            "model_version": MODEL_VERSION, "run_at": now}
