"""Scope and settings for the v1 pilot.

All timestamps in the app are UTC. The pilot covers January 2026, when UK local time is GMT (= UTC),
so a "delivery day" is simply a UTC calendar day.
"""
import os
from pathlib import Path

import pandas as pd

ELEXON_BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"

# Purchase decisions made in January 2026 are for delivery days 2 Jan .. 1 Feb (decided the day before).
FIRST_DELIVERY_DAY = pd.Timestamp("2026-01-02", tz="UTC")
LAST_DELIVERY_DAY = pd.Timestamp("2026-02-01", tz="UTC")

# Download windows. Forecasts start a few days earlier so every delivery day has its longest-horizon
# forecasts (WINDFOR looks ~2.5 days ahead); actuals cover every half-hour of the delivery days.
FORECAST_PUBLISH_FROM = pd.Timestamp("2025-12-29", tz="UTC")
FORECAST_PUBLISH_TO = pd.Timestamp("2026-02-02", tz="UTC")
ACTUAL_FROM = FIRST_DELIVERY_DAY
ACTUAL_TO = LAST_DELIVERY_DAY + pd.Timedelta(days=1)

# Day-ahead decision cut-off on D-1. GB day-ahead auctions close ~09:20 (EPEX) and ~09:50 (N2EX)
# UK time, so 09:00 is the latest time a forecast can realistically feed into the bids.
DEFAULT_CUTOFF = "09:00"

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
ACTUALS_CSV = DATA_DIR / "fuelhh_wind.csv"
FORECASTS_CSV = DATA_DIR / "windfor.csv"

# Built React app, served by FastAPI in the single production container.
STATIC_DIR = Path(os.getenv("STATIC_DIR", Path(__file__).resolve().parent.parent / "static"))
