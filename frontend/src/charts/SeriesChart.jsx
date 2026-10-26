import { useMemo } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ChartTooltip from '../components/ChartTooltip.jsx'
import { fmtDateTime, fmtDay, fmtMW, gwTick, gwTicks, toMs } from '../format.js'
import { useChartColors } from '../theme.js'

const DAY_MS = 24 * 3600_000

/** Actual vs selected forecast over a multi-day period. */
export default function SeriesChart({ points, forecastLabel }) {
  const colors = useChartColors()
  const rows = useMemo(
    () => points.map((point) => ({ t: toMs(point.start_time), actual: point.actual, forecast: point.forecast })),
    [points],
  )
  if (!rows.length) return null

  const start = rows[0].t
  const days = Math.ceil((rows.at(-1).t - start) / DAY_MS)
  const step = Math.max(1, Math.ceil(days / 8))
  const ticks = Array.from({ length: Math.floor(days / step) + 1 }, (_, i) => start + i * step * DAY_MS)
  const yTicks = gwTicks(Math.max(...rows.map((row) => Math.max(row.actual ?? 0, row.forecast ?? 0))))

  return (
    <>
      <div className="legend">
        <span>
          <i className="swatch" style={{ background: colors.actual }} /> Actual
        </span>
        <span>
          <i className="swatch" style={{ background: colors.forecast }} /> {forecastLabel}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey="t"
            type="number"
            domain={['dataMin', 'dataMax']}
            ticks={ticks}
            tickFormatter={fmtDay}
            stroke={colors.grid}
          />
          <YAxis tickFormatter={gwTick} width={52} stroke={colors.grid} ticks={yTicks} domain={[0, yTicks.at(-1)]} />
          <Tooltip
            content={
              <ChartTooltip
                title={(t) => fmtDateTime(t)}
                rows={(row) => [
                  ['Actual', fmtMW(row.actual)],
                  ['Forecast', row.forecast === null ? null : fmtMW(row.forecast)],
                ]}
              />
            }
          />
          <Line dataKey="forecast" stroke={colors.forecast} strokeWidth={1.5} dot={false} connectNulls isAnimationActive={false} />
          <Line dataKey="actual" stroke={colors.actual} strokeWidth={1.5} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </>
  )
}
