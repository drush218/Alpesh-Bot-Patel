"""Dashboard tiles: Book day move, Macro read, Analysis subject, Indices, Calendar + dividends.

Day moves and index levels come from Yahoo (last vs previous close), earnings dates from
Yahoo's calendar and dividends as the trailing 12 months paid per share. Yahoo is slow per
symbol, so lookups run in parallel and are cached (quotes 15 min, calendar/dividends a day).
Day P&L applies each holding's local-currency day return to its GBP value, so FX moves on
the day are not included.
"""

import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

from supabase import Client

from app.crypto import get_t212_credentials
from app.services import macro_view, t212_client
from app.services.analysis_view import staleness
from app.services.index_map import CONCENTRATION_LIMIT_PCT, INDEX_META, INDEX_YAHOO, index_for_ticker
from app.services.market_data import parse_t212_ticker
from app.services.workspace import latest_price

QUOTE_TTL = 15 * 60
SLOW_TTL = 24 * 60 * 60
_cache: dict[tuple[str, str], tuple[float, object]] = {}
_lock = threading.Lock()


def _cached(kind: str, key: str, ttl: float, fn):
    with _lock:
        hit = _cache.get((kind, key))
        if hit and time.monotonic() - hit[0] < ttl:
            return hit[1]
    try:
        val = fn()
    except Exception:
        val = None
    with _lock:
        _cache[(kind, key)] = (time.monotonic(), val)
    return val


def _quote(symbol: str):
    def f():
        import yfinance as yf
        fi = yf.Ticker(symbol).fast_info
        last, prev = float(fi["last_price"]), float(fi["previous_close"])
        if math.isnan(last) or math.isnan(prev) or not prev:
            return None
        return {"last": last, "prev": prev, "day_pct": (last / prev - 1) * 100, "currency": fi["currency"]}
    return _cached("quote", symbol, QUOTE_TTL, f)


def _next_earnings(symbol: str):
    def f():
        import yfinance as yf
        dates = (yf.Ticker(symbol).calendar or {}).get("Earnings Date") or []
        future = sorted(d for d in dates if d >= date.today())
        return future[0].isoformat() if future else None
    return _cached("earnings", symbol, SLOW_TTL, f)


def _ttm_dividend(symbol: str):
    def f():
        import yfinance as yf
        divs = yf.Ticker(symbol).dividends
        if divs is None or divs.empty:
            return 0.0
        cutoff = datetime.now(timezone.utc) - timedelta(days=365)
        return float(divs[divs.index >= cutoff].sum())
    return _cached("divs", symbol, SLOW_TTL, f)


def _parallel(fn, items):
    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(zip(items, pool.map(fn, items)))


