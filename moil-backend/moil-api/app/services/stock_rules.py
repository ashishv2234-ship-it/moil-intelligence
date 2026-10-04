"""Stockpile rules for the shortfall risk engine. No imports, so they are easy to test.

Days of cover = the mine's newest stockpile reading divided by its daily target. A thin stockpile leaves little buffer if
output falls short, so it adds a few probability points. A big stockpile never lowers the probability (it does not make
the mine produce more). Like weather and rain, stockpile changes the probability only; the risk level still comes from the
production forecast. The thresholds are expert assumptions, not learned values: change them here if MOIL's data says otherwise.
"""
FRESH_DAYS = 7          # an older reading says little about the stockpile today
VERY_LOW_DAYS, LOW_DAYS = 2, 5
EXTRA_PROBABILITY = {"Very low": 4, "Low": 2}


def cover_days(stock_t: float | None, daily_target_t: float) -> float | None:
    """Days of target output the stockpile covers (None when there is no reading or no target)."""
    if stock_t is None or daily_target_t <= 0: return None
    return stock_t / daily_target_t


def stock_class(cover: float | None, age_days: int | None) -> str | None:
    """'Very low', 'Low' or None (no fresh reading, or enough cover)."""
    if cover is None or age_days is None or age_days > FRESH_DAYS or age_days < 0: return None
    return "Very low" if cover < VERY_LOW_DAYS else "Low" if cover < LOW_DAYS else None


def stock_effect(cover: float | None, age_days: int | None) -> int:
    """Extra probability points (0 when data is missing, stale or the cover is enough)."""
    return EXTRA_PROBABILITY.get(stock_class(cover, age_days) or "", 0)
