import { useEffect, useState } from 'react'
import { searchLogs } from '../api/logs'
import type { LogEvent } from '../api/logs'

const LEVEL_COLORS: Record<string, string> = {
  DEBUG: 'bg-gray-700 text-gray-300',
  INFO:  'bg-blue-900 text-blue-300',
  WARN:  'bg-yellow-900 text-yellow-300',
  ERROR: 'bg-red-900 text-red-300',
  FATAL: 'bg-red-700 text-red-100',
}

export function LogTable() {
  const [logs, setLogs]       = useState<LogEvent[]>([])
  const [total, setTotal]     = useState(0)
  const [page, setPage]       = useState(1)
  const [query, setQuery]     = useState('')
  const [service, setService] = useState('')
  const [level, setLevel]     = useState('')
  const [loading, setLoading] = useState(false)

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const res = await searchLogs({
        query:     query   || undefined,
        service:   service || undefined,
        level:     level   || undefined,
        page,
        page_size: 20,
      })
      setLogs(res.results)
      setTotal(res.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { setPage(1) }, [query, service, level])
  useEffect(() => { fetchLogs() }, [query, service, level, page])

  const formatTs = (ms: number) =>
    new Date(ms).toISOString().replace('T', ' ').slice(0, 19)

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-700">
      <div className="flex gap-3 p-4 border-b border-gray-700">
        <input
          type="text"
          placeholder="Search messages..."
          value={query}
          onChange={e => setQuery(e.target.value)}
          className="flex-1 bg-gray-800 text-gray-200 rounded px-3 py-2 text-sm
                     border border-gray-600 focus:outline-none focus:border-blue-500"
        />
        <select
          value={service}
          onChange={e => setService(e.target.value)}
          className="bg-gray-800 text-gray-200 rounded px-3 py-2 text-sm
                     border border-gray-600 focus:outline-none"
        >
          <option value="">All services</option>
          <option value="web-api">web-api</option>
          <option value="auth-service">auth-service</option>
          <option value="payment-service">payment-service</option>
        </select>
        <select
          value={level}
          onChange={e => setLevel(e.target.value)}
          className="bg-gray-800 text-gray-200 rounded px-3 py-2 text-sm
                     border border-gray-600 focus:outline-none"
        >
          <option value="">All levels</option>
          {['DEBUG','INFO','WARN','ERROR','FATAL'].map(l => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
        <button
          onClick={fetchLogs}
          className="bg-blue-600 hover:bg-blue-700 text-white rounded px-4 py-2 text-sm"
        >
          Refresh
        </button>
      </div>

      <div className="px-4 py-2 text-xs text-gray-400 border-b border-gray-700">
        {total.toLocaleString()} logs found
        {loading && <span className="ml-2 text-blue-400">Loading...</span>}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-400 text-xs border-b border-gray-700">
              <th className="text-left px-4 py-2">Timestamp</th>
              <th className="text-left px-4 py-2">Service</th>
              <th className="text-left px-4 py-2">Level</th>
              <th className="text-left px-4 py-2">Message</th>
              <th className="text-left px-4 py-2">Duration</th>
            </tr>
          </thead>
          <tbody>
            {logs.map(log => (
              <tr key={log.event_id}
                  className="border-b border-gray-800 hover:bg-gray-800 transition-colors">
                <td className="px-4 py-2 text-gray-400 font-mono text-xs whitespace-nowrap">
                  {formatTs(log.timestamp)}
                </td>
                <td className="px-4 py-2 text-gray-300 text-xs whitespace-nowrap">
                  {log.service}
                </td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium
                                   ${LEVEL_COLORS[log.level] ?? LEVEL_COLORS.INFO}`}>
                    {log.level}
                  </span>
                </td>
                <td className="px-4 py-2 text-gray-200 max-w-md truncate">
                  {log.message}
                </td>
                <td className="px-4 py-2 text-gray-400 text-xs">
                  {log.duration_ms != null ? `${log.duration_ms}ms` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between px-4 py-3 border-t border-gray-700">
        <button
          onClick={() => setPage(p => Math.max(1, p - 1))}
          disabled={page === 1}
          className="text-sm text-gray-400 hover:text-white disabled:opacity-30"
        >
          ← Previous
        </button>
        <span className="text-xs text-gray-400">Page {page}</span>
        <button
          onClick={() => setPage(p => p + 1)}
          disabled={logs.length < 20}
          className="text-sm text-gray-400 hover:text-white disabled:opacity-30"
        >
          Next →
        </button>
      </div>
    </div>
  )
}