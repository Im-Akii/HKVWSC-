const OPTIONS = Array.from({ length: 48 }, (_, i) => `${String(Math.floor(i / 2)).padStart(2, '0')}:${i % 2 ? '30' : '00'}`)

export default function CutoffSelect({ value, onChange }) {
  return (
    <label className="field">
      Decision cut-off (D-1, UK time)
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {OPTIONS.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  )
}
