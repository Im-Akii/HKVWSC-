"""Load the cached Elexon snapshot (downloading it on first run if the CSVs are missing)."""
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from app import analysis, config, elexon


@dataclass(frozen=True)
class Dataset:
    actuals: pd.DataFrame  # start_time, actual (half-hourly MW)
    forecasts: pd.DataFrame  # start_time, publish_time, forecast, horizon_h (true forecasts only)


@lru_cache
def load_dataset() -> Dataset:
    if not (config.ACTUALS_CSV.exists() and config.FORECASTS_CSV.exists()):
        elexon.refresh_snapshot()
    actuals = pd.read_csv(config.ACTUALS_CSV)
    forecasts = pd.read_csv(config.FORECASTS_CSV)
    for df, columns in ((actuals, ["start_time"]), (forecasts, ["start_time", "publish_time"])):
        for column in columns:
            df[column] = pd.to_datetime(df[column], utc=True)
    return Dataset(actuals=actuals, forecasts=analysis.true_forecasts(forecasts))
