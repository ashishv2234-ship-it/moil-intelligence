"""CSV ingestion with data-quality checks (production records).
Errors reject a row; warnings import the row but flag it. Uses only the csv module (no pandas)."""
import csv, io
from datetime import date, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Mine, ProductionRecord, Upload, DataQualityIssue, DataSource, Equipment, EquipmentSnapshot, StockReading

REQUIRED = ["mine", "date", "planned_t", "actual_t"]
MAX_ROWS, MAX_STORED_ISSUES = 20000, 500
SOURCE_NAME = "Production CSV upload"
SOURCE_FOR = {"production": SOURCE_NAME, "telematics": "Fleet telematics", "sap": "SAP production (CSV)", "stockpile": "Stockpile (CSV)"}  # upload kind -> row in the Data sources table
# SAP-style export: header names (lower case, spaces and hyphens as underscores) -> the standard production columns.
SAP_COLUMNS = {"plant": "mine", "plant_name": "mine", "mine": "mine",
               "posting_date": "date", "budat": "date", "date": "date",
               "target_qty": "planned_t", "planned_qty": "planned_t", "soll_qty": "planned_t", "planned_t": "planned_t",
               "confirmed_qty": "actual_t", "actual_qty": "actual_t", "yield": "actual_t", "actual_t": "actual_t",
               "unit": "unit", "uom": "unit", "meins": "unit"}
SAP_EXPECTED = "Plant, Posting Date, Target Qty, Confirmed Qty (optional: Unit)"
UNIT_FACTOR = {"": 1.0, "t": 1.0, "to": 1.0, "mt": 1.0, "ton": 1.0, "tonne": 1.0, "kg": 0.001}  # a blank unit means tonnes
def sap_header(c: str) -> str:
    c = (c or "").strip().lower().replace(" ", "_").replace("-", "_")
    return SAP_COLUMNS.get(c, c)
STOCK_REQUIRED = ["mine", "date", "stockpile_t"]
STOCK_ALIASES = {"closing_t": "stockpile_t", "closing_stock_t": "stockpile_t", "stock_t": "stockpile_t"}
TELE_REQUIRED = ["code", "status"]
TELE_OPTIONAL = ["availability_pct", "health_score", "downtime_hrs"]  # blank cell = keep the current value
STATUSES = {"running": "Running", "idle": "Idle", "breakdown": "Breakdown", "maintenance": "Maintenance"}

def _date(s: str):
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y%m%d"):  # last two are the usual SAP export formats
        try: return datetime.strptime(s.strip(), f).date()
        except ValueError: pass
    return None

def _num(s: str):
    try: v = float(s.strip().replace(",", ""))
    except ValueError: return None
    return v if v == v and abs(v) != float("inf") else None

def _finish(db: Session, up: Upload, issues: list) -> tuple[Upload, list]:
    up.issues_total = len(issues)
    db.add(up); db.flush()
    for row_no, field, sev, msg in issues[:MAX_STORED_ISSUES]:
        db.add(DataQualityIssue(upload_id=up.id, row_no=row_no, field=field, severity=sev, message=msg[:300]))
    if up.kind in SOURCE_FOR and not up.dry_run and up.rows_ok:
        src = db.scalar(select(DataSource).where(DataSource.name == SOURCE_FOR[up.kind]))
        if not src: src = DataSource(name=SOURCE_FOR[up.kind], records=0); db.add(src)
        src.status = "Success" if not up.rows_rejected else "Warning"
        src.last_sync = datetime.utcnow(); src.records = (src.records or 0) + up.rows_ok
    db.commit()
    return up, issues[:MAX_STORED_ISSUES]

