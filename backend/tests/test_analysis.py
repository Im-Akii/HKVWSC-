import math

import pandas as pd
import pytest

from app import analysis


def ts(value: str) -> pd.Timestamp:
    return pd.Timestamp(value, tz="UTC")


def forecasts_frame(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    """rows: (start_time, publish_time, forecast)"""
    return pd.DataFrame(
        {
            "start_time": [ts(r[0]) for r in rows],
            "publish_time": [ts(r[1]) for r in rows],
            "forecast": [float(r[2]) for r in rows],
        }
    )


def actuals_frame(rows: list[tuple[str, float]]) -> pd.DataFrame:
    return pd.DataFrame({"start_time": [ts(r[0]) for r in rows], "actual": [float(r[1]) for r in rows]})


def test_true_forecasts_drops_past_targets_and_adds_horizon():
    raw = forecasts_frame(
        [
            ("2026-01-10 06:00", "2026-01-10 07:30", 100),  # already in the past: not a forecast
            ("2026-01-10 08:00", "2026-01-10 07:30", 200),
            ("2026-01-11 07:30", "2026-01-10 07:30", 300),
        ]
    )
    result = analysis.true_forecasts(raw)
    assert list(result["forecast"]) == [200, 300]
    assert list(result["horizon_h"]) == [0.5, 24.0]


def test_day_ahead_decision_time_is_cutoff_on_previous_day():
    targets = pd.Series([ts("2026-01-15 00:00"), ts("2026-01-15 23:00")])
    decision = analysis.day_ahead_decision_times(targets, "09:00")
    assert list(decision) == [ts("2026-01-14 09:00"), ts("2026-01-14 09:00")]


def test_horizon_decision_time():
    targets = pd.Series([ts("2026-01-15 12:00")])
    assert analysis.horizon_decision_times(targets, 24).iloc[0] == ts("2026-01-14 12:00")


def test_select_takes_latest_run_published_at_or_before_decision_time():
    forecasts = analysis.true_forecasts(
        forecasts_frame(
            [
                ("2026-01-15 12:00", "2026-01-14 04:30", 1000),
                ("2026-01-15 12:00", "2026-01-14 09:00", 2000),  # exactly at cut-off: allowed
                ("2026-01-15 12:00", "2026-01-14 09:30", 3000),  # after cut-off: not known yet
            ]
        )
    )
    targets = pd.Series([ts("2026-01-15 12:00")])
    selected = analysis.select_forecasts(
        forecasts, targets, analysis.day_ahead_decision_times(targets, "09:00")
    )
    assert len(selected) == 1
    assert selected.loc[0, "forecast"] == 2000
    assert selected.loc[0, "publish_time"] == ts("2026-01-14 09:00")
    assert selected.loc[0, "horizon_h"] == 27.0


def test_select_matches_runs_per_target_and_drops_targets_without_forecast():
    forecasts = analysis.true_forecasts(
        forecasts_frame(
            [
                ("2026-01-15 10:00", "2026-01-14 07:30", 10),
                ("2026-01-15 11:00", "2026-01-14 07:30", 11),
                ("2026-01-15 11:00", "2026-01-14 08:30", 21),
            ]
        )
    )
    targets = pd.Series([ts("2026-01-15 10:00"), ts("2026-01-15 11:00"), ts("2026-01-15 12:00")])
    selected = analysis.select_forecasts(
        forecasts, targets, analysis.day_ahead_decision_times(targets, "09:00")
    )
    assert list(selected["start_time"]) == [ts("2026-01-15 10:00"), ts("2026-01-15 11:00")]
    assert list(selected["forecast"]) == [10, 21]


def test_select_in_horizon_mode_respects_horizon():
    forecasts = analysis.true_forecasts(
        forecasts_frame(
            [
                ("2026-01-15 12:00", "2026-01-14 11:30", 1),  # 24.5 h ahead
                ("2026-01-15 12:00", "2026-01-15 02:30", 2),  # 9.5 h ahead
            ]
        )
    )
    targets = pd.Series([ts("2026-01-15 12:00")])
    at_24h = analysis.select_forecasts(forecasts, targets, analysis.horizon_decision_times(targets, 24))
    at_4h = analysis.select_forecasts(forecasts, targets, analysis.horizon_decision_times(targets, 4))
    assert at_24h.loc[0, "forecast"] == 1
    assert at_4h.loc[0, "forecast"] == 2


@pytest.fixture
def pairs() -> pd.DataFrame:
    forecasts = analysis.true_forecasts(
        forecasts_frame(
            [
                ("2026-01-15 00:00", "2026-01-14 07:30", 100),
                ("2026-01-15 01:00", "2026-01-14 07:30", 200),
                ("2026-01-15 02:00", "2026-01-14 07:30", 300),
                ("2026-01-15 03:00", "2026-01-14 07:30", 400),
            ]
        )
    )
    actuals = actuals_frame(
        [
            ("2026-01-15 00:00", 110),
            ("2026-01-15 00:30", 999),  # half-hour actual: never scored
            ("2026-01-15 01:00", 180),
            ("2026-01-15 02:00", 300),
            ("2026-01-15 03:00", 500),
        ]
    )
    targets = pd.Series(pd.date_range(ts("2026-01-15 00:00"), periods=4, freq="h"))
    selected = analysis.select_forecasts(
        forecasts, targets, analysis.day_ahead_decision_times(targets, "09:00")
    )
    return analysis.pair_with_actuals(selected, actuals)


def test_pair_with_actuals_computes_forecast_minus_actual(pairs):
    assert list(pairs["error"]) == [-10, 20, 0, -100]


def test_summarize_metrics(pairs):
    summary = analysis.summarize(pairs)
    assert summary["n"] == 4
    assert summary["mae"] == pytest.approx(32.5)
    assert summary["rmse"] == pytest.approx(math.sqrt((100 + 400 + 0 + 10000) / 4))
    assert summary["bias"] == pytest.approx(-22.5)
    assert summary["mean_actual"] == pytest.approx(272.5)
    assert summary["nmae_pct"] == pytest.approx(32.5 / 272.5 * 100)
    assert summary["pct_over_forecast"] == pytest.approx(25.0)
    assert (summary["horizon_h_min"], summary["horizon_h_max"]) == (16.5, 19.5)
    assert summary["error_quantiles"]["p50"] == pytest.approx(-5.0)
    assert summary["worst_over"] == {"time": ts("2026-01-15 01:00"), "error": 20.0}
    assert summary["worst_under"] == {"time": ts("2026-01-15 03:00"), "error": -100.0}


def test_summarize_empty():
    empty = pd.DataFrame(columns=["start_time", "forecast", "actual", "error"])
    assert analysis.summarize(empty) == {"n": 0}


def test_by_hour_of_day(pairs):
    stats = analysis.by_hour_of_day(pairs)
    assert list(stats["hour"]) == [0, 1, 2, 3]
    assert list(stats["mae"]) == [10, 20, 0, 100]


def test_by_horizon_buckets_every_run():
    forecasts = analysis.true_forecasts(
        forecasts_frame(
            [
                ("2026-01-15 12:00", "2026-01-15 11:00", 110),  # 1 h  -> bucket 0-3
                ("2026-01-15 12:00", "2026-01-15 07:30", 130),  # 4.5 h -> bucket 3-6
                ("2026-01-15 13:00", "2026-01-15 11:00", 90),  # 2 h  -> bucket 0-3
                ("2026-01-15 12:00", "2026-01-12 11:00", 500),  # 73 h -> beyond max_h, ignored
            ]
        )
    )
    actuals = actuals_frame([("2026-01-15 12:00", 100), ("2026-01-15 13:00", 100)])
    stats = analysis.by_horizon(forecasts, actuals, bucket_h=3, max_h=48)
    assert list(stats["horizon_from_h"]) == [0, 3]
    assert list(stats["horizon_to_h"]) == [3, 6]
    assert list(stats["n"]) == [2, 1]
    assert list(stats["mae"]) == [10, 30]
    assert list(stats["bias"]) == [0, 30]


def test_by_forecast_level(pairs):
    stats = analysis.by_forecast_level(pairs, bin_mw=250)
    assert list(stats["level_from"]) == [0, 250]
    assert list(stats["n"]) == [2, 2]


def test_histogram_counts_every_error():
    errors = pd.Series([-600.0, -100.0, 0.0, 250.0, 1000.0])
    hist = analysis.histogram(errors, bin_mw=500)
    assert hist["bin_from"].iloc[0] == -1000
    assert hist["bin_to"].iloc[-1] == 1000
    assert hist["count"].sum() == len(errors)
    assert list(hist["count"]) == [1, 1, 2, 1]
