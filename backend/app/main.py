"""FastAPI app: JSON API under /api, plus the built React app at / in production."""
from datetime import date

from fastapi import FastAPI, HTTPException, Query

from . import config, service
from .data import load_dataset

app = FastAPI(title="Wind Forecast Monitor", version="1.0.0")

CUTOFF = Query(config.DEFAULT_CUTOFF, pattern=r"^([01]\d|2[0-3]):[0-5]\d$", description="HH:MM UTC on D-1")
HORIZON = Query(24.0, ge=0, le=48, description="Hours ahead (horizon mode)")
START = Query(config.FIRST_DELIVERY_DAY.date())
END = Query(config.LAST_DELIVERY_DAY.date())


def _check_range(start: date, end: date) -> None:
    if start > end:
        raise HTTPException(status_code=422, detail="start must be on or before end")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/meta")
def meta() -> dict:
    data = load_dataset()
    run_times = sorted(data.forecasts["publish_time"].dt.strftime("%H:%M").unique())
    return {
        "first_day": config.FIRST_DELIVERY_DAY.date().isoformat(),
        "last_day": config.LAST_DELIVERY_DAY.date().isoformat(),
        "default_cutoff": config.DEFAULT_CUTOFF,
        "forecast_run_times_utc": run_times,
        "n_actuals": len(data.actuals),
        "n_forecast_runs": int(data.forecasts["publish_time"].nunique()),
        "source": "Elexon BMRS: FUELHH (fuelType=WIND) actuals, WINDFOR forecasts",
    }


@app.get("/api/day")
def day(day: date = Query(...), cutoff: str = CUTOFF) -> dict:
    if not config.FIRST_DELIVERY_DAY.date() <= day <= config.LAST_DELIVERY_DAY.date():
        raise HTTPException(status_code=404, detail="day is outside the pilot period")
    return service.day_view(load_dataset(), day, cutoff)


@app.get("/api/series")
def series(
    start: date = START,
    end: date = END,
    mode: service.Mode = "day_ahead",
    cutoff: str = CUTOFF,
    horizon_h: float = HORIZON,
) -> dict:
    _check_range(start, end)
    return service.series(load_dataset(), start, end, mode, cutoff, horizon_h)


@app.get("/api/accuracy")
def accuracy(
    start: date = START,
    end: date = END,
    mode: service.Mode = "day_ahead",
    cutoff: str = CUTOFF,
    horizon_h: float = HORIZON,
) -> dict:
    _check_range(start, end)
    return service.accuracy(load_dataset(), start, end, mode, cutoff, horizon_h)


@app.get("/api/accuracy/horizon")
def accuracy_by_horizon(
    start: date = START, end: date = END, bucket_h: int = Query(3, ge=1, le=12)
) -> list[dict]:
    _check_range(start, end)
    return service.accuracy_by_horizon(load_dataset(), start, end, bucket_h)


# The built React app (absent in dev/tests, where Vite serves it). API routes always take priority;
# on Vercel these files are promoted to the CDN at build time.
if config.STATIC_DIR.is_dir():
    app.frontend("/", directory=config.STATIC_DIR)
