"""Index CAGR since the first deposit, for the Dashboard's "CAGR vs indices" comparison."""

import math
from datetime import date

from app.services.deposits import cagr_pct

INDICES = [
    ("S&P 500", "^GSPC"),
    ("Nasdaq 100", "^NDX"),
    ("FTSE 100", "^FTSE"),
    ("German DAX", "^GDAXI"),
    ("Nikkei 225", "^N225"),
]

# Daily closes move once a day, so results are kept per (symbol, start, today).
_cache: dict[tuple[str, str, str], float | None] = {}


def yahoo_first_last_close(symbol: str, start: str) -> tuple[float, float] | None:
    import yfinance as yf

    try:
        closes = yf.Ticker(symbol).history(start=start, auto_adjust=True)["Close"].dropna()
    except Exception:
        return None
    if closes.empty:
        return None
    first, last = float(closes.iloc[0]), float(closes.iloc[-1])
    if math.isnan(first) or math.isnan(last):
        return None
    return first, last


def index_cagrs(start: str, years: float, fetch=yahoo_first_last_close, today: date | None = None) -> list[dict]:
    today_key = (today or date.today()).isoformat()
    out = []
    for name, symbol in INDICES:
        key = (symbol, start, today_key)
        if key not in _cache:
            closes = fetch(symbol, start)
            _cache[key] = cagr_pct(closes[1], closes[0], years) if closes else None
        out.append({"name": name, "symbol": symbol, "cagr_pct": _cache[key]})
    return out
