// Mirrors backend/app/models/account.py

export interface AccountSummary {
  portfolio_value_gbp: number
  cost_basis_gbp: number
  cash_gbp: number
  cash_pct_of_book: number | null
  unrealised_ppl_gbp: number
  unrealised_ppl_pct: number | null
  net_deposited_gbp: number | null
  first_deposit_date: string | null
  total_return_gbp: number | null
  total_return_pct: number | null
  cagr_pct: number | null
  years: number | null
  warnings: string[]
}

export interface BenchmarkCagr {
  name: string
  symbol: string
  cagr_pct: number | null
}

export interface BenchmarksResponse {
  since: string | null
  years: number | null
  indices: BenchmarkCagr[]
}
