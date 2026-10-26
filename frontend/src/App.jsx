import { useState } from 'react'
import AccuracyView from './AccuracyView.jsx'
import { useApi } from './api.js'
import Status from './components/Status.jsx'
import DayAheadView from './DayAheadView.jsx'

const TABS = [
  { id: 'day', label: 'Day-ahead forecast' },
  { id: 'accuracy', label: 'Forecast accuracy' },
]

export default function App() {
  const [tab, setTab] = useState('day')
  const meta = useApi('/api/meta', {})
  // The cut-off is shared: changing it on one tab applies to the other.
  const [cutoff, setCutoff] = useState(null)

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Wind Forecast Monitor</h1>
          <p>GB national wind generation for day-ahead buying · January 2026 pilot</p>
        </div>
        <nav className="tabs" role="tablist">
          {TABS.map(({ id, label }) => (
            <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id)}>
              {label}
            </button>
          ))}
        </nav>
      </header>

      <Status loading={meta.loading} error={meta.error} />
      {meta.data &&
        (() => {
          const props = { meta: meta.data, cutoff: cutoff ?? meta.data.default_cutoff, onCutoffChange: setCutoff }
          return tab === 'day' ? <DayAheadView {...props} /> : <AccuracyView {...props} />
        })()}

      <footer className="footer">
        Data: Elexon BMRS (FUELHH, WINDFOR) · Times are UK time (GMT = UTC in January) · Delivery days{' '}
        {meta.data ? `${meta.data.first_day} to ${meta.data.last_day}` : ''}
      </footer>
    </div>
  )
}
