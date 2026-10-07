"""Macro factor series into macro_factor_moves (one row per factor per observation date).

Each row's change/move is against the observation about a month earlier, which is what the
Macro screen shows ("1m +2.8%") and what v_macro_cross flips directions on. Sources are FRED's
public CSV download (no key needed); a factor's own series/provider in macro_factors wins over
the defaults here, so an approved proposal like us_gasoline_retail (GASREGW, FRED) just works.
"""

import csv
import io
import threading
from datetime import date, timedelta

import requests
from supabase import Client

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"
HISTORY = timedelta(days=730)
WINDOW = timedelta(days=30)        # "1m" comparison
UPSERT_TAIL = 90                   # rows re-written per refresh (older ones never change)

# code -> (provider, series, kind). kind: "rate" moves are absolute points, "level" relative %.
DEFAULTS = {
    "rates_policy":   ("FRED", "DFF", "rate"),
    "rates_10y":      ("FRED", "DGS10", "rate"),
    "fx_usd":         ("FRED", "DTWEXBGS", "level"),
    "oil":            ("FRED", "DCOILBRENTEU", "level"),
    "natgas":         ("FRED", "DHHNGSP", "level"),
    "labour":         ("FRED", "CES0500000003", "slow"),
    "consumer_spend": ("FRED", "RSAFS", "slow"),
    "credit_spreads": ("FRED", "BAMLH0A0HYM2", "rate"),
    "inflation":      ("FRED", "T10YIE", "rate"),
    # china_activity: no default. FRED's OECD China CLI (CHNLOLITONOSTSAM) stopped in Jan 2024;
    # set macro_factors.series/provider if a live gauge is chosen.
}
FLAT_BAND = {"rate": 0.10, "level": 1.0, "slow": 0.2}   # rate: points; level/slow: percent
UNITS = {"rate": "pp", "level": "%", "slow": "%"}

_fetched_on: dict[str, date] = {}
_lock = threading.Lock()


def fetch_fred(series: str, start: date) -> list[tuple[str, float]]:
    resp = requests.get(FRED_CSV, params={"id": series, "cosd": start.isoformat()}, timeout=20)
    resp.raise_for_status()
    rows = []
    for r in csv.reader(io.StringIO(resp.text)):
        if len(r) < 2 or r[0] in ("observation_date", "DATE"):
            continue
        try:
            rows.append((r[0], float(r[1])))
        except ValueError:      # "." marks a missing observation
            continue
    return rows


def _kind(code: str, series: str | None) -> str:
    if code in DEFAULTS:
        return DEFAULTS[code][2]
    return "level"


def moves(obs: list[tuple[str, float]], kind: str) -> list[dict]:
    """Attach change vs ~1 month earlier and an up/down/flat move to each observation."""
    out, j = [], 0
    for i, (d, v) in enumerate(obs):
        cutoff = (date.fromisoformat(d) - WINDOW).isoformat()
        while j + 1 < i and obs[j + 1][0] <= cutoff:
            j += 1
        if i == 0 or obs[j][0] > cutoff:
            continue                       # not a month of history yet
        prev = obs[j][1]
        change = v - prev if kind == "rate" else ((v / prev - 1) * 100 if prev else 0.0)
        band = FLAT_BAND[kind]
        out.append({"as_of": d, "value": v, "change": round(change, 4),
                    "move": "flat" if abs(change) < band else ("up" if change > 0 else "down")})
    return out


def factor_sources(db: Client) -> list[dict]:
    rows = db.table("macro_factors").select("code, name, series, provider").execute().data
    out = []
    for r in rows:
        provider, series, kind = DEFAULTS.get(r["code"], (None, None, "level"))
        if r.get("series"):
            provider, series, kind = (r.get("provider") or "FRED"), r["series"], _kind(r["code"], r["series"])
        out.append({"code": r["code"], "name": r["name"], "provider": provider, "series": series, "kind": kind})
    return out


def refresh_macro(db: Client, fetch=fetch_fred, today: date | None = None) -> dict:
    """Fetch every factor with a known FRED series, at most once per process per day."""
    today = today or date.today()
    summary = {"updated": [], "skipped": [], "failed": [], "no_source": []}
    for f in factor_sources(db):
        code = f["code"]
        if f["provider"] != "FRED" or not f["series"]:
            summary["no_source"].append(code)
            continue
        with _lock:
            if _fetched_on.get(code) == today:
                summary["skipped"].append(code)
                continue
        try:
            rows = moves(fetch(f["series"], today - HISTORY), f["kind"])
        except Exception as e:  # network / bad series: report, keep going
            summary["failed"].append(f"{code}: {type(e).__name__}")
            continue
        if rows:
            db.table("macro_factor_moves").upsert(
                [{"factor_code": code, **r} for r in rows[-UPSERT_TAIL:]] if _has_history(db, code) else [{"factor_code": code, **r} for r in rows],
                on_conflict="factor_code,as_of",
            ).execute()
        with _lock:
            _fetched_on[code] = today
        summary["updated"].append(code)
    return summary


def _has_history(db: Client, code: str) -> bool:
    return bool(db.table("macro_factor_moves").select("as_of").eq("factor_code", code).limit(1).execute().data)
