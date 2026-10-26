import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import ChartTooltip from '../components/ChartTooltip.jsx'
import { fmtMW, gwTick, gwTicks } from '../format.js'
import { useChartColors } from '../theme.js'

/** How error grows with forecast horizon (all forecast runs), with the day-ahead horizons shaded. */
export default function HorizonChart({ data, dayAheadRange }) {
  const colors = useChartColors()
  const rows = data.map((row) => ({ ...row, mid: (row.horizon_from_h + row.horizon_to_h) / 2 }))
  const values = rows.flatMap((row) => [row.rmse, row.bias])
  const yTicks = gwTicks(Math.max(...values), Math.min(...values))
  return (
    <>
      <div className="legend">
        <span>
          <i className="swatch" style={{ background: colors.actual }} /> MAE
        </span>
        <span>
          <i className="swatch dashed" style={{ color: colors.actual }} /> RMSE
        </span>
        <span>
          <i className="swatch" style={{ background: colors.bias }} /> Bias
        </span>
        {dayAheadRange && (
          <span>
            <i className="swatch band" style={{ background: colors.band }} /> Horizons used at your cut-off
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} />
          {dayAheadRange && (
            <ReferenceArea x1={dayAheadRange[0]} x2={dayAheadRange[1]} fill={colors.band} fillOpacity={0.1} />
          )}
          <XAxis
            dataKey="mid"
            type="number"
            domain={[0, 48]}
            ticks={[0, 6, 12, 18, 24, 30, 36, 42, 48]}
            tickFormatter={(h) => `${h}h`}
            stroke={colors.grid}
          />
          <YAxis tickFormatter={gwTick} width={52} stroke={colors.grid} ticks={yTicks} domain={[yTicks[0], yTicks.at(-1)]} />
          <ReferenceLine y={0} stroke={colors.muted} />
          <Tooltip
            content={
              <ChartTooltip
                title={(label, row) => `${row.horizon_from_h}–${row.horizon_to_h} h ahead`}
                rows={(row) => [
                  ['MAE', fmtMW(row.mae)],
                  ['RMSE', fmtMW(row.rmse)],
                  ['Bias', fmtMW(row.bias, { signed: true })],
                  ['Pairs', row.n],
                ]}
              />
            }
          />
          <Line dataKey="mae" stroke={colors.actual} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
          <Line
            dataKey="rmse"
            stroke={colors.actual}
            strokeWidth={2}
            strokeDasharray="5 4"
            dot={false}
            isAnimationActive={false}
          />
          <Line dataKey="bias" stroke={colors.bias} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </>
  )
}
