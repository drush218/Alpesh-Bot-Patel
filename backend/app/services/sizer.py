"""Context for the position sizer: live quote + GBP conversion, book value, current holding,
and the analysis band (if there is a current analysis) to seed target / stop.

Book value is the Streamlit calculator's conservative figure: the lower of cost basis and
market value of the invested part, plus cash.
"""

from supabase import Client

from app.crypto import get_t212_credentials
from app.services import t212_client
from app.services.dashboard import _quote
from app.services.market_data import parse_t212_ticker
from app.services.workspace import NotFound, current_analysis, latest_price


def _fx_to_gbp(currency: str | None) -> float | None:
    if currency in ("GBP",):
        return 1.0
    if currency in ("GBp", "GBX"):
        return 0.01
    if not currency:
        return None
    q = _quote(f"{currency.upper()}GBP=X")
    return q["last"] if q else None


def sizer_context(db: Client, user_id: str, ticker: str) -> dict:
    ticker = ticker.strip().upper()
    inst = db.table("instruments").select("id, yahoo_symbol").eq("ticker", ticker).execute().data
    symbol = (inst[0].get("yahoo_symbol") if inst else None) or ticker
    q = _quote(symbol)
    out: dict = {"ticker": ticker, "symbol": symbol, "warnings": []}
    if q:
        out.update(price=q["last"], currency=q["currency"], fx_to_gbp=_fx_to_gbp(q["currency"]))
    else:
        out.update(price=None, currency=None, fx_to_gbp=None)
        out["warnings"].append(f"No live quote for {symbol} on Yahoo. Enter the price by hand.")

    api_key, secret = get_t212_credentials(db, user_id)
    out["book"] = None
    out["held"] = None
    if api_key:
        try:
            cash = t212_client.get_cash(api_key, secret or "")
            positions = t212_client.get_positions(api_key, secret or "")
            invested, free, ppl = float(cash.get("invested", 0)), float(cash.get("free", 0)), float(cash.get("ppl", 0))
            out["book"] = {"conservative_gbp": min(invested, invested + ppl) + free, "total_gbp": float(cash.get("total", invested + free + ppl))}
            for p in positions:
                if parse_t212_ticker(p.get("ticker", ""))[0] == ticker:
                    d = t212_client.derive_position_gbp(p)
                    out["held"] = {"quantity": d["quantity"], "value_gbp": d["value_gbp"]}
        except t212_client.T212Error as e:
            out["warnings"].append(f"Trading212 unavailable: {e}")

    try:
        base = current_analysis(db, ticker)
        sc = base["outputs"]["scenarios"]
        stored = latest_price(db, base["instrument_id"], base["inputs"]["meta"].get("reporting_currency"))
        out["analysis"] = {
            "data_as_of": base["inputs"]["meta"].get("data_as_of"),
            "years": base["inputs"]["meta"]["forecast_years"],
            "eps": {k: [r["eps"] for r in sc[k]] for k in ("low", "bau", "high")},
            "fx": stored["fx"] if stored and stored["fx"] is not None else 1.0,
        }
    except (NotFound, KeyError, TypeError):
        out["analysis"] = None
    return out
