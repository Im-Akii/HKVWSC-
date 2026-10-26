# Video outline (≤ 10 min, unlisted YouTube)

Record at 1280×800 or larger, app running from the deployed URL (fall back to `docker compose up`).
Numbers below are for the default 09:00 cut-off; re-check them in the app before recording.

## Part 1: Pilot results for the client (≤ 5 min)

Audience: the utility's day-ahead buying team. Goal: they leave wanting to use it.

1. **The problem (30 s).** You bid for tomorrow's power by ~09:20. Wind can swing by several GW, so
   the wind forecast you hold at that moment drives how much you buy. Two questions: *what did the
   forecast say when we had to decide*, and *how far can we trust it*.
2. **Day-ahead view (1.5 min).** Open 15 Jan.
   - The callout: "latest forecast at the 09:00 cut-off was the 07:30 run, 16.5–39.5 h ahead".
   - Forecast vs actual line, the shaded "typical error range".
   - Tick "show every forecast run": how the forecast moved as delivery approached; dashed runs came
     after the cut-off (you couldn't have used them).
   - Change the cut-off to 10:00: now the 09:30 run is used. Pick a bad day (11 or 28 Jan) to show
     a large miss.
3. **Accuracy view (2 min).**
   - Headline: off by ~2.0 GW an hour on average (18% of output), and **over-forecast 85% of the
     time by ~1.7 GW**.
   - Planning buffer: in 90% of hours actual wind was within 4.2 GW below forecast. That's a number
     you can put into the buying rule.
   - Error by wind level: the over-forecast is worst in high wind (+4.5 GW above 20 GW forecast).
     Likely curtailment; worth confirming.
   - Horizon chart: error grows from ~1.65 GW (0–6 h) to ~2.35 GW (48 h); the shaded band shows
     the horizons you actually face at your cut-off.
4. **Recommendation & next steps (1 min).** Treat the forecast as an upper estimate, especially in
   high wind; size buffers from the percentiles; next: longer history, live data, a bias-corrected
   forecast, regional split, alerts when the latest run moves a lot.

## Part 2: Tech-lead walkthrough (≤ 5 min)

1. **Architecture (1 min).** Diagram in words: Elexon BMRS → `elexon.py` (stream fetch, weekly
   chunks) → CSV snapshot → `data.py` (load once, cached) → `analysis.py` (pure functions) →
   `service.py` (use cases) → FastAPI `/api/*` → React (Vite + Recharts). One Docker image serves
   both; same image locally (`docker compose up`) and on Heroku (`heroku.yml`).
2. **The core logic (1.5 min).** Open `analysis.py`:
   - `true_forecasts`: drop the ~20% of rows that re-publish past hours (they would flatter accuracy).
   - `select_forecasts`: `merge_asof` by target time, backward on publish time = "latest run known
     at decision time"; two ways to set decision time (cut-off on D-1 or fixed horizon).
   - Error sign convention and why hourly forecasts are scored against the `hh:00` half-hour.
3. **Tests & practices (1 min).** `pytest`: hand-computed metrics, cut-off edge cases (run exactly at
   the cut-off counts, later runs don't), API on synthetic data. CI runs tests, frontend build and
   Docker build. Pinned deps, typed query validation (FastAPI returns 422 for bad input).
4. **Frontend (45 s).** `useApi` hook (loading/error/abort), shared cut-off state, chart components,
   light/dark tokens.
5. **Trade-offs & next steps (45 s).** CSV snapshot vs database (fine for a pilot, swap for scheduled
   ingestion into Postgres); in-sample error band; national only; what I'd build next.
