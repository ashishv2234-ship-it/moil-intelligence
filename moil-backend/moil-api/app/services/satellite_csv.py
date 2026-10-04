"""Validation for satellite layer CSV files (no database here, so it is easy to test).
Columns: indicator, lat, lng, value (required); date, source, cell_deg (optional)."""
import csv, io
from datetime import date, datetime

INDICATORS = {  # key: (label, unit, lowest allowed, highest allowed)
    "ndvi": ("NDVI (vegetation)", "", -0.2, 1.0),
    "soil": ("Soil moisture", "%", 0.0, 100.0),
    "lst": ("Land-surface temperature", "°C", -10.0, 70.0),
    "rain": ("Rainfall (last 30 days)", "mm", 0.0, 2000.0)}
REQUIRED = ["indicator", "lat", "lng", "value"]
MAX_ROWS = 5000

def _num(s):
    try: v = float((s or "").strip().replace(",", ""))
    except ValueError: return None
    return v if v == v and abs(v) != float("inf") else None

def _date(s):
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try: return datetime.strptime(s.strip(), f).date()
        except ValueError: pass
    return None

def parse_csv(text: str, today: date | None = None) -> tuple[list[dict], list[tuple[int, str]]]:
    """Returns (good rows, problems). Row numbers are file line numbers (header = line 1). Raises ValueError for a bad header."""
    today = today or date.today()
    rd = csv.DictReader(io.StringIO(text))
    head = [(h or "").strip().lower() for h in (rd.fieldnames or [])]
    missing = [c for c in REQUIRED if c not in head]
    if missing: raise ValueError("Missing column(s): " + ", ".join(missing) + ". Required: " + ", ".join(REQUIRED))
    rd.fieldnames = head
    rows, problems, seen = [], [], set()
    for n, r in enumerate(rd, start=2):
        if n - 1 > MAX_ROWS: problems.append((n, f"Too many rows: only the first {MAX_ROWS} are read")); break
        ind = (r.get("indicator") or "").strip().lower(); lat = _num(r.get("lat")); lng = _num(r.get("lng")); val = _num(r.get("value"))
        if ind not in INDICATORS: problems.append((n, f"Unknown indicator '{ind}'. Use: " + ", ".join(INDICATORS))); continue
        if lat is None or lng is None or not (6 <= lat <= 38 and 68 <= lng <= 98): problems.append((n, "Latitude or longitude is missing or outside India")); continue
        _, _, lo, hi = INDICATORS[ind]
        if val is None or not (lo <= val <= hi): problems.append((n, f"Value must be a number between {lo} and {hi} for {ind}")); continue
        raw_d = (r.get("date") or "").strip(); d = _date(raw_d) if raw_d else today
        if d is None or d > today: problems.append((n, "Date is not valid or is in the future (use YYYY-MM-DD)")); continue
        cd = _num(r.get("cell_deg")) if (r.get("cell_deg") or "").strip() else 0.25
        if cd is None or not (0.01 <= cd <= 1): problems.append((n, "cell_deg must be between 0.01 and 1")); continue
        key = (ind, round(lat, 4), round(lng, 4))
        if key in seen: problems.append((n, "Duplicate cell for this indicator")); continue
        seen.add(key)
        rows.append({"indicator": ind, "lat": lat, "lng": lng, "value": val, "observed_on": d, "cell_deg": cd, "source": (r.get("source") or "").strip()[:60] or "CSV upload"})
    return rows, problems
