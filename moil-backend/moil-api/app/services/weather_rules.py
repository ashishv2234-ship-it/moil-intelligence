"""Weather rules for the shortfall risk engine. No imports, so they are easy to test.

Only a FRESH observation counts, because old weather says nothing about today. Weather changes the
probability only; the risk level still comes from the production forecast.
"""
FRESH_HOURS = 12
EXTRA_PROBABILITY = {"Unsuitable": 10, "Caution": 4}


def weather_effect(blasting: str | None, age_hours: float | None) -> int:
    """Extra probability points (0 when there is no fresh observation or conditions are Suitable)."""
    if blasting is None or age_hours is None or age_hours > FRESH_HOURS: return 0
    return EXTRA_PROBABILITY.get(blasting, 0)


def weather_is_cause(blasting: str | None, age_hours: float | None, shortfall_pct: float) -> bool:
    """Name weather as the main cause only when blasting is unsuitable now AND a real shortfall is forecast."""
    return weather_effect(blasting, age_hours) == EXTRA_PROBABILITY["Unsuitable"] and shortfall_pct > 3


FORECAST_FRESH_HOURS = 24  # a forecast older than this is not shown


def forecast_status(rain_mm: float, wind_kmh: float) -> str:
    """Blasting suitability for a forecast DAY from its rain total and maximum wind. Same idea as the live rules, but a daily
    maximum wind is a stricter number than a spot reading, so treat this as an early warning, not a go/no-go."""
    if rain_mm >= 10 or wind_kmh >= 40: return "Unsuitable"
    if rain_mm >= 3 or wind_kmh >= 25: return "Caution"
    return "Suitable"
