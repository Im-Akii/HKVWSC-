"""API tests on a small synthetic dataset (no network, no dependency on the CSV snapshot)."""
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import analysis, main
from app.data import Dataset


def synthetic_dataset() -> Dataset:
    # Actuals: constant 10 GW for 2-3 Jan. Forecast runs at 07:30 and 09:30 each day, 48 h ahead;
    # the 07:30 run is 1 GW too high, the 09:30 run is spot on.
    actual_times = pd.date_range("2026-01-02", "2026-01-04", freq="30min", inclusive="left", tz="UTC")
    actuals = pd.DataFrame({"start_time": actual_times, "actual": 10_000.0})
    rows = []
    for day in pd.date_range("2025-12-31", "2026-01-03", freq="D", tz="UTC"):
        for run, value in (("07:30", 11_000.0), ("09:30", 10_000.0)):
            publish = day + pd.Timedelta(f"{run}:00")
            for target in pd.date_range(publish.ceil("h"), periods=48, freq="h"):
                rows.append((target, publish, value))
    forecasts = pd.DataFrame(rows, columns=["start_time", "publish_time", "forecast"])
    return Dataset(actuals=actuals, forecasts=analysis.true_forecasts(forecasts))


@pytest.fixture
def client(monkeypatch) -> TestClient:
    dataset = synthetic_dataset()
    monkeypatch.setattr(main, "load_dataset", lambda: dataset)
    return TestClient(main.app)


def test_accuracy_uses_cutoff(client):
    params = {"start": "2026-01-02", "end": "2026-01-03"}
    before = client.get("/api/accuracy", params={**params, "cutoff": "09:00"}).json()
    after = client.get("/api/accuracy", params={**params, "cutoff": "10:00"}).json()
    assert before["summary"]["n"] == 48
    assert before["summary"]["bias"] == 1000  # only the 07:30 run was known at 09:00
    assert after["summary"]["mae"] == 0  # the 09:30 run is known at 10:00
    assert len(before["by_hour"]) == 24
    assert len(before["by_day"]) == 2


def test_horizon_mode(client):
    response = client.get(
        "/api/accuracy", params={"mode": "horizon", "horizon_h": 1, "start": "2026-01-03", "end": "2026-01-03"}
    )
    assert response.status_code == 200
    assert response.json()["summary"]["n"] == 24


def test_day_view(client):
    body = client.get("/api/day", params={"day": "2026-01-03", "cutoff": "09:00"}).json()
    assert body["decision_time"] == "2026-01-02T09:00:00Z"
    assert body["used_publish_time"] == "2026-01-02T07:30:00Z"
    assert len(body["points"]) == 48  # half-hourly actuals
    assert body["points"][0]["forecast"] == 11000
    assert body["points"][1]["forecast"] is None  # hh:30 has no hourly forecast
    assert {run["before_cutoff"] for run in body["runs"]} == {True, False}


def test_series_and_horizon_endpoints(client):
    series = client.get("/api/series", params={"start": "2026-01-02", "end": "2026-01-02"}).json()
    assert len(series["points"]) == 48
    horizon = client.get("/api/accuracy/horizon", params={"bucket_h": 6}).json()
    assert horizon[0]["horizon_from_h"] == 0


@pytest.mark.parametrize(
    "path, params",
    [
        ("/api/accuracy", {"cutoff": "25:00"}),
        ("/api/accuracy", {"mode": "weekly"}),
        ("/api/accuracy", {"start": "2026-01-10", "end": "2026-01-05"}),
        ("/api/series", {"horizon_h": 100}),
    ],
)
def test_invalid_params_are_rejected(client, path, params):
    assert client.get(path, params=params).status_code == 422


def test_day_outside_pilot_is_404(client):
    assert client.get("/api/day", params={"day": "2026-03-01"}).status_code == 404
