import { useEffect, useState } from 'react'

// Same origin in production (FastAPI serves the built app); Vite proxies /api in development.
const API_BASE = import.meta.env.VITE_API_URL ?? ''

export async function getJson(path, params = {}, signal) {
  const query = new URLSearchParams(params).toString()
  const response = await fetch(`${API_BASE}${path}${query ? `?${query}` : ''}`, { signal })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`)
  }
  return response.json()
}

/** Fetch `path` whenever `params` change. Returns { data, error, loading }. */
export function useApi(path, params) {
  const key = JSON.stringify(params)
  const [state, setState] = useState({ data: null, error: null, loading: true })

  useEffect(() => {
    const controller = new AbortController()
    setState((previous) => ({ ...previous, loading: true, error: null }))
    getJson(path, JSON.parse(key), controller.signal)
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((error) => {
        if (error.name !== 'AbortError') setState({ data: null, error: error.message, loading: false })
      })
    return () => controller.abort()
  }, [path, key])

  return state
}
