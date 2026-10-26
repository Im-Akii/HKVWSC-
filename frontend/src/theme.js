import { useEffect, useState } from 'react'

const TOKENS = {
  actual: '--series-actual',
  forecast: '--series-forecast',
  run: '--series-run',
  bias: '--series-bias',
  band: '--band',
  grid: '--grid',
  muted: '--text-muted',
}

function readColors() {
  const style = getComputedStyle(document.documentElement)
  return Object.fromEntries(Object.entries(TOKENS).map(([name, token]) => [name, style.getPropertyValue(token).trim()]))
}

/** Chart colours from the CSS tokens (SVG attributes can't use var()), updated on light/dark switch. */
export function useChartColors() {
  const [colors, setColors] = useState(readColors)
  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const update = () => setColors(readColors())
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])
  return colors
}
