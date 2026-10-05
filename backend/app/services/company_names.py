from functools import lru_cache

import yfinance as yf


@lru_cache(maxsize=256)
def company_name(ticker: str) -> str:
    """Name from Yahoo for a T212 ticker (BGEOl_EQ -> BGEO.L), falling back to our ticker."""
    from app.services.market_data import parse_t212_ticker
    clean, yahoo = parse_t212_ticker(ticker) if ticker.endswith("_EQ") else (ticker, ticker)
    if not yahoo:
        return clean
    try:
        info = yf.Ticker(yahoo).info
        return info.get("longName") or info.get("shortName") or clean
    except Exception:
        return clean
