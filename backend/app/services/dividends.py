"""The user's dividend input per stock (Analysis screen Income panel).

Amounts are per share in the quote currency. Yahoo's trailing-12-month total is returned
alongside as a sanity check only; the user's figure is what the yields use.
"""

from datetime import datetime, timezone

from supabase import Client

from app.services.dashboard import _ttm_dividend
from app.services.workspace import NotFound

MODES = ("per_payment", "half", "annual", "uneven")


def annual_dps(inp: dict | None) -> float | None:
    if not inp:
        return None
    mode, amount = inp["mode"], inp.get("amount")
    if mode == "uneven":
        return float(sum(inp.get("payments") or []))
    if amount is None:
        return None
    if mode == "per_payment":
        return float(amount) * (inp.get("frequency") or 1)
    if mode == "half":
        return float(amount) * 2
    return float(amount)


def _instrument(db: Client, ticker: str) -> dict:
    rows = db.table("instruments").select("id, yahoo_symbol").eq("ticker", ticker.upper()).execute().data
    if not rows:
        raise NotFound(f"No instrument {ticker}")
    return rows[0]


def get_dividend(db: Client, user_id: str, ticker: str) -> dict:
    inst = _instrument(db, ticker)
    rows = (db.table("dividend_inputs").select("mode, amount, frequency, payments")
            .eq("user_id", user_id).eq("instrument_id", inst["id"]).execute().data)
    inp = rows[0] if rows else None
    if inp and inp.get("amount") is not None:
        inp["amount"] = float(inp["amount"])
    return {
        "input": inp,
        "annual_dps": annual_dps(inp),
        "yahoo_ttm": _ttm_dividend(inst["yahoo_symbol"]) if inst.get("yahoo_symbol") else None,
    }


def save_dividend(db: Client, user_id: str, ticker: str, inp: dict) -> dict:
    inst = _instrument(db, ticker)
    db.table("dividend_inputs").upsert({
        "user_id": user_id,
        "instrument_id": inst["id"],
        "mode": inp["mode"],
        "amount": inp.get("amount") if inp["mode"] != "uneven" else None,
        "frequency": inp.get("frequency") if inp["mode"] == "per_payment" else None,
        "payments": (inp.get("payments") or []) if inp["mode"] == "uneven" else [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    return get_dividend(db, user_id, ticker)


def clear_dividend(db: Client, user_id: str, ticker: str) -> dict:
    inst = _instrument(db, ticker)
    db.table("dividend_inputs").delete().eq("user_id", user_id).eq("instrument_id", inst["id"]).execute()
    return get_dividend(db, user_id, ticker)
