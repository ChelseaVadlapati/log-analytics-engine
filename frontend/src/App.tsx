import { ServiceGrid } from './components/ServiceGrid'
import { LogTable }    from './components/LogTable'
import { LiveTail }    from './components/LiveTail'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-white">
            Log Analytics Engine
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Distributed log ingestion, search, and anomaly detection
          </p>
        </div>
        <div className="text-xs text-gray-500 font-mono">
          ES: localhost:9200 · API: localhost:8000
        </div>
      </div>

      <ServiceGrid />

      <div className="mb-6">
        <LiveTail />
      </div>

      <LogTable />
    </div>
  )
}