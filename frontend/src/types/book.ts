// Mirrors backend/app/models/book.py

export interface LedgerRow {
  ticker: string
  company: string
  is_cash: boolean
  quantity: number | null
  price: number | null
  cost_gbp: number
  value_gbp: number
  ppl_gbp: number | null
  ppl_pct: number | null
  weight_of_book_pct: number
  cost_basis_of_book_pct: number | null
  index_code: string | null
  modelled: boolean
  today_vs_exp_pct: number | null
  has_flag: boolean
  z_score: number | null
  live_pe: number | null
  band_pct: number | null
  band_low: number | null
  band_high: number | null
}

export interface IndexExposureRow {
  code: string
  name: string
  weight_of_book_pct: number
  share_of_invested_pct: number
  over_limit: boolean
  member_tickers: string[]
}

export interface BookSummary {
  holdings_count: number
  total_book_gbp: number
  unexplained_count: number
  no_model_count: number
}

export interface BookResponse {
  summary: BookSummary
  index_exposure: IndexExposureRow[]
  ledger: LedgerRow[]
  cash_gbp: number
  invested_gbp: number
}
