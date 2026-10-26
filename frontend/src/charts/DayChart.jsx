import { useMemo } from 'react'
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ChartTooltip from '../components/ChartTooltip.jsx'
import { fmtDateTime, fmtMW, fmtTime, gwTick, gwTicks, toMs } from '../format.js'
import { useChartColors } from '../theme.js'

/** One delivery day: actual vs the forecast known at the cut-off, its error band, and other runs. */
export default function DayChart({ day, showRuns }) {
  const colors = useChartColors()

  const otherRuns = useMemo(
    () => (showRuns ? day.runs.filter((run) => run.publish_time !== day.used_publish_time) : []),
    [day, showRuns],
  )

  const rows = useMemo(() => {
    const byTime = new Map(
      day.points.map((point) => [
        point.start_time,
        {
          t: toMs(point.start_time),
          actual: point.actual,
          forecast: point.forecast,
          band: point.forecast === null ? null : [point.band_low, point.band_high],
        },
      ]),
    )
    otherRuns.forEach((run, index) =>
      run.points.forEach((point) => {
        const row = byTime.get(point.start_time)
        if (row) row[`run${index}`] = point.forecast
      }),
    )
    return [...byTime.values()]
  }, [day, otherRuns])

  const start = rows[0]?.t ?? 0
  const ticks = Array.from({ length: 9 }, (_, i) => start + i * 3 * 3600_000)
  const yTicks = gwTicks(
    Math.max(...rows.flatMap(({ t, band, ...values }) => [band?.[1] ?? 0, ...Object.values(values).map((v) => v ?? 0)])),
  )

  return (
    <>
      <div className="legend">
        <span>
          <i className="swatch" style={{ background: colors.actual }} /> Actual (metered, half-hourly)
        </span>
        <span>
          <i className="swatch" style={{ background: colors.forecast }} /> Forecast known at cut-off
        </span>
        <span>
          <i className="swatch band" style={{ background: colors.band }} /> Typical error range (10th–90th pct)
        </span>
        {showRuns && (
          <>
            <span>
              <i className="swatch" style={{ background: colors.run }} /> Earlier runs
            </span>
            <span>
              <i className="swatch dashed" style={{ color: colors.run }} /> Runs after cut-off
            </span>
          </>
        )}
      </div>
      <ResponsiveContainer width="100%" height={360}>
        <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey="t"
            type="number"
            domain={[start, start + 24 * 3600_000]}
            ticks={ticks}
            tickFormatter={fmtTime}
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
                  ['Typical range', row.band ? `${fmtMW(row.band[0])} – ${fmtMW(row.band[1])}` : null],
                ]}
              />
            }
          />
          <Area
            dataKey="band"
            stroke="none"
            fill={colors.band}
            fillOpacity={0.15}
            connectNulls
            isAnimationActive={false}
            activeDot={false}
          />
          {otherRuns.map((run, index) => (
            <Line
              key={run.publish_time}
              dataKey={`run${index}`}
              stroke={colors.run}
              strokeWidth={1}
              strokeDasharray={run.before_cutoff ? undefined : '4 3'}
              dot={false}
              activeDot={false}
              connectNulls
              isAnimationActive={false}
            />
          ))}
          <Line
            dataKey="forecast"
            name="Forecast"
            stroke={colors.forecast}
            strokeWidth={2}
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
          <Line
            dataKey="actual"
            name="Actual"
            stroke={colors.actual}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </>
  )
}
