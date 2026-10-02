"""Price and FX refresh into the prices / fx_rates tables.

Runs at session start (POST /api/market/refresh) and on demand. Anything fetched within
MAX_AGE is skipped, so repeated calls are cheap. Quotes come from Yahoo via yfinance;
fetch_quote is injectable so tests (or a future paid feed) can swap it out.
"""

import math
from datetime import datetime, timedelta, timezone

from supabase import Client

MAX_AGE = timedelta(minutes=15)
BASE_CCY = "GBP"   # portfolio currency; every quoted currency also gets an X->GBP rate

# Trading212 marks non-US listings with a lowercase letter on the symbol: HSBAl_EQ is LSE.
# Only suffixes we've confirmed are mapped; anything else needs yahoo_symbol set by hand.
_T212_SUFFIX_TO_YAHOO = {"l": ".L"}


def parse_t212_ticker(t212_ticker: str) -> tuple[str, str | None]:
    """'BROS_US_EQ' -> ('BROS', 'BROS'); 'HSBAl_EQ' -> ('HSBA', 'HSBA.L'); 'BRK_B_US_EQ' -> ('BRK_B', 'BRK-B')."""
    body = t212_ticker.removesuffix("_EQ")
    if body.endswith("_US"):
        base = body.removesuffix("_US")
        return base.upper(), base.upper().replace("_", "-")
    if body and body[-1].islower():
        base, suffix = body[:-1], body[-1]
        yahoo = base.upper() + _T212_SUFFIX_TO_YAHOO[suffix] if suffix in _T212_SUFFIX_TO_YAHOO else None
        return base.upper(), yahoo
    return body.upper(), None


def yahoo_quote(symbol: str) -> tuple[float, str] | None:
    """Latest (price, currency) from Yahoo, or None if it can't be fetched."""
    import yfinance as yf

    try:
        info = yf.Ticker(symbol).fast_info
        price, currency = info["last_price"], info["currency"]
    except Exception:
        return None
    if price is None or (isinstance(price, float) and math.isnan(price)) or not currency:
        return None
    return float(price), currency


def _major(ccy: str | None) -> str | None:
    if not ccy:
        return None
    return "GBP" if ccy in ("GBp", "GBX") else ccy.upper()


def _is_fresh(fetched_at: str | None, now: datetime) -> bool:
    if not fetched_at:
        return False
    return now - datetime.fromisoformat(fetched_at) < MAX_AGE


def sync_instruments(db: Client, t212_tickers: list[str]) -> None:
    """Make sure every held position has an instrument row with its T212 and Yahoo symbols."""
    existing = {r["ticker"]: r for r in db.table("instruments").select("id, ticker, t212_ticker, yahoo_symbol").execute().data}
    for t212 in t212_tickers:
        ticker, yahoo = parse_t212_ticker(t212)
        row = existing.get(ticker)
        if row is None:
            db.table("instruments").insert({"ticker": ticker, "t212_ticker": t212, "yahoo_symbol": yahoo}).execute()
            continue
        missing = {}
        if not row.get("t212_ticker"):
            missing["t212_ticker"] = t212
        if not row.get("yahoo_symbol") and yahoo:
            missing["yahoo_symbol"] = yahoo
        if missing:
            db.table("instruments").update(missing).eq("id", row["id"]).execute()


def refresh_market_data(db: Client, fetch_quote=yahoo_quote, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    today = now.date().isoformat()

    instruments = db.table("instruments").select("id, ticker, yahoo_symbol").execute().data
    todays = {r["instrument_id"]: r for r in db.table("prices").select("instrument_id, fetched_at, currency").eq("price_date", today).execute().data}

    summary = {"prices_updated": 0, "prices_fresh": 0, "fx_updated": 0, "fx_fresh": 0,
               "failed": [], "unmapped": []}
    quoted_ccy = {}
    for inst in instruments:
        sym = inst.get("yahoo_symbol")
        if not sym:
            summary["unmapped"].append(inst["ticker"])
            continue
        prev = todays.get(inst["id"])
        if prev and _is_fresh(prev["fetched_at"], now):
            summary["prices_fresh"] += 1
            quoted_ccy[inst["id"]] = prev["currency"]
            continue
        quote = fetch_quote(sym)
        if quote is None:
            summary["failed"].append(sym)
            continue
        price, ccy = quote
        db.table("prices").upsert({
            "instrument_id": inst["id"], "price_date": today, "close": price, "currency": ccy,
            "source": "yahoo", "fetched_at": now.isoformat(),
        }, on_conflict="instrument_id,price_date").execute()
        quoted_ccy[inst["id"]] = ccy
        summary["prices_updated"] += 1

    # FX: every quoted currency -> GBP, plus each current analysis's EPS currency -> its quote currency.
    pairs = {(_major(c), BASE_CCY) for c in quoted_ccy.values()}
    current = db.table("analyses").select("instrument_id, reporting_currency, price_currency").eq("is_current", True).execute().data
    for a in current:
        pairs.add((_major(a["reporting_currency"]), _major(quoted_ccy.get(a["instrument_id"]) or a["price_currency"])))
    pairs = sorted((f, t) for f, t in pairs if f and t and f != t)

    todays_fx = {(r["from_ccy"], r["to_ccy"]): r for r in db.table("fx_rates").select("from_ccy, to_ccy, fetched_at").eq("rate_date", today).execute().data}
    for f, t in pairs:
        prev = todays_fx.get((f, t))
        if prev and _is_fresh(prev["fetched_at"], now):
            summary["fx_fresh"] += 1
            continue
        quote = fetch_quote(f"{f}{t}=X")
        if quote is None:
            summary["failed"].append(f"{f}{t}=X")
            continue
        db.table("fx_rates").upsert({
            "from_ccy": f, "to_ccy": t, "rate_date": today, "rate": quote[0],
            "source": "yahoo", "fetched_at": now.isoformat(),
        }, on_conflict="from_ccy,to_ccy,rate_date").execute()
        summary["fx_updated"] += 1

    return summary
