import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ChartTooltip from '../components/ChartTooltip.jsx'
import { fmtMW } from '../format.js'
import { useChartColors } from '../theme.js'

/** Distribution of signed errors. Right of zero = over-forecast (the buyer ends up short). */
export default function HistogramChart({ data }) {
  const colors = useChartColors()
  const rows = data.map((bin) => ({ ...bin, label: bin.bin_from }))
  return (
    <>
      <div className="legend">
        <span>
          <i className="swatch band" style={{ background: colors.forecast, opacity: 1 }} /> Over-forecast (you
          would be short)
        </span>
        <span>
          <i className="swatch band" style={{ background: colors.actual, opacity: 1 }} /> Under-forecast (you would
          be long)
        </span>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }} barCategoryGap={1}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="label" tickFormatter={(v) => `${v / 1000} GW`} stroke={colors.grid} />
          <YAxis width={40} stroke={colors.grid} allowDecimals={false} />
          <Tooltip
            cursor={{ fill: colors.grid, opacity: 0.5 }}
            content={
              <ChartTooltip
                title={(label, row) => `Error ${fmtMW(row.bin_from, { signed: true })} to ${fmtMW(row.bin_to, { signed: true })}`}
                rows={(row) => [['Hours', row.count]]}
              />
            }
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]} isAnimationActive={false}>
            {rows.map((bin) => (
              <Cell key={bin.bin_from} fill={bin.bin_from >= 0 ? colors.forecast : colors.actual} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </>
  )
}
