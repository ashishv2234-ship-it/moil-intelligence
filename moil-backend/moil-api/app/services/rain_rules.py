"""Rainfall rules for the shortfall risk engine. No imports, so they are easy to test.

Input is the last-30-days rainfall (mm) at the mine's grid cell from the satellite layer. Heavy recent rain waterlogs pits and
haul roads and slows loading and hauling. Like weather, rainfall changes the probability only; the risk level still comes from
the production forecast. The thresholds are expert assumptions, not learned values: change them here if MOIL's own data says otherwise.
"""
FRESH_DAYS = 7          # older rainfall data says little about the ground today
WET_MM, VERY_WET_MM = 150, 300
EXTRA_PROBABILITY = {"Very wet": 6, "Wet": 3}


def rain_class(mm: float | None, age_days: int | None) -> str | None:
    """'Very wet', 'Wet' or None (no fresh data, or not wet)."""
    if mm is None or age_days is None or age_days > FRESH_DAYS: return None
    return "Very wet" if mm >= VERY_WET_MM else "Wet" if mm >= WET_MM else None


def rain_effect(mm: float | None, age_days: int | None) -> int:
    """Extra probability points (0 when data is missing, stale or not wet)."""
    return EXTRA_PROBABILITY.get(rain_class(mm, age_days) or "", 0)


def rain_is_cause(mm: float | None, age_days: int | None, shortfall_pct: float) -> bool:
    """Name wet ground as the main cause only when it is very wet AND a real shortfall is forecast."""
    return rain_class(mm, age_days) == "Very wet" and shortfall_pct > 3
