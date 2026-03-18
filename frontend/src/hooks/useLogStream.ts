import { useEffect, useRef, useState } from 'react'
import type { LogEvent } from '../api/logs'

const MAX_LOGS = 200

export function useLogStream(active: boolean) {
  const [logs, setLogs]           = useState<LogEvent[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!active) {
      wsRef.current?.close()
      setConnected(false)
      return
    }

    const ws = new WebSocket('ws://localhost:8000/api/logs/tail')
    wsRef.current = ws

    ws.onopen    = () => setConnected(true)
    ws.onclose   = () => setConnected(false)
    ws.onmessage = (e) => {
      const log: LogEvent = JSON.parse(e.data)
      setLogs(prev => [log, ...prev].slice(0, MAX_LOGS))
    }

    return () => ws.close()
  }, [active])

  return { logs, connected }
}