from fastapi import APIRouter, Depends, HTTPException

from app.crypto import get_t212_credentials
from app.deps import CurrentUser, get_current_user
from app.models.book import BookResponse, BookSummary, IndexExposureRow, LedgerRow
from app.services import expected_move, t212_client
from app.services.analysis_lookup import modelled_tickers
from app.services.company_names import company_name
from app.services.index_map import CONCENTRATION_LIMIT_PCT, INDEX_META, index_for_ticker
from app.services.market_data import parse_t212_ticker

router = APIRouter()


@router.get("/book", response_model=BookResponse)
def get_book(user: CurrentUser = Depends(get_current_user)) -> BookResponse:
    api_key, api_secret = get_t212_credentials(user.db, user.id)
    if not api_key:
        raise HTTPException(status_code=400, detail="No Trading212 credentials found. Save them in Settings.")

    try:
        cash_data = t212_client.get_cash(api_key, api_secret or "")
        positions = t212_client.get_positions(api_key, api_secret or "")
    except t212_client.T212Error as e:
        raise HTTPException(status_code=502, detail=str(e))

    free_cash = float(cash_data.get("free", 0))
    modelled = modelled_tickers(user.db)

    derived = [t212_client.derive_position_gbp(p) for p in positions]
    invested_gbp = sum(d["value_gbp"] for d in derived)
    total_book_gbp = invested_gbp + free_cash

    moves = expected_move.explain_holdings([
        {"ticker": d["ticker"], "yahoo": parse_t212_ticker(d["ticker"])[1], "index": index_for_ticker(d["ticker"])}
        for d in derived
    ])

    ledger: list[LedgerRow] = []
    for d in derived:
        ticker = d["ticker"]
        m = moves.get(ticker) or {}
        flag = m.get("category") if m.get("category") in ("unexplained", "earnings") else None
        ledger.append(
            LedgerRow(
                ticker=ticker,
                company=company_name(ticker),
                quantity=d["quantity"],
                price=d["curr_price"],
                cost_gbp=d["cost_gbp"],
                value_gbp=d["value_gbp"],
                ppl_gbp=d["ppl_gbp"],
                ppl_pct=d["ppl_pct"],
                weight_of_book_pct=(d["value_gbp"] / total_book_gbp * 100) if total_book_gbp else 0,
                cost_basis_of_book_pct=(d["cost_gbp"] / total_book_gbp * 100) if total_book_gbp else 0,
                index_code=index_for_ticker(ticker),
                modelled=parse_t212_ticker(ticker)[0] in modelled,
                today_vs_exp_pct=m.get("actual_pct"),
                expected_pct=m.get("expected_pct"),
                residual_pct=m.get("residual_pct"),
                z_score=m.get("z"),
                flag=flag,
                has_flag=flag == "unexplained",
                move_date=m.get("date"),
                index_beta=(m.get("betas") or {}).get("index"),
                fit_r2=m.get("r2"),
            )
        )
    ledger.sort(key=lambda r: r.weight_of_book_pct, reverse=True)

    if free_cash:
        ledger.append(
            LedgerRow(
                ticker="CASH",
                company="Cash",
                is_cash=True,
                cost_gbp=free_cash,
                value_gbp=free_cash,
                weight_of_book_pct=(free_cash / total_book_gbp * 100) if total_book_gbp else 0,
            )
        )

    # Weighting-by-index panel: share of invested (cash excluded from the denominator).
    index_totals: dict[str, float] = {}
    index_members: dict[str, list[str]] = {}
    for d in derived:
        code = index_for_ticker(d["ticker"])
        if not code:
            continue
        index_totals[code] = index_totals.get(code, 0) + d["value_gbp"]
        index_members.setdefault(code, []).append(parse_t212_ticker(d["ticker"])[0])

    index_exposure = []
    for code, value in index_totals.items():
        share_of_invested = (value / invested_gbp * 100) if invested_gbp else 0
        index_exposure.append(
            IndexExposureRow(
                code=code,
                name=INDEX_META.get(code, code),
                weight_of_book_pct=(value / total_book_gbp * 100) if total_book_gbp else 0,
                share_of_invested_pct=share_of_invested,
                over_limit=share_of_invested > CONCENTRATION_LIMIT_PCT,
                member_tickers=sorted(index_members.get(code, [])),
            )
        )
    index_exposure.sort(key=lambda r: r.weight_of_book_pct, reverse=True)

    no_model_count = sum(1 for d in derived if parse_t212_ticker(d["ticker"])[0] not in modelled)

    return BookResponse(
        summary=BookSummary(
            holdings_count=len(derived),
            total_book_gbp=total_book_gbp,
            no_model_count=no_model_count,
            unexplained_count=sum(r.has_flag for r in ledger),
        ),
        index_exposure=index_exposure,
        ledger=ledger,
        cash_gbp=free_cash,
        invested_gbp=invested_gbp,
    )
