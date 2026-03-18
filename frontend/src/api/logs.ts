import axios from 'axios'

const BASE = 'http://localhost:8000'

export interface LogEvent {
  event_id:    string
  timestamp:   number
  service:     string
  level:       string
  message:     string
  trace_id:    string | null
  duration_ms: number | null
  host:        string
  is_error:    boolean
  ingested_at: number
}

export interface SearchResponse {
  total:   number
  page:    number
  pages:   number
  results: LogEvent[]
}

export interface SearchParams {
  query?:     string
  service?:   string
  level?:     string
  page?:      number
  page_size?: number
}

export const searchLogs = async (params: SearchParams): Promise<SearchResponse> => {
  const { data } = await axios.get(`${BASE}/api/logs/search`, { params })
  return data
}

export const countLogs = async (service?: string, level?: string) => {
  const { data } = await axios.get(`${BASE}/api/logs/count`, {
    params: { service, level }
  })
  return data as { count: number }
}

export const getServices = async (): Promise<string[]> => {
  const { data } = await axios.get(`${BASE}/api/logs/services`)
  return data.services
}