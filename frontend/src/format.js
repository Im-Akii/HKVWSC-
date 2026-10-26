// All times from the API are UTC; in January UK time is GMT, so UTC is what the client's desk sees.
const dateTime = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'UTC',
})
const dayFormat = new Intl.DateTimeFormat('en-GB', {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
  timeZone: 'UTC',
})
const timeFormat = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' })

export const toMs = (iso) => new Date(iso).getTime()
export const fmtDateTime = (value) => dateTime.format(new Date(value))
export const fmtDay = (value) => dayFormat.format(new Date(value))
export const fmtTime = (value) => timeFormat.format(new Date(value))

export function fmtMW(value, { signed = false } = {}) {
  if (value === null || value === undefined) return '–'
  const sign = signed && value > 0 ? '+' : ''
  return `${sign}${Math.round(value).toLocaleString('en-GB')} MW`
}

export function fmtGW(value, { signed = false } = {}) {
  if (value === null || value === undefined) return '–'
  const sign = signed && value > 0 ? '+' : ''
  return `${sign}${(value / 1000).toFixed(1)} GW`
}
export const gwTick = (value) => `${Number((value / 1000).toFixed(1))} GW`
export const fmtPct = (value) => (value === null || value === undefined ? '–' : `${value.toFixed(1)}%`)

/** Add `days` to an ISO date string (YYYY-MM-DD). */
export function shiftDay(isoDate, days) {
  const date = new Date(`${isoDate}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

/** Axis ticks (MW values) in whole-GW steps covering [minMW, maxMW], always including 0. */
export function gwTicks(maxMW, minMW = 0) {
  const span = Math.max(1, (maxMW - Math.min(0, minMW)) / 1000)
  const step = span <= 6 ? 1 : span <= 12 ? 2 : span <= 24 ? 4 : 5
  const bottom = Math.floor(Math.min(0, minMW) / 1000 / step) * step
  const top = Math.max(step, Math.ceil(maxMW / 1000 / step) * step)
  return Array.from({ length: (top - bottom) / step + 1 }, (_, i) => (bottom + i * step) * 1000)
}
