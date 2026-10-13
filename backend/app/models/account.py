from pydantic import BaseModel


class AccountSummary(BaseModel):
    portfolio_value_gbp: float
    cost_basis_gbp: float
    cash_gbp: float
    cash_pct_of_book: float | None = None
    unrealised_ppl_gbp: float
    unrealised_ppl_pct: float | None = None
    # Deposit-based figures; null until the transaction history has been scanned once.
    net_deposited_gbp: float | None = None
    first_deposit_date: str | None = None
    total_return_gbp: float | None = None
    total_return_pct: float | None = None
    cagr_pct: float | None = None          # money-weighted (XIRR on dated deposits)
    simple_cagr_pct: float | None = None   # old figure: every deposit treated as made on day one
    years: float | None = None
    warnings: list[str] = []


class BenchmarkCagr(BaseModel):
    name: str
    symbol: str
    cagr_pct: float | None = None


class BenchmarksResponse(BaseModel):
    since: str | None = None
    years: float | None = None
    indices: list[BenchmarkCagr]
