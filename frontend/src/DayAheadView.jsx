import { useState } from 'react'
import { useApi } from './api.js'
import DayChart from './charts/DayChart.jsx'
import CutoffSelect from './components/CutoffSelect.jsx'
import Status from './components/Status.jsx'
import Tile from './components/Tile.jsx'
import { fmtDateTime, fmtDay, fmtGW, fmtMW, fmtTime, shiftDay } from './format.js'

/** "What did we know when we had to bid?" — one delivery day at a time. */
export default function DayAheadView({ meta, cutoff, onCutoffChange }) {
  const [day, setDay] = useState('2026-01-15')
  const [showRuns, setShowRuns] = useState(false)
  const { data, error, loading } = useApi('/api/day', { day, cutoff })

  return (
    <>
      <div className="controls">
        <label className="field">
          Delivery day
          <span className="inline">
            <button
              className="icon-button"
              aria-label="Previous day"
              disabled={day <= meta.first_day}
              onClick={() => setDay(shiftDay(day, -1))}
            >
              ‹
            </button>
            <input
              type="date"
              value={day}
              min={meta.first_day}
              max={meta.last_day}
              onChange={(event) => event.target.value && setDay(event.target.value)}
            />
            <button
              className="icon-button"
              aria-label="Next day"
              disabled={day >= meta.last_day}
              onClick={() => setDay(shiftDay(day, 1))}
            >
              ›
            </button>
          </span>
        </label>
        <CutoffSelect value={cutoff} onChange={onCutoffChange} />
        <label className="checkbox">
          <input type="checkbox" checked={showRuns} onChange={(event) => setShowRuns(event.target.checked)} />
          Show every forecast run for this day
        </label>
        <p className="hint">Forecast runs are published at about {meta.forecast_run_times_utc.filter((t) => t.endsWith(':30')).join(', ')}.</p>
      </div>

      <Status loading={loading && !data} error={error} />
      {data && <DayDetails data={data} cutoff={cutoff} showRuns={showRuns} />}
    </>
  )
}

function DayDetails({ data, cutoff, showRuns }) {
  const forecasts = data.points.filter((point) => point.forecast !== null)
  if (!data.used_publish_time || !forecasts.length) {
    return <div className="status">No forecast had been published by the cut-off for this day.</div>
  }
  const peak = forecasts.reduce((a, b) => (b.forecast > a.forecast ? b : a))
  const trough = forecasts.reduce((a, b) => (b.forecast < a.forecast ? b : a))
  const mean = forecasts.reduce((sum, point) => sum + point.forecast, 0) / forecasts.length
  const nextRun = data.runs.find((run) => !run.before_cutoff)
  const { summary, band } = data

  return (
    <>
      <div className="callout">
        <p>
          For delivery on <b>{fmtDay(data.day)}</b>, the latest wind forecast available at the {cutoff} cut-off was
          the run published <b>{fmtDateTime(data.used_publish_time)}</b>, looking {data.horizon_range_h[0]}–
          {data.horizon_range_h[1]} hours ahead.
          {nextRun && <> The next run ({fmtDateTime(nextRun.publish_time)}) arrived after the cut-off.</>}
        </p>
      </div>

      <div className="tiles">
        <Tile label="Forecast average" value={fmtGW(mean)} note="National wind, hourly forecast" />
        <Tile label="Forecast peak" value={fmtGW(peak.forecast)} note={`at ${fmtTime(peak.start_time)}`} />
        <Tile label="Forecast low" value={fmtGW(trough.forecast)} note={`at ${fmtTime(trough.start_time)}`} />
        <Tile
          label="Typical error range"
          value={`${fmtGW(-band.p90, { signed: true })} to ${fmtGW(-band.p10, { signed: true })}`}
          note="Actual minus forecast in 80% of pilot hours"
        />
        <Tile
          label="Outcome: MAE this day"
          value={fmtMW(summary.mae)}
          note={`Bias ${fmtMW(summary.bias, { signed: true })} · actual avg ${fmtGW(summary.mean_actual)}`}
        />
      </div>

      <div className="card">
        <h2>Wind generation: forecast at cut-off vs what happened</h2>
        <p className="subtitle">UK time (GMT). The shaded band is where actual wind typically landed relative to this kind of forecast.</p>
        <DayChart day={data} showRuns={showRuns} />
      </div>
    </>
  )
}
