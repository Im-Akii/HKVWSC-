import { useState } from 'react'
import { useApi } from './api.js'
import ErrorBreakdownChart from './charts/ErrorBreakdownChart.jsx'
import HistogramChart from './charts/HistogramChart.jsx'
import HorizonChart from './charts/HorizonChart.jsx'
import SeriesChart from './charts/SeriesChart.jsx'
import CutoffSelect from './components/CutoffSelect.jsx'
import Status from './components/Status.jsx'
import Tile from './components/Tile.jsx'
import { fmtDateTime, fmtDay, fmtGW, fmtMW, fmtPct } from './format.js'

/** "How wrong is the forecast, and in which direction?" over a chosen period. */
export default function AccuracyView({ meta, cutoff, onCutoffChange }) {
  const [start, setStart] = useState(meta.first_day)
  const [end, setEnd] = useState(meta.last_day)
  const [mode, setMode] = useState('day_ahead')
  const [horizon, setHorizon] = useState(24)

  const params = { start, end, mode, cutoff, horizon_h: horizon }
  const accuracy = useApi('/api/accuracy', params)
  const series = useApi('/api/series', params)
  const byHorizon = useApi('/api/accuracy/horizon', { start, end })

  const summary = accuracy.data?.summary
  const selectionLabel =
    mode === 'day_ahead' ? `Day-ahead forecast (latest before ${cutoff} on D-1)` : `Forecast ${horizon} h ahead`

  return (
    <>
      <div className="controls">
        <label className="field">
          From
          <input type="date" value={start} min={meta.first_day} max={end} onChange={(e) => e.target.value && setStart(e.target.value)} />
        </label>
        <label className="field">
          To
          <input type="date" value={end} min={start} max={meta.last_day} onChange={(e) => e.target.value && setEnd(e.target.value)} />
        </label>
        <label className="field">
          Which forecast to score
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="day_ahead">Known at day-ahead cut-off</option>
            <option value="horizon">Fixed hours ahead</option>
          </select>
        </label>
        {mode === 'day_ahead' ? (
          <CutoffSelect value={cutoff} onChange={onCutoffChange} />
        ) : (
          <label className="field">
            Horizon: {horizon} h ahead
            <input type="range" min={0} max={48} step={1} value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} />
          </label>
        )}
      </div>

      <Status loading={accuracy.loading && !accuracy.data} error={accuracy.error} />
      {summary && summary.n === 0 && <div className="status">No forecast/actual pairs for this selection.</div>}
      {summary && summary.n > 0 && (
        <>
          <Takeaways summary={summary} selectionLabel={selectionLabel} />

          <div className="tiles">
            <Tile label="Mean absolute error" value={fmtMW(summary.mae)} note={`${fmtPct(summary.nmae_pct)} of mean actual (${fmtGW(summary.mean_actual)})`} />
            <Tile label="RMSE" value={fmtMW(summary.rmse)} note="Penalises large misses" />
            <Tile label="Bias (forecast − actual)" value={fmtMW(summary.bias, { signed: true })} note={`Over-forecast in ${fmtPct(summary.pct_over_forecast)} of hours`} />
            <Tile label="90% shortfall buffer" value={fmtMW(summary.error_quantiles.p90)} note="Actual fell further below forecast in only 10% of hours" />
            <Tile label="95% shortfall buffer" value={fmtMW(summary.error_quantiles.p95)} note={`${summary.n} hourly pairs scored`} />
          </div>

          <div className="grid">
            <div className="card">
              <h2>Actual vs forecast</h2>
              <p className="subtitle">{selectionLabel}. Hover for values.</p>
              {series.data && <SeriesChart points={series.data.points} forecastLabel={selectionLabel} />}
            </div>

            <div className="grid grid-2">
              <div className="card">
                <h2>Error vs forecast horizon</h2>
                <p className="subtitle">Every forecast run scored against actuals: accuracy decays the further ahead it looks.</p>
                {byHorizon.data && (
                  <HorizonChart
                    data={byHorizon.data}
                    dayAheadRange={mode === 'day_ahead' ? [summary.horizon_h_min, summary.horizon_h_max] : [horizon, horizon + 1]}
                  />
                )}
              </div>
              <div className="card">
                <h2>Error distribution</h2>
                <p className="subtitle">Hours by forecast − actual, 500 MW bins.</p>
                <HistogramChart data={accuracy.data.histogram} />
              </div>
              <div className="card">
                <h2>Error by time of day</h2>
                <p className="subtitle">UK time (GMT) of the target hour.</p>
                <ErrorBreakdownChart
                  data={accuracy.data.by_hour}
                  xKey="hour"
                  xFormatter={(h) => `${String(h).padStart(2, '0')}:00`}
                  titleFormatter={(row) => `${String(row.hour).padStart(2, '0')}:00`}
                />
              </div>
              <div className="card">
                <h2>Error by forecast wind level</h2>
                <p className="subtitle">The higher the forecast, the more it overshoots.</p>
                <ErrorBreakdownChart
                  data={accuracy.data.by_level}
                  xKey="level_from"
                  xFormatter={(v) => `${v / 1000}–${v / 1000 + 4} GW`}
                  titleFormatter={(row) => `Forecast ${row.level_from / 1000}–${row.level_to / 1000} GW`}
                />
              </div>
            </div>

            <div className="card">
              <h2>Error by delivery day</h2>
              <p className="subtitle">Spot the days that hurt: hover a bar for the numbers.</p>
              <ErrorBreakdownChart
                data={accuracy.data.by_day}
                xKey="day"
                xFormatter={(d) => fmtDay(d).replace(/^\w+ /, '')}
                titleFormatter={(row) => fmtDay(row.day)}
                height={240}
              />
            </div>
          </div>

          <DataNotes />
        </>
      )}
    </>
  )
}

