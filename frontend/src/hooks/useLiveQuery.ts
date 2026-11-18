import { useEffect, useState } from 'react'
import { api } from '../api'

const REFRESH_INTERVAL_MS = 5_000

type QueryResult<T> = { path: string; data: T | null; error: boolean }

export function useLiveQuery<T>(path: string) {
  const [result, setResult] = useState<QueryResult<T>>({ path, data: null, error: false })

  useEffect(() => {
    let disposed = false
    let timer: ReturnType<typeof setTimeout> | undefined
    let pending: AbortController | undefined
    setResult({ path, data: null, error: false })

    function schedule() {
      if (!disposed) timer = setTimeout(tick, REFRESH_INTERVAL_MS)
    }

    function tick() {
      if (document.visibilityState === 'hidden' || !navigator.onLine) {
        schedule()
      } else {
        void refresh()
      }
    }

    async function refresh() {
      if (disposed || pending) return
      clearTimeout(timer)
      pending = new AbortController()
      try {
        const response = await api.get<T>(path, { signal: pending.signal, timeout: 15_000 })
        if (!disposed) {
          // Keep chart references stable when a poll returns unchanged data.
          setResult(previous => previous.path === path && !previous.error &&
            JSON.stringify(previous.data) === JSON.stringify(response.data)
            ? previous : { path, data: response.data, error: false })
        }
      } catch {
        if (!disposed) setResult(previous => ({ ...previous, error: true }))
      } finally {
        pending = undefined
        schedule()
      }
    }

    function resume() {
      if (document.visibilityState !== 'hidden' && navigator.onLine) void refresh()
    }

    void refresh()
    window.addEventListener('focus', resume)
    window.addEventListener('online', resume)
    document.addEventListener('visibilitychange', resume)
    return () => {
      disposed = true
      clearTimeout(timer)
      pending?.abort()
      window.removeEventListener('focus', resume)
      window.removeEventListener('online', resume)
      document.removeEventListener('visibilitychange', resume)
    }
  }, [path])

  // A superseded filter must never display results from the previous request.
  return result.path === path ? result : { path, data: null, error: false }
}
