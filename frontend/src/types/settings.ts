// Mirrors backend/app/services/settings_status.py and ingest.py

export interface AnalysisOnFile {
  ticker: string
  company: string | null
  data_as_of: string | null
  ingested_at: string | null
  warning_count: number
  is_stale: boolean
  last_earnings: string | null
}

export interface FactorProposal {
  code: string
  name: string | null
  series: string | null
  provider: string | null
  scope: string | null
  rationale: string | null
  proposed_by_tickers: string[]
}

export interface SettingsStatus {
  credentials: { saved: boolean; key_hint: string | null }
  analyses: AnalysisOnFile[]
  holdings: { count: number; modelled: number; without_analysis: string[] }
  oldest_strike: string | null
  prices: { last_fetched: string | null; unmapped: string[] }
  deposits_cached_at: string | null
  proposals: FactorProposal[]
  warnings: string[]
}

export interface IngestPreview {
  ok: boolean
  filename: string | null
  errors: string[]
  ticker?: string
  company?: string | null
  exchange?: string | null
  data_as_of?: string | null
  status?: 'new' | 'replaces' | 'duplicate'
  replaces_as_of?: string | null
  bau_eps?: { year: string; eps: number }[]
  currency?: string | null
  macro_count?: number
  lever_count?: number
  event_count?: number
  proposed_factors?: string[]
  warnings?: string[]
  bottom_line?: string | null
}