function Takeaways({ summary, selectionLabel }) {
  const overForecast = summary.bias > 0
  return (
    <div className="callout">
      <p>
        <b>{selectionLabel}:</b> off by <b>{fmtMW(summary.mae)}</b> per hour on average ({fmtPct(summary.nmae_pct)} of
        mean wind output). It {overForecast ? 'over' : 'under'}-forecast in{' '}
        {fmtPct(overForecast ? summary.pct_over_forecast : 100 - summary.pct_over_forecast)} of hours, by{' '}
        {fmtMW(Math.abs(summary.bias))} on average, so plan for {overForecast ? 'less' : 'more'} wind than forecast.
      </p>
      <p>
        Planning buffer: in 90% of hours actual wind was no more than <b>{fmtMW(summary.error_quantiles.p90)}</b> below
        the forecast (95%: {fmtMW(summary.error_quantiles.p95)}). Worst miss: {fmtMW(summary.worst_over.error, { signed: true })} at{' '}
        {fmtDateTime(summary.worst_over.time)}.
      </p>
    </div>
  )
}

function DataNotes() {
  return (
    <div className="notes card">
      <b>How to read this (and what it can't tell you)</b>
      <ul>
        <li>
          Source: Elexon BMRS. Actuals are FUELHH wind generation (half-hourly, metered transmission-connected wind);
          forecasts are WINDFOR (hourly). Each hourly forecast is scored against the half-hour that starts at the same
          time.
        </li>
        <li>
          Rows a forecast run publishes for hours already in the past are ignored: they are not forecasts.
        </li>
        <li>
          The over-forecast grows with the wind level. A likely cause is curtailment: in high wind, transmission
          constraints turn wind farms down, so metered output is below what the weather supported. This pilot does not
          verify that; it would need balancing-action data.
        </li>
        <li>
          One month (January 2026) is a small sample of winter weather; buffers should be re-estimated on a longer
          history before being relied on, and the error band is in-sample.
        </li>
      </ul>
    </div>
  )
}
