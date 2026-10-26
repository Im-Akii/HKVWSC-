# Wind Forecast Monitor

A v1 web app for a UK utility's day-ahead power buying desk. It answers two questions for national
(GB) wind generation, using Elexon BMRS data for purchase decisions made in **January 2026**:

1. **What wind forecast did we have when we had to bid?** For any delivery day, it shows the latest
   forecast published before the day-ahead decision cut-off, alongside what actually happened.
2. **How wrong is that forecast, and in which direction?** MAE, RMSE, bias, error percentiles
   ("planning buffers"), and how the error changes with forecast horizon, time of day and wind level.

**Live app:** https://my-sable-three.vercel.app/ (API docs: https://my-sable-three.vercel.app/docs)

Stack: React (Vite, Recharts) · Python (FastAPI, pandas) · Docker (local) · Vercel (hosting).

---

## Quick start

### With Docker (recommended)

```bash
docker compose up --build
```

Open http://localhost:8000. One container serves both the API (`/api/...`, docs at `/docs`) and the
built React app.

### Without Docker (development, hot reload)

Prerequisites: Python 3.11+, Node 20+.

```bash
# Terminal 1: API on :8000
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2: React dev server on :5173 (proxies /api to :8000)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

### Tests

```bash
cd backend
pytest
```

22 tests: the forecast-selection and metric logic (`tests/test_analysis.py`) and the API on a small
synthetic dataset (`tests/test_api.py`). GitHub Actions runs the tests, the frontend build and the
Docker build on every push.

### Refreshing the data

The January 2026 data is committed as a CSV snapshot in `backend/data/` so the app starts instantly
and doesn't depend on Elexon being up. To re-download it:

```bash
cd backend
python -m app.elexon
```

If the CSVs are missing, the API downloads them automatically on the first request.

---

## How the analysis works

### Data (Elexon BMRS, no API key needed)

| What | Stream | Resolution | Notes |
|---|---|---|---|
| Actual wind generation | `FUELHH`, `fuelType=WIND` | half-hourly | `startTime` = start of the settlement period |
| Wind forecasts | `WINDFOR` | hourly | `publishTime` = when the run was issued; ~8 runs a day (02:30, 04:30, 07:30, 09:30, 11:30, 15:30, 18:30, 22:30 UTC), each looking up to ~2.5 days ahead |

Scope: delivery days **2 Jan – 1 Feb 2026** (the days bought in January), with forecasts published
from 29 Dec so every day has its long-horizon forecasts.

### Choosing "the forecast known at decision time"

Each WINDFOR run also re-publishes a few hours that are already in the past (about 20% of rows).
Those are not forecasts, so they are dropped first (`horizon = startTime − publishTime ≥ 0`).

Two selection rules, both selectable in the app:

- **Day-ahead cut-off (default).** For every hour of delivery day D, take the latest run published at
  or before the cut-off on D-1. The default cut-off is **09:00 UK time**, just before the GB
  day-ahead auctions close (EPEX ~09:20, N2EX ~09:50). With 09:00 that's the 07:30 run, which looks
  16.5–39.5 h ahead. This mirrors what the desk actually had.
- **Fixed horizon.** For every target hour T, take the latest run published at least *h* hours before
  T (0–48 h). Useful to compare horizons like-for-like.

Implementation: one `pandas.merge_asof(..., by="start_time", direction="backward")` in
[`backend/app/analysis.py`](backend/app/analysis.py).

Hourly forecasts are scored against the half-hour that starts at the same time (`hh:00`); `hh:30`
actuals are charted but not scored. January is GMT, so UTC = UK time throughout.

### Metrics

Error = forecast − actual (MW). Positive = wind over-forecast, so a buyer relying on it is **short**.

- **MAE**, **RMSE** (penalises big misses), **bias** (mean error), MAE as % of mean output.
- **Error percentiles** → planning buffers: "in 90% of hours actual wind was no more than X MW below
  the forecast".
- Breakdowns by **horizon** (every run, 3-hour buckets), **hour of day**, **forecast wind level** and
  **delivery day**, plus the error **distribution**.

### What January 2026 shows (09:00 cut-off)

| Metric | Value |
|---|---|
| MAE | 2,023 MW (17.9% of mean output of 11.3 GW) |
| RMSE | 2,497 MW |
| Bias | **+1,746 MW**: over-forecast in 85% of hours |
| 90% / 95% shortfall buffer | 4,154 MW / 5,268 MW |
| MAE by horizon | ~1.65 GW at 0–6 h → ~2.0 GW at 24 h → ~2.35 GW at 45–48 h |

The over-forecast grows with the wind level (+0.3 GW when 4–8 GW is forecast, +4.5 GW above 20 GW);
actual output never exceeded 17.8 GW while forecasts reached 21 GW. A plausible cause is
**curtailment**: in high wind, transmission constraints turn wind farms down, so metered output
(FUELHH) is below what the weather supported. This app does not prove that; it would need
balancing-mechanism data (e.g. BOALF) to confirm.

### Limits (stated in the app too)

- One winter month is a small sample; buffers should be re-estimated on a longer history.
- The error band on the day view is in-sample (estimated over the same month it is drawn on).
- National wind only; FUELHH covers transmission-metered wind, not embedded (distribution) wind.

---

## Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI routes (/api/...) + serves the built React app
│   │   ├── service.py     # use cases: builds pairs for a request, day view, JSON shaping
│   │   ├── analysis.py    # pure analysis: forecast selection, metrics, breakdowns (unit-tested)
│   │   ├── data.py        # loads the CSV snapshot (downloads it if missing), cached in memory
│   │   ├── elexon.py      # Elexon BMRS client: FUELHH + WINDFOR streams → CSV (`python -m app.elexon`)
│   │   └── config.py      # pilot scope (dates), default cut-off, paths
│   ├── data/              # January 2026 snapshot: fuelhh_wind.csv, windfor.csv
│   ├── tests/             # pytest: analysis logic + API
│   ├── requirements.txt   # runtime deps (pinned)
│   └── requirements-dev.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # shell: tabs, shared cut-off
│   │   ├── DayAheadView.jsx   # tab 1: one delivery day, forecast at cut-off vs actual
│   │   ├── AccuracyView.jsx   # tab 2: metrics, takeaways and breakdown charts
│   │   ├── charts/            # Recharts components (day, series, horizon, histogram, breakdowns)
│   │   ├── components/        # small UI pieces (tiles, tooltip, cut-off picker, status)
│   │   ├── api.js             # fetch helper + useApi hook
│   │   ├── format.js          # MW/GW/date formatting, axis ticks
│   │   └── theme.js / styles.css  # design tokens, light + dark mode
│   └── vite.config.js     # dev proxy /api → :8000
├── docs/VIDEO_OUTLINE.md  # outline for the walkthrough video
├── Dockerfile             # multi-stage: build React, then Python image serving API + static app
├── docker-compose.yml     # local run: `docker compose up`
├── pyproject.toml         # Vercel: Python deps + entrypoint (backend.app.main:app)
├── vercel.json            # Vercel: builds the React app into backend/static, function bundle excludes
├── .python-version        # Python 3.12 (Vercel runtime, Docker, CI)
└── .github/workflows/ci.yml   # tests + frontend build + Docker build
```

