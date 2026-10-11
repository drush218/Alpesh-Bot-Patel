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

export type Dimension = 'growth' | 'value' | 'income' | 'macro'

export interface ScorecardIn {
  growth: number | null // 0–3
  value: number | null
  income: number | null
  macro: number | null
  bull_catalysts: Catalyst[]
  bear_catalysts: Catalyst[]
  note: string | null
  target_pe: number | null
  target_pe_note: string | null
}

export type DividendMode = 'per_payment' | 'half' | 'annual' | 'uneven'

export interface DividendInput {
  mode: DividendMode
  amount: number | null
  frequency: 1 | 2 | 4 | 12 | null
  payments: number[]
}

export interface DividendResponse {
  input: DividendInput | null
  annual_dps: number | null // quote currency per share
  yahoo_ttm: number | null
}

export interface ScorecardResponse {
  current: (ScorecardIn & { id: number; created_at: string | null }) | null
  versions: number
  suggested: {
    as_of: string | null
    growth: { score: number | null; score_1_5: number | null; ref: string } | null
    value: { score: number | null; score_1_5: number | null; ref: string } | null
    income: { score: number | null; score_1_5: number | null; ref: string } | null
    macro?: null
    bull_catalysts: { text: string; date?: string }[]
    bear_catalysts: { text: string; date?: string }[]
  } | null
}

export interface MacroLink {
  factor: string
  channel: 'demand' | 'cost' | 'valuation' | 'earnings' | string
  direction: 'bull' | 'bear' | 'neutral'
  strength: 'negligible' | 'mild' | 'medium' | 'strong'
  speed: 'immediate' | 'near' | 'lagged'
  ref?: string
  sensitivity?: number // -2..+2 to the factor rising (medium counts as strong)
  move?: 'up' | 'down' | 'flat' | null // factor's latest 1-month move
  effect?: number | null // sensitivity × move: today's headwind (−) / tailwind (+); null = no data
}

export interface MacroSummary {
  tailwind: number
  tailwind_links: number
  headwind: number
  headwind_links: number
  neutral_links: number
  no_data_links: number
  net: number
  verdict: string
}

export interface Lever {
  base: string
  lever_name: string
  exposure: string
  exposure_pct: number | null
  speed: string
  direction: string
  macro_factor_code: string | null
  watch_metric: string | null
  current_reading: string | null
  pushes_low: string | null
  pushes_high: string | null
}

export interface CalendarEvent {
  date: string
  event: string
  type: string
  confirmed?: boolean
  source?: string
}

export interface AnalysisView {
  ticker: string
  factor_names: Record<string, string>
  analysis_id: number
  ingested_at: string | null
  data_as_of: string | null
  meta: ModelInputs['meta'] & { data_sources?: string[]; structure_note?: string; price_currency?: string }
  bottom_line: string | null
  macro: MacroLink[]
  macro_summary: MacroSummary
  levers: Lever[]
  calendar: CalendarEvent[]
  warnings: string[]
  stale: { is_stale: boolean; last_earnings: string | null }
  price: Price | null
  position: {
    quantity: number
    avg_price: number
    price: number
    value_gbp: number
    ppl_gbp: number
    ppl_pct: number
    weight_pct: number | null
  } | null
  what_changed: {
    previous_as_of: string | null
    rows: { year: string; eps_was: number; eps_now: number; revenue_was: number; revenue_now: number }[]
    new_years: string[]
    dropped_years: string[]
    bottom_line_was: string | null
  } | null
}

export interface AnalysesRow {
  ticker: string
  company: string
  held: boolean
  weight_pct: number | null
  ppl_pct: number | null
  price: number | null
  price_currency: string | null
  pe: number | null
  pe_year: string | null
  eps_cagr: number | null
  eps_cagr_years: string | null
  scores: { growth: number | null; value: number | null; income: number | null; macro: number | null } | null
  macro: MacroSummary
  stale: boolean
  data_as_of: string | null
}

export interface AnalysesList {
  rows: AnalysesRow[]
  holdings_available: boolean
  not_modelled: string[]
}
