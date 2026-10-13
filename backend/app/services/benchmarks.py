"""Index returns for the Dashboard's "vs indices" comparison, money-weighted like the account.

Each index is run on the same deposits: every dated flow buys (or a withdrawal sells) index
units at that day's close, and the XIRR of those flows against today's value is compared
with the account's. Index levels are in their own currency; FX is ignored, as before.
"""

import bisect
import hashlib
import json
import math
from datetime import date

from app.services.deposits import xirr_pct

INDICES = [
    ("S&P 500", "^GSPC"),
    ("Nasdaq 100", "^NDX"),
    ("FTSE 100", "^FTSE"),
    ("German DAX", "^GDAXI"),
    ("Nikkei 225", "^N225"),
]

# Daily closes move once a day, so results are kept per (symbol, flows, today).
_cache: dict[tuple[str, str, str], float | None] = {}


def yahoo_closes(symbol: str, start: str) -> list[tuple[str, float]] | None:
    """[(YYYY-MM-DD, close)] from start to today, oldest first."""
    import yfinance as yf

    try:
        closes = yf.Ticker(symbol).history(start=start, auto_adjust=True)["Close"].dropna()
    except Exception:
        return None
    out = [(ts.date().isoformat(), float(c)) for ts, c in closes.items() if not math.isnan(float(c))]
    return out or None


def index_mwr_pct(flows: dict[str, float], closes: list[tuple[str, float]], today: date) -> float | None:
    """Money-weighted return if each flow had gone into the index at that day's close (or the last one before)."""
    days = [d for d, _ in closes]
    units = 0.0
    for d, amount in sorted(flows.items()):
        i = bisect.bisect_right(days, d) - 1
        close = closes[max(i, 0)][1]   # a flow before the first close uses the first close
        units += amount / close
    return xirr_pct(flows, units * closes[-1][1], today)


def index_returns(flows: dict[str, float], fetch=yahoo_closes, today: date | None = None) -> list[dict]:
    today = today or date.today()
    start = min(flows)
    flows_key = hashlib.sha1(json.dumps(flows, sort_keys=True).encode()).hexdigest()[:12]
    out = []
    for name, symbol in INDICES:
        key = (symbol, flows_key, today.isoformat())
        if key not in _cache:
            closes = fetch(symbol, start)
            _cache[key] = index_mwr_pct(flows, closes, today) if closes else None
        out.append({"name": name, "symbol": symbol, "cagr_pct": _cache[key]})
    return out
