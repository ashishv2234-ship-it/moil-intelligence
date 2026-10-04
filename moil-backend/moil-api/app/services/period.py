"""Custom date range (from/to) checks shared by the dashboard and reports. No imports from the app, so it is easy to test."""
from datetime import date

MAX_DAYS = 366


def check_range(date_from: date | None, date_to: date | None, today: date | None = None) -> tuple[date, date] | None:
    """Returns (from, to) for a valid custom range, None when no range is given, or raises ValueError with a plain message."""
    if date_from is None and date_to is None: return None
    if date_from is None or date_to is None: raise ValueError("Give both a from date and a to date")
    if date_from > date_to: raise ValueError("The from date must be on or before the to date")
    if date_to > (today or date.today()): raise ValueError("The to date cannot be in the future")
    if (date_to - date_from).days + 1 > MAX_DAYS: raise ValueError(f"The range can be at most {MAX_DAYS} days")
    return date_from, date_to
