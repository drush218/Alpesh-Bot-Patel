// Mirrors backend/app/services/workspace.py and scorecard.py responses.

export interface SourcedPct {
  pct: number
  source?: string
  ref?: string
}

export interface SourcedValue {
  value: number
  source?: string
  ref?: string
}

/** The v2 model inputs the workspace edits (subset the UI uses). */
export interface ModelInputs {
  meta: {
    ticker: string
    company: string
    exchange?: string
    reporting_currency?: string
    units?: string
    base_year: string
    forecast_years: string[]
    data_as_of?: string
    reference_price?: { value: number; date: string }
  }
  revenue: { segments: { name: string; base: number; growth: SourcedPct[] }[] }
  operating_margin: SourcedPct[]
  net_interest: SourcedValue[]
  tax_rate: SourcedPct[]
  nci_pct?: SourcedPct[]
  shares: { base_diluted: number; annual_change: SourcedPct[] }
  scenarios: Record<'low' | 'high', { growth_pp: number; margin_pp: number; ref?: string }>
}

export interface YearOutput {
  year: string
  revenue: number
  revenue_growth_pct: number
  operating_margin_pct: number
  operating_income: number
  pretax: number
  tax: number
  net_income: number
  shares_diluted: number
  eps: number
}

export interface ModelOutputs {
  base_revenue: number
  scenarios: Record<'bau' | 'low' | 'high', YearOutput[]>
}

export interface Price {
  close: number
  currency: string
  price_date: string
  fetched_at: string
  source: string | null
  fx: number | null
}

export interface BaseMoved {
  path: string
  saved_base: number
  current_base: number
  note: string
}

export interface Override {
  path: string
  value: number
}

export interface WorkspaceResult {
  analysis_id: number
  data_as_of: string | null
  price: Price | null
  actual: { year: string; revenue: number; shares: number }
  base_inputs: ModelInputs
  base_outputs: ModelOutputs
  outputs: ModelOutputs | null
  errors: string[]
  warnings: string[]
  could_not_apply: string[]
  base_moved: BaseMoved[]
  scenario?: {
    id: number
    name: string
    note: string | null
    base_analysis_id: number | null
    rebased: boolean
    overrides: Override[]
  }
}

export interface ScenarioSummary {
  id: number
  name: string
  note: string | null
  override_count: number
  on_current_base: boolean
  updated_at: string | null
}

export type CatalystStatus = 'open' | 'hit' | 'missed'

export interface Catalyst {
  text: string
  date: string | null
  status: CatalystStatus
}

export type Dimension = 'growth' | 'value' | 'income'

export interface ScorecardIn {
  growth: number
  value: number
  income: number
  bull_catalysts: Catalyst[]
  bear_catalysts: Catalyst[]
  note: string | null
}

export interface ScorecardResponse {
  current: (ScorecardIn & { id: number; created_at: string | null }) | null
  versions: number
  suggested: {
    as_of: string | null
    growth: { score: number; ref: string } | null
    value: { score: number; ref: string } | null
    income: { score: number; ref: string } | null
    bull_catalysts: { text: string; date?: string }[]
    bear_catalysts: { text: string; date?: string }[]
  } | null
}