def process_production(db: Session, text: str, filename: str, user_id: int | None, dry_run: bool, kind: str = "production"):
    """kind="sap" reads SAP-style column names and units (kg or tonnes) and stores the same production records."""
    sap = kind == "sap"
    up = Upload(kind=kind, filename=filename[:200], dry_run=dry_run, uploaded_by=user_id, status="Failed",
                 rows_total=0, rows_ok=0, rows_rejected=0, rows_warning=0, issues_total=0)  # defaults only apply on save, so set counters now
    issues: list[tuple[int, str, str, str]] = []
    reader = csv.DictReader(io.StringIO(text))
    cols = [sap_header(c) if sap else (c or "").strip().lower() for c in (reader.fieldnames or [])]
    missing = [c for c in REQUIRED if c not in cols]
    if missing:
        issues.append((1, "header", "Error", f"Missing column(s): {', '.join(missing)}. Expected: " + (SAP_EXPECTED if sap else ', '.join(REQUIRED))))
        return _finish(db, up, issues)
    reader.fieldnames = cols
    mines = {m.name.lower(): m for m in db.scalars(select(Mine))}
    existing = {(r[0], r[1]) for r in db.execute(select(ProductionRecord.mine_id, ProductionRecord.day))}
    seen: set = set(); good: list[ProductionRecord] = []
    for line, row in enumerate(reader, start=2):
        if not any(v.strip() for v in row.values() if isinstance(v, str)): continue  # blank line
        if up.rows_total >= MAX_ROWS:
            issues.append((line, "file", "Error", f"More than {MAX_ROWS} rows; the rest were ignored")); break
        up.rows_total += 1
        errs: list[tuple[str, str]] = []; warns: list[tuple[str, str]] = []
        name = (row.get("mine") or "").strip()
        mine = mines.get(name.lower())
        if not mine: errs.append(("mine", f"Unknown mine '{name}'"))
        d = _date(row.get("date") or "")
        if d is None: errs.append(("date", "Date must look like 2026-09-30"))
        elif d > date.today(): errs.append(("date", "Date is in the future"))
        p, a = _num(row.get("planned_t") or ""), _num(row.get("actual_t") or "")
        if sap:
            unit = (row.get("unit") or "").strip(); factor = UNIT_FACTOR.get(unit.lower())
            if factor is None: errs.append(("unit", f"Unit '{unit}' is not supported. Use TO, T, MT or KG"))
            else: p = round(p * factor, 3) if p is not None else None; a = round(a * factor, 3) if a is not None else None
        if p is None or p < 0: errs.append(("planned_t", "Planned tonnes must be a number, zero or more"))
        if a is None or a < 0: errs.append(("actual_t", "Actual tonnes must be a number, zero or more"))
        if not errs:
            key = (mine.id, d)
            if key in seen: errs.append(("date", "Duplicate mine and date earlier in this file"))
            elif key in existing: errs.append(("date", "A record for this mine and date already exists"))
            else:
                if a > 2 * mine.daily_target_t: warns.append(("actual_t", f"Actual {a:,.0f} t is more than twice the daily target ({mine.daily_target_t:,.0f} t). Please check."))
                if a == 0 and p > 0: warns.append(("actual_t", "Zero output on a planned day. Please check."))
                seen.add(key); good.append(ProductionRecord(mine_id=mine.id, day=d, planned_t=p, actual_t=a))
        issues += [(line, f, "Error", m) for f, m in errs] + [(line, f, "Warning", m) for f, m in warns]
        if errs: up.rows_rejected += 1
        else: up.rows_ok += 1
        if warns: up.rows_warning += 1
    if up.rows_total == 0: issues.append((1, "file", "Error", "The file has no data rows"))
    if good and not dry_run: db.add_all(good)
    up.status = "Failed" if not up.rows_ok else "Validated" if dry_run else "Imported"
    return _finish(db, up, issues)


def process_telematics(db: Session, text: str, filename: str, user_id: int | None, dry_run: bool):
    """Fleet telematics snapshot: one row per machine updates its status, availability, health and downtime.
    Machines are never created here: an unknown code is an error. Blank optional cells keep the current value."""
    up = Upload(kind="telematics", filename=filename[:200], dry_run=dry_run, uploaded_by=user_id, status="Failed",
                 rows_total=0, rows_ok=0, rows_rejected=0, rows_warning=0, issues_total=0)
    issues: list[tuple[int, str, str, str]] = []
    reader = csv.DictReader(io.StringIO(text))
    cols = [(c or "").strip().lower() for c in (reader.fieldnames or [])]
    missing = [c for c in TELE_REQUIRED if c not in cols]
    if missing:
        issues.append((1, "header", "Error", f"Missing column(s): {', '.join(missing)}. Expected: {', '.join(TELE_REQUIRED + TELE_OPTIONAL)}"))
        return _finish(db, up, issues)
    reader.fieldnames = cols
    machines = {e.code.lower(): e for e in db.scalars(select(Equipment))}
    seen: set = set(); good: list[tuple[Equipment, dict]] = []
    for line, row in enumerate(reader, start=2):
        if not any(v.strip() for v in row.values() if isinstance(v, str)): continue  # blank line
        if up.rows_total >= MAX_ROWS:
            issues.append((line, "file", "Error", f"More than {MAX_ROWS} rows; the rest were ignored")); break
        up.rows_total += 1
        errs: list[tuple[str, str]] = []; warns: list[tuple[str, str]] = []; new: dict = {}
        code = (row.get("code") or "").strip(); eq = machines.get(code.lower())
        if not eq: errs.append(("code", f"Unknown equipment code '{code}'"))
        elif eq.id in seen: errs.append(("code", "Duplicate code earlier in this file"))
        st = STATUSES.get((row.get("status") or "").strip().lower())
        if not st: errs.append(("status", "Status must be Running, Idle, Breakdown or Maintenance"))
        else: new["status"] = st
        for field, lo, hi in (("availability_pct", 0, 100), ("health_score", 0, 100), ("downtime_hrs", 0, None)):
            raw = (row.get(field) or "").strip()
            if not raw: continue
            v = _num(raw)
            if v is None or v < lo or (hi is not None and v > hi): errs.append((field, f"{field} must be a number" + (f" from {lo} to {hi}" if hi is not None else f", {lo} or more")))
            else: new[field] = v
        if not errs:
            av = new.get("availability_pct", eq.availability_pct)
            if new["status"] == "Running" and av < 50: warns.append(("status", f"Marked Running but availability is only {av:.0f}%. Please check."))
            if new["status"] == "Breakdown" and av > 90: warns.append(("status", f"Marked Breakdown but availability is {av:.0f}%. Please check."))
            if new.get("downtime_hrs", 0) > 720: warns.append(("downtime_hrs", "More than 720 hours (30 days) of downtime. Please check."))
            seen.add(eq.id); good.append((eq, new))
        issues += [(line, f, "Error", m) for f, m in errs] + [(line, f, "Warning", m) for f, m in warns]
        if errs: up.rows_rejected += 1
        else: up.rows_ok += 1
        if warns: up.rows_warning += 1
    if up.rows_total == 0: issues.append((1, "file", "Error", "The file has no data rows"))
    if good and not dry_run:
        db.add(up); db.flush()  # gives the upload an id so each snapshot can point to it
        for eq, new in good:
            for k, v in new.items(): setattr(eq, k, v)
            db.add(EquipmentSnapshot(equipment_id=eq.id, upload_id=up.id, status=eq.status, availability_pct=eq.availability_pct, health_score=eq.health_score, downtime_hrs=eq.downtime_hrs))  # history point
    up.status = "Failed" if not up.rows_ok else "Validated" if dry_run else "Imported"
    return _finish(db, up, issues)


