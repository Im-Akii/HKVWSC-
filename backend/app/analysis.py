"""Core analysis: pick the forecast that was known at decision time, then score it against actuals.

Pure functions on DataFrames (no I/O) so they are easy to test.

Conventions
- Timestamps are tz-aware UTC.
- error = forecast - actual (MW). Positive error = wind was over-forecast, so a buyer relying on the
  forecast would be short and have to buy the gap later (intraday / imbalance).
- WINDFOR targets are hourly, FUELHH actuals half-hourly. A forecast for hh:00 is scored against the
  settlement period that starts at hh:00; hh:30 actuals are charted but not scored.
"""
import numpy as np
import pandas as pd

ERROR_QUANTILES = [0.05, 0.10, 0.50, 0.90, 0.95]


def true_forecasts(forecasts: pd.DataFrame) -> pd.DataFrame:
    """Drop rows whose target time is before the publish time and add the forecast horizon.

    Each WINDFOR run also repeats a few hours that are already in the past; those rows are not
    forecasts and would flatter the accuracy figures.
    """
    horizon_h = (forecasts["start_time"] - forecasts["publish_time"]).dt.total_seconds() / 3600
    return forecasts.assign(horizon_h=horizon_h)[horizon_h >= 0].reset_index(drop=True)


def day_ahead_decision_times(targets: pd.Series, cutoff: str) -> pd.Series:
    """Decision time for each target = the cut-off ("HH:MM") on the day before its delivery day."""
    hours, minutes = (int(part) for part in cutoff.split(":"))
    return targets.dt.normalize() - pd.Timedelta(days=1) + pd.Timedelta(hours=hours, minutes=minutes)


def horizon_decision_times(targets: pd.Series, horizon_h: float) -> pd.Series:
    """Decision time for each target = a fixed number of hours before it."""
    return targets - pd.Timedelta(hours=horizon_h)


def select_forecasts(
    forecasts: pd.DataFrame, targets: pd.Series, decision_times: pd.Series
) -> pd.DataFrame:
    """For each target time, take the latest forecast published at or before its decision time.

    `forecasts` must already be filtered with `true_forecasts`. Targets with no forecast available
    by their decision time are dropped.
    """
    left = pd.DataFrame(
        {"start_time": targets.to_numpy(), "decision_time": decision_times.to_numpy()}
    ).sort_values("decision_time")
    right = forecasts[["start_time", "publish_time", "forecast", "horizon_h"]].sort_values(
        "publish_time"
    )
    selected = pd.merge_asof(
        left,
        right,
        left_on="decision_time",
        right_on="publish_time",
        by="start_time",
        direction="backward",  # latest publish_time <= decision_time
    )
    return selected.dropna(subset=["forecast"]).sort_values("start_time").reset_index(drop=True)


def pair_with_actuals(selected: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    """Join selected forecasts to actuals on target time and compute the error."""
    pairs = selected.merge(actuals[["start_time", "actual"]], on="start_time", how="inner")
    return pairs.assign(error=pairs["forecast"] - pairs["actual"])


def summarize(pairs: pd.DataFrame) -> dict:
    """Headline accuracy metrics for a set of forecast/actual pairs."""
    error = pairs["error"]
    if error.empty:
        return {"n": 0}
    abs_error = error.abs()
    mean_actual = pairs["actual"].mean()
    worst_over = pairs.loc[error.idxmax()]
    worst_under = pairs.loc[error.idxmin()]
    return {
        "n": int(len(error)),
        "mae": float(abs_error.mean()),
        "rmse": float(np.sqrt((error**2).mean())),
        "bias": float(error.mean()),
        "mean_actual": float(mean_actual),
        "nmae_pct": float(abs_error.mean() / mean_actual * 100) if mean_actual else None,
        "abs_error_p50": float(abs_error.quantile(0.5)),
        "abs_error_p90": float(abs_error.quantile(0.9)),
        "error_quantiles": {f"p{round(q * 100):02d}": float(error.quantile(q)) for q in ERROR_QUANTILES},
        "pct_over_forecast": float((error > 0).mean() * 100),
        "horizon_h_min": float(pairs["horizon_h"].min()),
        "horizon_h_max": float(pairs["horizon_h"].max()),
        "worst_over": {"time": worst_over["start_time"], "error": float(worst_over["error"])},
        "worst_under": {"time": worst_under["start_time"], "error": float(worst_under["error"])},
    }


def _grouped_errors(pairs: pd.DataFrame, key: pd.Series) -> pd.DataFrame:
    grouped = pairs.assign(abs_error=pairs["error"].abs(), sq_error=pairs["error"] ** 2).groupby(key)
    stats = grouped.agg(
        n=("error", "size"),
        mae=("abs_error", "mean"),
        mse=("sq_error", "mean"),
        bias=("error", "mean"),
        mean_actual=("actual", "mean"),
    )
    stats["rmse"] = np.sqrt(stats.pop("mse"))
    return stats.reset_index()


def by_hour_of_day(pairs: pd.DataFrame) -> pd.DataFrame:
    return _grouped_errors(pairs, pairs["start_time"].dt.hour.rename("hour"))


def by_day(pairs: pd.DataFrame) -> pd.DataFrame:
    return _grouped_errors(pairs, pairs["start_time"].dt.strftime("%Y-%m-%d").rename("day"))


def by_forecast_level(pairs: pd.DataFrame, bin_mw: int = 4000) -> pd.DataFrame:
    """Errors grouped by how much wind was forecast (does the error depend on the wind level?)."""
    level = (pairs["forecast"] // bin_mw * bin_mw).astype(int).rename("level_from")
    stats = _grouped_errors(pairs, level)
    stats["level_to"] = stats["level_from"] + bin_mw
    return stats


def by_horizon(
    forecasts: pd.DataFrame, actuals: pd.DataFrame, bucket_h: int = 3, max_h: int = 48
) -> pd.DataFrame:
    """Error of every forecast run against actuals, grouped into horizon buckets.

    Uses all runs (not just the one chosen at the cut-off), so it shows how accuracy decays the
    further ahead the forecast looks. `forecasts` must be filtered with `true_forecasts`.
    """
    pairs = pair_with_actuals(forecasts[forecasts["horizon_h"] < max_h], actuals)
    bucket = (pairs["horizon_h"] // bucket_h * bucket_h).astype(int).rename("horizon_from_h")
    stats = _grouped_errors(pairs, bucket)
    stats["horizon_to_h"] = stats["horizon_from_h"] + bucket_h
    return stats


def histogram(errors: pd.Series, bin_mw: int = 500) -> pd.DataFrame:
    """Counts of signed errors in fixed-width MW bins."""
    if errors.empty:
        return pd.DataFrame(columns=["bin_from", "bin_to", "count"])
    low = np.floor(errors.min() / bin_mw) * bin_mw
    high = max(np.ceil(errors.max() / bin_mw) * bin_mw, low + bin_mw)
    # np.histogram counts a value equal to the last edge in the last bin.
    counts, edges = np.histogram(errors, bins=np.arange(low, high + bin_mw / 2, bin_mw))
    return pd.DataFrame({"bin_from": edges[:-1], "bin_to": edges[1:], "count": counts})
