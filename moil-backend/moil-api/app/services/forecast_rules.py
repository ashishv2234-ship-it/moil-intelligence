"""Forecast-weather rules for the shortfall risk engine. No imports, so they are easy to test.

Input is the blasting suitability of the NEXT 7 DAYS after today (tomorrow to today+7), taken from the stored daily forecast.
Today is left out on purpose: the live weather reading already covers it, so it is never counted twice.
Like the live weather and the rainfall rules, this changes the probability only; the risk level still comes from the
production forecast. The numbers below are expert assumptions, not learned values: change them here if MOIL's own data says otherwise.
"""
MIN_DAYS = 5                      # fewer forecast days than this is too little to judge a week
MANY_UNSUITABLE = 3               # this many unsuitable days in the week = a disrupted week
EXTRA_PROBABILITY = {"disrupted": 5, "some": 2}


def forecast_effect(statuses: list[str]) -> int:
    """Extra probability points from the coming week: 5 for 3 or more unsuitable days, 2 for 1 or 2, else 0.
    Caution days do not count. Returns 0 when fewer than MIN_DAYS days are known."""
    if len(statuses) < MIN_DAYS: return 0
    n = statuses.count("Unsuitable")
    return EXTRA_PROBABILITY["disrupted"] if n >= MANY_UNSUITABLE else EXTRA_PROBABILITY["some"] if n >= 1 else 0
