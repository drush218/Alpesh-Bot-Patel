"""Analyses screen: one row per current analysis, compared side by side (held vs watch).

Watch = analysed but not held. Scores are the user's latest scorecard only — blank when
they haven't scored it (Claude's suggestion is never shown here).
"""

from datetime import date

from supabase import Client

from app.crypto import get_t212_credentials
from app.services import actuals, t212_client
from app.services.analysis_view import latest_moves, macro_summary, score_links, staleness
from app.services.market_data import parse_t212_ticker
from app.services.scorecard import DIMENSIONS


def _holdings(db: Client, user_id: str) -> dict[str, dict] | None:
    """{ticker: {weight_pct, ppl_pct}} for every holding, or None when Trading212 isn't reachable."""
    api_key, secret = get_t212_credentials(db, user_id)
    if not api_key:
        return None
    try:
        positions = t212_client.get_positions(api_key, secret or "")
        cash = t212_client.get_cash(api_key, secret or "")
    except t212_client.T212Error:
        return None
    derived = [t212_client.derive_position_gbp(p) for p in positions]
    book = sum(d["value_gbp"] for d in derived) + float(cash.get("free", 0))
    return {parse_t212_ticker(d["ticker"])[0]: {
        "weight_pct": d["value_gbp"] / book * 100 if book else None,
        "ppl_pct": d["ppl_pct"],
    } for d in derived}


def _latest_scores(db: Client, user_id: str) -> dict[int, dict]:
    rows = db.table("scorecards").select("instrument_id, created_at, id, " + ", ".join(DIMENSIONS)).eq("user_id", user_id).execute().data
    latest: dict[int, dict] = {}
    for r in sorted(rows, key=lambda r: (r.get("created_at") or "", r["id"])):
        latest[r["instrument_id"]] = {d: r.get(d) for d in DIMENSIONS}
    return latest


def _eps_cagr(bau: list[dict]) -> float | None:
    if len(bau) < 2 or bau[0]["eps"] <= 0 or bau[-1]["eps"] <= 0:
        return None
    return ((bau[-1]["eps"] / bau[0]["eps"]) ** (1 / (len(bau) - 1)) - 1) * 100


def analyses_list(db: Client, user_id: str) -> dict:
    today = date.today().isoformat()
    analyses = (db.table("analyses")
                .select("instrument_id, model, data_as_of, reporting_currency, instruments(ticker, company)")
                .eq("is_current", True).execute().data)
    ids = [a["instrument_id"] for a in analyses]
    prices = {p["instrument_id"]: p for p in
              db.table("latest_prices").select("instrument_id, close, currency").in_("instrument_id", ids).execute().data} if ids else {}
    scores = _latest_scores(db, user_id)
    holdings = _holdings(db, user_id)

    moves = latest_moves(db, {m["factor"] for a in analyses for m in a["model"].get("macro", [])})
    fx_cache: dict[tuple[str, str], float | None] = {}

    def fx(src: str | None, dst: str) -> float | None:
        if not src or src == dst:
            return 1.0
        if (src, dst) not in fx_cache:
            v = db.rpc("fx_rate", {"from_ccy": src, "to_ccy": dst}).execute().data
            fx_cache[(src, dst)] = float(v) if v is not None else None
        return fx_cache[(src, dst)]

    rows = []
    for a in analyses:
        ticker = a["instruments"]["ticker"]
        model = a["model"]
        meta = model.get("meta", {})
        bau = (model.get("outputs") or {}).get("scenarios", {}).get("bau", [])
        p = prices.get(a["instrument_id"])
        pe = None
        if p and bau and bau[0]["eps"] > 0:
            rate = fx(a.get("reporting_currency"), p["currency"])
            pe = float(p["close"]) / (bau[0]["eps"] * rate) if rate else None
        act = actuals.compute(model)
        pe_actual = None
        if p and act["eps"] and act["eps"] > 0:
            rate = fx(a.get("reporting_currency"), p["currency"])
            pe_actual = float(p["close"]) / (act["eps"] * rate) if rate else None
        held = holdings.get(ticker) if holdings else None
        rows.append({
            "ticker": ticker,
            "company": meta.get("company") or a["instruments"].get("company") or ticker,
            "held": held is not None,
            "weight_pct": held["weight_pct"] if held else None,
            "ppl_pct": held["ppl_pct"] if held else None,
            "price": float(p["close"]) if p else None,
            "price_currency": p["currency"] if p else None,
            "pe": pe,
            "pe_year": bau[0]["year"] if bau else None,
            "pe_actual": pe_actual,
            "pe_actual_year": act["year"],
            "eps_cagr": _eps_cagr(bau),
            "eps_cagr_years": f"{bau[0]['year']}–{bau[-1]['year']}" if len(bau) > 1 else None,
            "scores": scores.get(a["instrument_id"]),
            "macro": macro_summary(score_links(model.get("macro", []), moves)),
            "stale": staleness(model, a["data_as_of"], today)["is_stale"],
            "data_as_of": a["data_as_of"],
        })
    rows.sort(key=lambda r: r["ticker"])

    modelled = {r["ticker"] for r in rows}
    return {
        "rows": rows,
        "holdings_available": holdings is not None,
        "not_modelled": sorted(t for t in (holdings or {}) if t not in modelled),
    }
