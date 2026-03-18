import { useEffect, useState } from 'react'
import { countLogs } from '../api/logs'

const SERVICES = ['web-api', 'auth-service', 'payment-service']

interface ServiceStats {
  name:   string
  total:  number
  errors: number
  rate:   string
}

export function ServiceGrid() {
  const [stats, setStats] = useState<ServiceStats[]>([])

  const fetchStats = async () => {
    const results = await Promise.all(
      SERVICES.map(async (s) => {
        const [total, errors] = await Promise.all([
          countLogs(s),
          countLogs(s, 'ERROR'),
        ])
        const errorRate = total.count > 0
          ? ((errors.count / total.count) * 100).toFixed(1)
          : '0.0'
        return { name: s, total: total.count, errors: errors.count, rate: errorRate }
      })
    )
    setStats(results)
  }

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 10000)
    return () => clearInterval(interval)
  }, [])

  const getColor = (rate: string) => {
    const r = parseFloat(rate)
    if (r > 20) return 'border-red-500 bg-red-950'
    if (r > 10) return 'border-yellow-500 bg-yellow-950'
    return 'border-green-500 bg-green-950'
  }

  const getDot = (rate: string) => {
    const r = parseFloat(rate)
    if (r > 20) return 'bg-red-400'
    if (r > 10) return 'bg-yellow-400'
    return 'bg-green-400'
  }

  return (
    <div className="grid grid-cols-3 gap-4 mb-6">
      {stats.map(s => (
        <div key={s.name} className={`border rounded-lg p-4 ${getColor(s.rate)}`}>
          <div className="flex items-center gap-2 mb-3">
            <div className={`w-2 h-2 rounded-full ${getDot(s.rate)}`} />
            <span className="text-sm font-medium text-gray-200">{s.name}</span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <div className="text-xl font-bold text-white">
                {s.total.toLocaleString()}
              </div>
              <div className="text-xs text-gray-400">total</div>
            </div>
            <div>
              <div className="text-xl font-bold text-red-400">
                {s.errors.toLocaleString()}
              </div>
              <div className="text-xs text-gray-400">errors</div>
            </div>
            <div>
              <div className="text-xl font-bold text-yellow-400">
                {s.rate}%
              </div>
              <div className="text-xs text-gray-400">error rate</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}