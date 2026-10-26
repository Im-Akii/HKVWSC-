/** Recharts tooltip body: a title plus one row per series, values formatted by `format`. */
export default function ChartTooltip({ active, payload, label, title, format, rows }) {
  if (!active || !payload?.length) return null
  const datum = payload[0].payload
  const items = rows ? rows(datum) : payload.map((item) => [item.name, format(item.value)])
  return (
    <div className="chart-tooltip">
      <div className="title">{title(label, datum)}</div>
      {items
        .filter(([, value]) => value !== null && value !== undefined)
        .map(([name, value]) => (
          <div className="row" key={name}>
            <span>{name}</span>
            <b>{value}</b>
          </div>
        ))}
    </div>
  )
}
