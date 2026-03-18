import { useState } from 'react'
import { useLogStream } from '../hooks/useLogStream'

const LEVEL_COLORS: Record<string, string> = {
  DEBUG: 'text-gray-400',
  INFO:  'text-blue-400',
  WARN:  'text-yellow-400',
  ERROR: 'text-red-400',
  FATAL: 'text-red-300',
}

export function LiveTail() {
  const [active, setActive]   = useState(false)
  const { logs, connected }   = useLogStream(active)

  const formatTs = (ms: number) =>
    new Date(ms).toISOString().replace('T', ' ').slice(0, 19)

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-700">
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-medium text-gray-200">Live tail</h2>
          <div className={`flex items-center gap-1.5 text-xs
            ${connected ? 'text-green-400' : 'text-gray-500'}`}>
            <div className={`w-1.5 h-1.5 rounded-full
              ${connected ? 'bg-green-400 animate-pulse' : 'bg-gray-500'}`} />
            {connected ? 'connected' : 'disconnected'}
          </div>
        </div>
        <button
          onClick={() => setActive(a => !a)}
          className={`px-4 py-1.5 rounded text-sm font-medium transition-colors
            ${active
              ? 'bg-red-700 hover:bg-red-800 text-white'
              : 'bg-green-700 hover:bg-green-800 text-white'}`}
        >
          {active ? 'Stop' : 'Start'}
        </button>
      </div>

      <div className="font-mono text-xs p-4 h-72 overflow-y-auto bg-black
                      rounded-b-lg space-y-0.5">
        {logs.length === 0 && (
          <div className="text-gray-600 text-center mt-24">
            {active ? 'Waiting for logs...' : 'Press Start to begin streaming'}
          </div>
        )}
        {logs.map(log => (
          <div key={log.event_id} className="flex gap-3 hover:bg-gray-900 px-1 rounded">
            <span className="text-gray-600 whitespace-nowrap">
              {formatTs(log.timestamp)}
            </span>
            <span className="text-gray-500 whitespace-nowrap">{log.service}</span>
            <span className={`whitespace-nowrap font-bold ${LEVEL_COLORS[log.level]}`}>
              {log.level}
            </span>
            <span className="text-gray-300 truncate">{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  )
}