"""Hand-maintained ticker -> primary benchmark index map.

Per DATA_MODEL.md: assigned by primary listing, a judgement call in places
(several names sit in more than one index, ADRs like TSM/ASML could
reasonably map to either the home market or the US listing). Not derived —
edit this table directly when a mapping should change.
"""

CONCENTRATION_LIMIT_PCT = 40.0

# code -> display name
INDEX_META: dict[str, str] = {
    "NDX": "Nasdaq 100",
    "SPX": "S&P 500",
    "RUT": "Russell 2000",
    "TWII": "Taiwan TAIEX",
    "UKX": "FTSE 100",
}

TICKER_INDEX: dict[str, str] = {
    "MSFT": "NDX",
    "COST": "NDX",
    "ASML": "NDX",
    "SBUX": "NDX",
    "V": "SPX",
    "CMG": "SPX",
    "CAVA": "RUT",
    "WING": "RUT",
    "BROS": "RUT",
    "TSM": "TWII",
    "SHEL": "UKX",
    "RIO": "UKX",
}


def index_for_ticker(ticker: str) -> str | None:
    clean = ticker.split("_")[0].upper()
    return TICKER_INDEX.get(clean)
