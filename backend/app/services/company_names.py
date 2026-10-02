from functools import lru_cache

import yfinance as yf


@lru_cache(maxsize=256)
def company_name(ticker: str) -> str:
    clean = ticker.split("_")[0]
    try:
        info = yf.Ticker(clean).info
        return info.get("longName") or info.get("shortName") or clean
    except Exception:
        return clean
