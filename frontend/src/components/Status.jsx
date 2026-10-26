export default function Status({ loading, error }) {
  if (error) return <div className="status error">Could not load data: {error}</div>
  if (loading) return <div className="status">Loading…</div>
  return null
}
