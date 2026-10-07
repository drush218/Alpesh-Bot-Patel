// Mirrors backend/app/services/dashboard.py
import type { MacroView, Verdict } from './macro'

export interface DayMove {
  ticker: string
  day_pct: number
  pnl_gbp: number
}

export interface DashboardData {
  error?: string
  book: {
    day_pnl_gbp: number
    day_pct: number | null
    best: DayMove | null
    worst: DayMove | null
    up: number
    down: number
    priced: number
    holdings: number
    flags: { ticker: string; category: 'unexplained' | 'earnings'; actual_pct: number; expected_pct: number; z: number; modelled: boolean }[]
  }
  macro: {
    tilt: MacroView['tilt']
    factors: { code: string; name: string; change: number; unit: 'pp' | '%'; move: 'up' | 'down' | 'flat' | null }[]
    most_affected: { ticker: string; weight_pct: number | null; verdict: Verdict | null }[]
  }
  analysis: {
    ticker: string
    data_as_of: string | null
    is_stale: boolean
    last_earnings: string | null
    price: number | null
    reference_price: number | null
    year: string | null
    eps_low: number | null
    eps_high: number | null
    fx: number | null
    currency: string | null
    count: number
  } | null
  indices: {
    rows: { code: string; name: string; level: number | null; day_pct: number | null; weight_pct: number; share_of_invested_pct: number; over_limit: boolean }[]
    cash_pct: number
    unmapped_pct: number
  }
  calendar: {
    earnings: { ticker: string; date: string }[]
    later: { ticker: string; date: string }[]
    dividend_run_rate_gbp: number
    yield_on_book_pct: number | null
  }
}