def dashboard(db: Client, user_id: str) -> dict:
    api_key, secret = get_t212_credentials(db, user_id)
    if not api_key:
        return {"error": "No Trading212 credentials found. Save them in Settings."}
    try:
        positions = t212_client.get_positions(api_key, secret or "")
        cash = float(t212_client.get_cash(api_key, secret or "").get("free", 0))
    except t212_client.T212Error as e:
        return {"error": str(e)}

    held = []
    for p in positions:
        d = t212_client.derive_position_gbp(p)
        ticker, yahoo = parse_t212_ticker(d["ticker"])
        fx = d["value_gbp"] / (d["quantity"] * d["curr_price"]) if d["quantity"] and d["curr_price"] else None
        held.append({**d, "ticker": ticker, "yahoo": yahoo, "fx_to_gbp": fx, "index": index_for_ticker(ticker)})
    invested = sum(h["value_gbp"] for h in held)
    book = invested + cash
    symbols = [h["yahoo"] for h in held if h["yahoo"]]
    quotes = _parallel(_quote, symbols + list(INDEX_YAHOO.values()))
    earnings = _parallel(_next_earnings, symbols)
    divs = _parallel(_ttm_dividend, symbols)

    # Book tile
    moves = []
    for h in held:
        q = quotes.get(h["yahoo"]) if h["yahoo"] else None
        if q:
            moves.append({"ticker": h["ticker"], "day_pct": q["day_pct"], "pnl_gbp": h["value_gbp"] * (1 - 1 / (1 + q["day_pct"] / 100))})
    day_pnl = sum(m["pnl_gbp"] for m in moves)
    book_tile = {
        "day_pnl_gbp": day_pnl,
        "day_pct": day_pnl / (book - day_pnl) * 100 if book - day_pnl else None,
        "best": max(moves, key=lambda m: m["day_pct"], default=None),
        "worst": min(moves, key=lambda m: m["day_pct"], default=None),
        "up": sum(m["day_pct"] > 0 for m in moves),
        "down": sum(m["day_pct"] < 0 for m in moves),
        "priced": len(moves),
        "holdings": len(held),
        "flags": None,      # expected-move model not built yet
    }

    # Indices tile
    by_index: dict[str, float] = {}
    for h in held:
        if h["index"]:
            by_index[h["index"]] = by_index.get(h["index"], 0) + h["value_gbp"]
    unmapped = sum(h["value_gbp"] for h in held if not h["index"])
    indices = []
    for code, name in INDEX_META.items():
        q = quotes.get(INDEX_YAHOO.get(code, ""))
        w = by_index.get(code, 0)
        if not w and code not in ("NDX", "SPX", "UKX"):
            continue
        share = w / invested * 100 if invested else 0
        indices.append({"code": code, "name": name, "level": q["last"] if q else None, "day_pct": q["day_pct"] if q else None,
                        "weight_pct": w / book * 100 if book else 0, "share_of_invested_pct": share,
                        "over_limit": share > CONCENTRATION_LIMIT_PCT})
    indices.sort(key=lambda r: r["weight_pct"], reverse=True)

    # Calendar tile
    horizon = (date.today() + timedelta(days=30)).isoformat()
    upcoming = sorted(({"ticker": h["ticker"], "date": earnings.get(h["yahoo"])} for h in held if earnings.get(h["yahoo"])), key=lambda e: e["date"])
    run_rate = 0.0
    for h in held:
        per_share = divs.get(h["yahoo"]) or 0.0
        # Yahoo pays per share in the quote unit (pence for London), the same unit T212 prices in,
        # so the T212-derived fx_to_gbp converts it.
        if per_share and h["fx_to_gbp"]:
            run_rate += per_share * h["quantity"] * h["fx_to_gbp"]
    calendar = {
        "earnings": [e for e in upcoming if e["date"] <= horizon],
        "later": upcoming[:3] if not any(e["date"] <= horizon for e in upcoming) else [],
        "dividend_run_rate_gbp": run_rate,
        "yield_on_book_pct": run_rate / book * 100 if book else None,
    }

    # Macro tile
    mv = macro_view.macro_view(db, user_id)
    used = [f for f in mv["factors"] if f["used"] and f["change"] is not None][:4]
    affected = sorted((h for h in mv["holdings"] if h["modelled"] and h["score"]), key=lambda h: abs(h["score"]) * (h["weight_pct"] or 0), reverse=True)[:3]
    macro_tile = {
        "tilt": mv["tilt"],
        "factors": [{"code": f["code"], "name": f["name"], "change": f["change"], "unit": f["unit"], "move": f["move"]} for f in used],
        "most_affected": [{"ticker": h["ticker"], "weight_pct": h["weight_pct"], "verdict": h["verdict"]} for h in affected],
    }

    # Analysis tile: the stalest current analysis, else the first
    rows = db.table("analyses").select("model, data_as_of, instrument_id, reporting_currency, instruments(ticker)").eq("is_current", True).execute().data
    subject = None
    for r in rows:
        st = staleness(r["model"], r["data_as_of"])
        cand = {"ticker": r["instruments"]["ticker"], "data_as_of": r["data_as_of"], **st, "_model": r["model"],
                "_iid": r["instrument_id"], "_ccy": r.get("reporting_currency")}
        if subject is None or (cand["is_stale"] and not subject["is_stale"]) or (cand["is_stale"] == subject["is_stale"] and (cand["data_as_of"] or "") < (subject["data_as_of"] or "")):
            subject = cand
    analysis_tile = None
    if subject:
        m = subject.pop("_model")
        stored = latest_price(db, subject.pop("_iid"), subject.pop("_ccy"))
        held_row = next((h for h in held if h["ticker"] == subject["ticker"]), None)
        q = quotes.get(held_row["yahoo"]) if held_row and held_row["yahoo"] else None
        ref = (m.get("meta") or {}).get("reference_price")
        out = (m.get("outputs") or {}).get("scenarios", {})
        first_year = (m.get("meta") or {}).get("forecast_years", [None])[0]
        analysis_tile = {
            **subject,
            "price": q["last"] if q else (held_row or {}).get("curr_price"),
            "reference_price": ref["value"] if ref else None,
            "year": first_year,
            "eps_low": out["low"][0]["eps"] if out.get("low") else None,
            "eps_high": out["high"][0]["eps"] if out.get("high") else None,
            "fx": stored["fx"] if stored else 1.0,     # EPS currency -> quote currency
            "currency": stored["currency"] if stored else None,
            "count": len(rows),
        }

    return {
        "book": book_tile,
        "macro": macro_tile,
        "analysis": analysis_tile,
        "indices": {"rows": indices, "cash_pct": cash / book * 100 if book else 0, "unmapped_pct": unmapped / book * 100 if book else 0},
        "calendar": calendar,
    }
