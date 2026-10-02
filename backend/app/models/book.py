from pydantic import BaseModel


class LedgerRow(BaseModel):
    ticker: str
    company: str
    is_cash: bool = False
    quantity: float | None = None
    price: float | None = None
    cost_gbp: float
    value_gbp: float
    ppl_gbp: float | None = None
    ppl_pct: float | None = None
    weight_of_book_pct: float          # value_gbp / total_book_gbp * 100
    cost_basis_of_book_pct: float | None = None  # cost_gbp / total_book_gbp * 100, for the weight-bar dot
    index_code: str | None = None
    modelled: bool = False
    # Deferred to a future pass (needs the expected-move regression model): always null this pass.
    today_vs_exp_pct: float | None = None
    has_flag: bool = False
    z_score: float | None = None
    # Deferred to a future pass (needs analysis EPS x macro-adjustment, and Macro doesn't exist yet).
    live_pe: float | None = None
    # Deferred to a future pass (needs EPS-scenario x forward-PE derivation from Analysis).
    band_pct: float | None = None
    band_low: float | None = None
    band_high: float | None = None


class IndexExposureRow(BaseModel):
    code: str
    name: str
    weight_of_book_pct: float          # share of total book incl. cash
    share_of_invested_pct: float       # share of book excl. cash — drives the bar + limit check
    over_limit: bool
    member_tickers: list[str]


class BookSummary(BaseModel):
    holdings_count: int
    total_book_gbp: float
    unexplained_count: int = 0         # deferred, always 0 this pass
    no_model_count: int


class BookResponse(BaseModel):
    summary: BookSummary
    index_exposure: list[IndexExposureRow]
    ledger: list[LedgerRow]
    cash_gbp: float
    invested_gbp: float