### API

| Endpoint | Returns |
|---|---|
| `GET /api/meta` | pilot dates, default cut-off, forecast run times |
| `GET /api/day?day=2026-01-15&cutoff=09:00` | one delivery day: forecast used, error band, all runs, actuals, day metrics |
| `GET /api/series?start&end&mode&cutoff&horizon_h` | half-hourly actuals + selected hourly forecast |
| `GET /api/accuracy?start&end&mode&cutoff&horizon_h` | summary metrics, by hour, by day, by wind level, histogram |
| `GET /api/accuracy/horizon?start&end&bucket_h=3` | MAE/RMSE/bias by forecast horizon (all runs) |

`mode` is `day_ahead` (uses `cutoff`, HH:MM on D-1) or `horizon` (uses `horizon_h`, 0–48).
Interactive docs: `/docs`.

---

## Deployment (Vercel)

Vercel runs the same FastAPI app with its FastAPI preset:

- `pyproject.toml` points Vercel at the app (`[tool.vercel] entrypoint = "backend.app.main:app"`)
  and lists the runtime dependencies (the same pins as `backend/requirements.txt`).
- `vercel.json` sets the build command: build the React app and copy it to `backend/static`, which
  FastAPI serves via `app.frontend("/")`. API routes (`/api/*`) always take priority.
- The whole FastAPI app becomes one Vercel Function (Python 3.12). Its bundle includes the app code
  and the CSV snapshot; `frontend/`, tests and docs are excluded.

To deploy: import the GitHub repo in the Vercel dashboard (no settings to change; `vercel.json`
carries them), or from the CLI:

```bash
npx vercel          # preview deployment
npx vercel --prod   # production
```

Docker is used for local runs (`docker compose up`); Vercel does not run Docker images, so it builds
from the same source instead.

## Design choices

- **Selection rule first, metrics second.** The whole analysis hinges on scoring only what was known
  at decision time; that logic is isolated in `analysis.py` and covered by tests.
- **Snapshot instead of a database.** The pilot data is ~1.3 MB of CSV; loading it into pandas at
  startup is simpler and faster than running a database, and makes the app reproducible offline.
  A live version would add a scheduled fetch into Postgres/Parquet.
- **One app.** FastAPI serves the built React app, so local Docker and Vercel run the same app on
  one origin with no CORS setup.
- **Plain React state.** Two views and a shared cut-off don't need Redux; a small `useApi` hook
  handles fetching, loading, errors and request cancellation.

## Use of AI tools

This project was built with AI assistance, as allowed by the challenge:

- **Claude Code (Anthropic)** was used as a pair programmer: to profile the Elexon data (publish
  cadence, horizons, the re-published past hours), scaffold the FastAPI and React projects, draft the
  analysis functions, tests, charts, Docker setup and this README, and look up the GB day-ahead
  auction gate-closure times used for the default cut-off.
- I reviewed and ran all code, checked the numbers against the raw data, and made the product
  decisions (scope, cut-off rule, which metrics matter to a buyer, how to word the caveats).
