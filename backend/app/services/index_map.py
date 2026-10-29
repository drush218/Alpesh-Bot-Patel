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
    "MCX": "FTSE 250",
    "AIM": "FTSE AIM All-Share",
}

# code -> Yahoo symbol, for levels and day moves
INDEX_YAHOO: dict[str, str] = {
    "NDX": "^NDX",
    "SPX": "^GSPC",
    "RUT": "^RUT",
    "TWII": "^TWII",
    "UKX": "^FTSE",
    "MCX": "^FTMC",
    "AIM": "^FTAI",
}

TICKER_INDEX: dict[str, str] = {
    # Current holdings (Oct 2026). ONON is NYSE-listed but in none of these; S&P 500 is the
    # closest benchmark. BGEO / UKW / GRG are FTSE 250, CAML is on AIM.
    "PYPL": "NDX",
    "MELI": "NDX",
    "SMCI": "SPX",
    "DECK": "SPX",
    "UBER": "SPX",
    "ONON": "SPX",
    "SOFI": "SPX",   # Nasdaq-listed, not in the S&P 500 or Nasdaq 100 (as of mid-2026); S&P 500 is the closest benchmark
    "BGEO": "MCX",
    "UKW": "MCX",
    "GRG": "MCX",
    "CAML": "AIM",
    # From the design prototype's sample book.
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
    """Accepts our ticker (BGEO) or the T212 one (BGEOl_EQ, MSFT_US_EQ)."""
    from app.services.market_data import parse_t212_ticker
    clean = parse_t212_ticker(ticker)[0] if ticker.endswith("_EQ") else ticker.upper()
    return TICKER_INDEX.get(clean)
