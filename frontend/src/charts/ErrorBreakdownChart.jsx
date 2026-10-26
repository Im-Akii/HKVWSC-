import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ChartTooltip from '../components/ChartTooltip.jsx'
import { fmtMW, gwTick, gwTicks } from '../format.js'
import { useChartColors } from '../theme.js'

/** MAE and bias (both MW, one axis) for each group: hour of day, forecast level, day... */
export default function ErrorBreakdownChart({ data, xKey, xFormatter, titleFormatter, height = 260 }) {
  const colors = useChartColors()
  const values = data.flatMap((row) => [row.mae, row.bias])
  const yTicks = gwTicks(Math.max(...values), Math.min(...values))
  return (
    <>
      <div className="legend">
        <span>
          <i className="swatch band" style={{ background: colors.actual, opacity: 1 }} /> Mean absolute error
        </span>
        <span>
          <i className="swatch band" style={{ background: colors.bias, opacity: 1 }} /> Bias (forecast − actual)
        </span>
      </div>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }} barGap={2}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey={xKey} tickFormatter={xFormatter} stroke={colors.grid} interval="preserveStartEnd" />
          <YAxis tickFormatter={gwTick} width={52} stroke={colors.grid} ticks={yTicks} domain={[yTicks[0], yTicks.at(-1)]} />
          <ReferenceLine y={0} stroke={colors.muted} />
          <Tooltip
            cursor={{ fill: colors.grid, opacity: 0.5 }}
            content={
              <ChartTooltip
                title={(label, row) => titleFormatter(row)}
                rows={(row) => [
                  ['MAE', fmtMW(row.mae)],
                  ['Bias', fmtMW(row.bias, { signed: true })],
                  ['RMSE', fmtMW(row.rmse)],
                  ['Hours', row.n],
                ]}
              />
            }
          />
          <Bar dataKey="mae" fill={colors.actual} radius={[4, 4, 0, 0]} isAnimationActive={false} />
          <Bar dataKey="bias" fill={colors.bias} radius={[4, 4, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </>
  )
}
