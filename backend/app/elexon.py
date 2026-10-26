"""Download wind actuals (FUELHH) and wind forecasts (WINDFOR) from the Elexon BMRS API.

Run `python -m app.elexon` to refresh the CSV snapshot in backend/data/.
"""
import httpx
import pandas as pd

from . import config

CHUNK = pd.Timedelta(days=7)  # keep each request small; the stream endpoints return everything in range


def _fetch_stream(dataset: str, start: pd.Timestamp, end: pd.Timestamp, **params) -> list[dict]:
    rows: list[dict] = []
    with httpx.Client(base_url=config.ELEXON_BASE_URL, timeout=60) as client:
        chunk_start = start
        while chunk_start < end:
            chunk_end = min(chunk_start + CHUNK, end)
            response = client.get(
                f"/{dataset}/stream",
                params={
                    "publishDateTimeFrom": chunk_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "publishDateTimeTo": chunk_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    **params,
                },
            )
            response.raise_for_status()
            rows.extend(response.json())
            chunk_start = chunk_end
    return rows


def fetch_actuals() -> pd.DataFrame:
    """Half-hourly outturn wind generation (MW). FUELHH publishes each period 30 min after it starts."""
    rows = _fetch_stream(
        "FUELHH",
        config.ACTUAL_FROM,
        config.ACTUAL_TO + pd.Timedelta(minutes=30),
        fuelType="WIND",
    )
    df = pd.DataFrame(rows)
    df = df[df["fuelType"] == "WIND"]
    df = pd.DataFrame(
        {
            "start_time": pd.to_datetime(df["startTime"], utc=True),
            "publish_time": pd.to_datetime(df["publishTime"], utc=True),
            "actual": df["generation"].astype(float),
        }
    )
    # A period can be republished with a correction: keep the latest value.
    df = df.sort_values("publish_time").drop_duplicates("start_time", keep="last")
    in_scope = (df["start_time"] >= config.ACTUAL_FROM) & (df["start_time"] < config.ACTUAL_TO)
    return df.loc[in_scope, ["start_time", "actual"]].sort_values("start_time").reset_index(drop=True)


def fetch_forecasts() -> pd.DataFrame:
    """Every WINDFOR forecast run (hourly targets) published in the download window."""
    rows = _fetch_stream("WINDFOR", config.FORECAST_PUBLISH_FROM, config.FORECAST_PUBLISH_TO)
    df = pd.DataFrame(rows)
    df = pd.DataFrame(
        {
            "start_time": pd.to_datetime(df["startTime"], utc=True),
            "publish_time": pd.to_datetime(df["publishTime"], utc=True),
            "forecast": df["generation"].astype(float),
        }
    )
    df = df.drop_duplicates(["start_time", "publish_time"], keep="last")
    return df.sort_values(["publish_time", "start_time"]).reset_index(drop=True)


def refresh_snapshot() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    actuals = fetch_actuals()
    forecasts = fetch_forecasts()
    actuals.to_csv(config.ACTUALS_CSV, index=False)
    forecasts.to_csv(config.FORECASTS_CSV, index=False)
    print(f"Saved {len(actuals)} actuals -> {config.ACTUALS_CSV}")
    print(f"Saved {len(forecasts)} forecast rows -> {config.FORECASTS_CSV}")


if __name__ == "__main__":
    refresh_snapshot()
