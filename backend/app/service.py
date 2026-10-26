"""Use cases behind the API: combine the dataset with the analysis functions for a request."""
from datetime import date
from typing import Literal

import numpy as np
import pandas as pd

from app import analysis, config
from app.data import Dataset

Mode = Literal["day_ahead", "horizon"]


def day_bounds(start: date, end: date) -> tuple[pd.Timestamp, pd.Timestamp]:
    """[start 00:00, end+1 00:00) in UTC, clipped to the pilot's delivery days."""
    first = max(pd.Timestamp(start, tz="UTC"), config.FIRST_DELIVERY_DAY)
    last = min(pd.Timestamp(end, tz="UTC"), config.LAST_DELIVERY_DAY)
    return first, last + pd.Timedelta(days=1)


def build_pairs(
    data: Dataset, start: date, end: date, mode: Mode, cutoff: str, horizon_h: float
) -> pd.DataFrame:
    """Forecast/actual pairs for every hourly target in the window, using the selection rule."""
    window_start, window_end = day_bounds(start, end)
    targets = pd.Series(pd.date_range(window_start, window_end, freq="h", inclusive="left"))
    if mode == "day_ahead":
        decision_times = analysis.day_ahead_decision_times(targets, cutoff)
    else:
        decision_times = analysis.horizon_decision_times(targets, horizon_h)
    selected = analysis.select_forecasts(data.forecasts, targets, decision_times)
    return analysis.pair_with_actuals(selected, data.actuals)


def series(data: Dataset, start: date, end: date, mode: Mode, cutoff: str, horizon_h: float) -> dict:
    """Half-hourly actuals with the selected hourly forecast, for the time-series chart."""
    window_start, window_end = day_bounds(start, end)
    actuals = data.actuals[
        (data.actuals["start_time"] >= window_start) & (data.actuals["start_time"] < window_end)
    ]
    pairs = build_pairs(data, start, end, mode, cutoff, horizon_h)
    points = actuals.merge(
        pairs[["start_time", "forecast", "publish_time", "horizon_h"]], on="start_time", how="left"
    )
    return {"points": records(points), "summary": jsonable(analysis.summarize(pairs))}


def day_view(data: Dataset, day: date, cutoff: str) -> dict:
    """What the trader sees for one delivery day: the forecast known at the cut-off, an error band
    from the pilot period, every forecast run for the day, and how it actually turned out."""
    day_start, day_end = day_bounds(day, day)
    decision_time = analysis.day_ahead_decision_times(pd.Series([day_start]), cutoff).iloc[0]
    pairs = build_pairs(data, day, day, "day_ahead", cutoff, 0)

    # Error band: 10th-90th percentile of day-ahead errors over the whole pilot, same cut-off.
    # actual = forecast - error, so the band is [forecast - p90, forecast - p10]. In-sample.
    all_pairs = build_pairs(
        data, config.FIRST_DELIVERY_DAY.date(), config.LAST_DELIVERY_DAY.date(), "day_ahead", cutoff, 0
    )
    p10, p90 = all_pairs["error"].quantile([0.10, 0.90])

    actuals = data.actuals[
        (data.actuals["start_time"] >= day_start) & (data.actuals["start_time"] < day_end)
    ]
    points = actuals.merge(pairs[["start_time", "forecast"]], on="start_time", how="left")
    points["band_low"] = points["forecast"] - p90
    points["band_high"] = points["forecast"] - p10

    # Every run published before the end of the day that covers it (for "how did the forecast evolve").
    runs = data.forecasts[
        (data.forecasts["start_time"] >= day_start)
        & (data.forecasts["start_time"] < day_end)
        & (data.forecasts["publish_time"] >= day_start - pd.Timedelta(days=2))
    ]
    run_list = [
        {
            "publish_time": iso(publish_time),
            "before_cutoff": bool(publish_time <= decision_time),
            "points": records(run[["start_time", "forecast"]]),
        }
        for publish_time, run in runs.groupby("publish_time")
    ]

    used_publish_time = pairs["publish_time"].iloc[0] if not pairs.empty else None
    return {
        "day": day.isoformat(),
        "decision_time": iso(decision_time),
        "used_publish_time": iso(used_publish_time) if used_publish_time is not None else None,
        "horizon_range_h": [float(pairs["horizon_h"].min()), float(pairs["horizon_h"].max())]
        if not pairs.empty
        else None,
        "band": {"p10": float(p10), "p90": float(p90)},
        "points": records(points),
        "runs": run_list,
        "summary": jsonable(analysis.summarize(pairs)),
    }


def accuracy(data: Dataset, start: date, end: date, mode: Mode, cutoff: str, horizon_h: float) -> dict:
    pairs = build_pairs(data, start, end, mode, cutoff, horizon_h)
    return {
        "summary": jsonable(analysis.summarize(pairs)),
        "by_hour": records(analysis.by_hour_of_day(pairs)),
        "by_day": records(analysis.by_day(pairs)),
        "by_level": records(analysis.by_forecast_level(pairs)),
        "histogram": records(analysis.histogram(pairs["error"])),
    }


def accuracy_by_horizon(data: Dataset, start: date, end: date, bucket_h: int) -> list[dict]:
    window_start, window_end = day_bounds(start, end)
    in_window = (data.forecasts["start_time"] >= window_start) & (
        data.forecasts["start_time"] < window_end
    )
    return records(analysis.by_horizon(data.forecasts[in_window], data.actuals, bucket_h=bucket_h))


# --- JSON helpers -------------------------------------------------------------------------------


def iso(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def jsonable(value):
    """Timestamps -> ISO strings, NaN -> None, floats rounded to 0.1 (MW precision is plenty)."""
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    if value is pd.NaT:
        return None
    if isinstance(value, pd.Timestamp):
        return iso(value)
    if isinstance(value, (float, np.floating)):
        return None if np.isnan(value) else round(float(value), 1)
    if isinstance(value, np.integer):
        return int(value)
    return value


def records(df: pd.DataFrame) -> list[dict]:
    return [jsonable(row) for row in df.to_dict("records")]
