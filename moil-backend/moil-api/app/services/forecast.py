"""Baseline forecasting: seasonal-naive (same weekday, last 4 weeks) blended with a 14-day moving average.
Swap `forecast()` for XGBoost/LightGBM later; keep the return shape.

Outlier handling: before averaging, the last 56 days are checked with a robust rule (median and MAD). A day far ABOVE
the normal range, for example a mistyped 4,200 t at a 1,500 t mine, is replaced by the median so it cannot drag the
forecast or widen the confidence band. Low days are kept, because breakdowns and stoppages are real. If more than a
quarter of the days look unusual, the data probably shows a real change in production, so nothing is replaced.

Seasonality: when at least about a year of dated history is supplied, a monthly index is learned (a month's average output
divided by the overall average, limited to 0.7 to 1.3). History is divided by it before the level is measured, and the
forecast is multiplied by the index of the month being forecast. A monsoon dip therefore is not mistaken for a lasting
trend, and recovery after the monsoon is expected. With less than a year of data, no adjustment is made."""
from datetime import date, timedelta
import numpy as np

WINDOW, K, MAX_SHARE = 56, 4.0, 0.25
MIN_DAYS, MIN_PER_MONTH, IDX_LO, IDX_HI = 330, 10, 0.7, 1.3


def clean_history(history: list[float]) -> tuple[np.ndarray, int]:
    """Returns (cleaned history, number of days replaced). Only the last WINDOW days are changed."""
    h = np.array(history, dtype=float)
    w = h[-WINDOW:]
    med = float(np.median(w))
    scale = max(1.4826 * float(np.median(np.abs(w - med))), 0.03 * abs(med), 1.0)  # floor stops a zero MAD flagging everything
    hi = med + K * scale
    bad = w > hi
    if not bad.any() or bad.mean() > MAX_SHARE:
        return h, 0
    h[-len(w):] = np.where(bad, med, w)
    return h, int(bad.sum())


def monthly_index(history: list[float], dates: list[date]) -> dict[int, float] | None:
    """Month number (1-12) -> seasonal factor, or None when there is not enough dated history."""
    if len(history) != len(dates) or len(history) < MIN_DAYS: return None
    overall = float(np.mean(history))
    if overall <= 0: return None
    idx = {}
    for m in range(1, 13):
        v = [x for x, d in zip(history, dates) if d.month == m]
        idx[m] = min(max(float(np.mean(v)) / overall, IDX_LO), IDX_HI) if len(v) >= MIN_PER_MONTH else 1.0
    return idx


def forecast_full(history: list[float], horizon: int = 30, dates: list[date] | None = None) -> dict:
    """Returns {"points": [...], "capped": days replaced as outliers, "seasonal": whether a seasonal adjustment was used}."""
    if len(history) < 28: raise ValueError("Need at least 28 days of history")
    idx = monthly_index(history, dates) if dates else None
    h = np.array(history, dtype=float)
    if idx: h = h / np.array([idx[d.month] for d in dates])
    h, capped = clean_history(h)
    ma, sd = h[-14:].mean(), h[-56:].std() if len(h) >= 56 else h.std()
    out = []
    for i in range(horizon):
        k = idx[(dates[-1] + timedelta(days=i + 1)).month] if idx else 1.0
        f = (0.5 * ma + 0.5 * h[-28:][(i % 7)::7].mean()) * k
        out.append({"day_offset": i + 1, "forecast_t": round(f), "lower_t": round(f - 1.28 * sd * k), "upper_t": round(f + 1.28 * sd * k)})
    return {"points": out, "capped": capped, "seasonal": idx is not None}


def forecast_with_info(history: list[float], horizon: int = 30, dates: list[date] | None = None) -> tuple[list[dict], int]:
    r = forecast_full(history, horizon, dates); return r["points"], r["capped"]


def forecast(history: list[float], horizon: int = 30, dates: list[date] | None = None) -> list[dict]:
    return forecast_full(history, horizon, dates)["points"]
