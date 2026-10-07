// Mirrors backend/app/services/macro_view.py

export type Verdict = 'strong headwind' | 'headwind' | 'neutral' | 'tailwind' | 'strong tailwind'

export interface MacroFactor {
  code: string
  name: string
  series: string | null
  provider: string | null
  unit: 'pp' | '%'
  value: number | null
  as_of: string | null
  change: number | null
  move: 'up' | 'down' | 'flat' | null
  state: string
  spark: number[]
  affected: number
  used: boolean
}

export interface MacroLinkScored {
  factor: string
  channel: string
  direction: 'bull' | 'bear' | 'neutral'
  strength: string
  speed: string | null
  ref: string | null
  move: 'up' | 'down' | 'flat' | null
  score: number
}

export interface MacroHolding {
  ticker: string
  company: string | null
  weight_pct: number | null
  modelled: boolean
  links: MacroLinkScored[]
  score: number | null
  verdict: Verdict | null
  factor_scores: Record<string, number>
}

export interface MacroView {
  factors: MacroFactor[]
  matrix_factors: string[]
  holdings: MacroHolding[]
  tilt: { score: number | null; verdict: Verdict | null; modelled: number; total: number }
  warnings: string[]
}
