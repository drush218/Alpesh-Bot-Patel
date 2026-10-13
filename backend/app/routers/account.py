from fastapi import APIRouter, Depends, HTTPException

from app.crypto import get_t212_credentials
from app.deps import CurrentUser, get_current_user
from app.models.account import AccountSummary, BenchmarkCagr, BenchmarksResponse
from app.services import benchmarks, deposits, t212_client

router = APIRouter()


@router.get("/account", response_model=AccountSummary)
def get_account(user: CurrentUser = Depends(get_current_user)) -> AccountSummary:
    api_key, api_secret = get_t212_credentials(user.db, user.id)
    if not api_key:
        raise HTTPException(status_code=400, detail="No Trading212 credentials found. Save them in Settings.")

    try:
        cash = t212_client.get_cash(api_key, api_secret or "")
    except t212_client.T212Error as e:
        raise HTTPException(status_code=502, detail=str(e))

    invested = float(cash.get("invested", 0))
    free = float(cash.get("free", 0))
    ppl = float(cash.get("ppl", 0))
    total = float(cash.get("total", invested + free + ppl))

    summary = AccountSummary(
        portfolio_value_gbp=total,
        cost_basis_gbp=invested,
        cash_gbp=free,
        cash_pct_of_book=(free / total * 100) if total else None,
        unrealised_ppl_gbp=ppl,
        unrealised_ppl_pct=(ppl / invested * 100) if invested else None,
    )

    try:
        stats = deposits.get_deposit_stats(user.db, user.id, api_key, api_secret or "")
    except t212_client.T212Error as e:
        summary.warnings.append(f"Deposit history not loaded: {e}")
        return summary

    deposited = stats["total_deposited"] if stats else 0
    if deposited:
        years = deposits.years_since(stats["first_deposit_date"])
        summary.net_deposited_gbp = deposited
        summary.first_deposit_date = stats["first_deposit_date"]
        summary.total_return_gbp = total - deposited
        summary.total_return_pct = (total - deposited) / deposited * 100
        summary.years = years
        summary.simple_cagr_pct = deposits.cagr_pct(total, deposited, years)
        summary.cagr_pct = deposits.xirr_pct(stats["flows"], total) if stats.get("flows") else None
    return summary


@router.get("/account/benchmarks", response_model=BenchmarksResponse)
def get_benchmarks(user: CurrentUser = Depends(get_current_user)) -> BenchmarksResponse:
    """Money-weighted index returns on the account's own deposits. Uses cached deposit stats only (no T212 call)."""
    stats = deposits.load_cached(user.db, user.id)
    flows = stats.get("flows") if stats else None
    since = stats["first_deposit_date"] if stats else None
    if not flows or not since:
        return BenchmarksResponse(indices=[BenchmarkCagr(name=n, symbol=s) for n, s in benchmarks.INDICES])
    return BenchmarksResponse(
        since=since[:10],
        years=deposits.years_since(since),
        indices=[BenchmarkCagr(**row) for row in benchmarks.index_returns(flows)],
    )