def process_stockpile(db: Session, text: str, filename: str, user_id: int | None, dry_run: bool):
    """Closing stockpile per mine and day (tonnes). An existing reading for the same mine and day is replaced (with a warning)."""
    up = Upload(kind="stockpile", filename=filename[:200], dry_run=dry_run, uploaded_by=user_id, status="Failed",
                 rows_total=0, rows_ok=0, rows_rejected=0, rows_warning=0, issues_total=0)
    issues: list[tuple[int, str, str, str]] = []
    reader = csv.DictReader(io.StringIO(text))
    cols = [STOCK_ALIASES.get(c, c) for c in ((c or "").strip().lower() for c in (reader.fieldnames or []))]
    missing = [c for c in STOCK_REQUIRED if c not in cols]
    if missing:
        issues.append((1, "header", "Error", f"Missing column(s): {', '.join(missing)}. Expected: {', '.join(STOCK_REQUIRED)}"))
        return _finish(db, up, issues)
    reader.fieldnames = cols
    mines = {m.name.lower(): m for m in db.scalars(select(Mine))}
    existing = {(r.mine_id, r.day): r for r in db.scalars(select(StockReading))}
    seen: set = set(); good: list[tuple[Mine, date, float]] = []
    for line, row in enumerate(reader, start=2):
        if not any(v.strip() for v in row.values() if isinstance(v, str)): continue  # blank line
        if up.rows_total >= MAX_ROWS:
            issues.append((line, "file", "Error", f"More than {MAX_ROWS} rows; the rest were ignored")); break
        up.rows_total += 1
        errs: list[tuple[str, str]] = []; warns: list[tuple[str, str]] = []
        name = (row.get("mine") or "").strip(); mine = mines.get(name.lower())
        if not mine: errs.append(("mine", f"Unknown mine '{name}'"))
        day = _date(row.get("date") or "")
        if day is None: errs.append(("date", "Date must look like 2026-09-30 (or 30.09.2026)"))
        elif day > date.today(): errs.append(("date", "Date is in the future"))
        val = _num(row.get("stockpile_t") or "")
        if val is None or val < 0: errs.append(("stockpile_t", "stockpile_t must be a number, 0 or more"))
        if not errs:
            if (mine.id, day) in seen: errs.append(("date", "Duplicate mine and date earlier in this file"))
            else:
                seen.add((mine.id, day))
                if val > mine.daily_target_t * 365: warns.append(("stockpile_t", f"{val:,.0f} t is more than a year of this mine's output. Please check."))
                old = existing.get((mine.id, day))
                if old: warns.append(("date", f"Replaces the earlier reading of {old.closing_t:,.0f} t for this day."))
                good.append((mine, day, val))
        issues += [(line, f, "Error", m) for f, m in errs] + [(line, f, "Warning", m) for f, m in warns]
        if errs: up.rows_rejected += 1
        else: up.rows_ok += 1
        if warns: up.rows_warning += 1
    if up.rows_total == 0: issues.append((1, "file", "Error", "The file has no data rows"))
    if good and not dry_run:
        db.add(up); db.flush()
        for mine, day, val in good:
            old = existing.get((mine.id, day))
            if old: old.closing_t = val; old.upload_id = up.id
            else: db.add(StockReading(mine_id=mine.id, day=day, closing_t=val, upload_id=up.id))
    up.status = "Failed" if not up.rows_ok else "Validated" if dry_run else "Imported"
    return _finish(db, up, issues)

