"""Everything the Analysis screen shows around the workspace: status, position, what changed, calendar.

The v2 model is the source; there's no thesis prose, risks or peers in it, so the screen
shows the bottom line as the thesis and leaves those panels out.
"""

from datetime import date

from supabase import Client

from app.crypto import get_t212_credentials
from app.services import t212_client
from app.services.macro_data import factor_sources
from app.services.macro_view import MOVE, verdict
from app.services.market_data import parse_t212_ticker
from app.services.workspace import NotFound, latest_price


def staleness(model: dict, data_as_of: str | None, today: str | None = None) -> dict:
    """Stale once an earnings date in the analysis's own calendar falls after its data date and has passed.

    Compared with data_as_of, not the upload date: a file struck on July data but uploaded in
    October is still stale if the company reported in August.
    """
    today = today or date.today().isoformat()
    since = data_as_of or "0000-00-00"
    passed = [e["date"] for e in model.get("calendar", []) if e.get("type") == "earnings" and since < e.get("date", "") < today]
    return {"is_stale": bool(passed), "last_earnings": max(passed) if passed else None}


# A link's direction is a sensitivity: bull = the stock gains when the factor RISES. Whether it's a
# tailwind or headwind today depends on the factor's latest 1-month move, as on the Macro screen.
# Five labels: strong/mild headwind, neutral, mild/strong tailwind. "medium" counts as strong: the
# skill only uses it for a deliberate step up from mild.
LINK_WEIGHT = {"negligible": 0, "mild": 1, "medium": 2, "strong": 2}
LINK_SIGN = {"bull": 1, "bear": -1, "neutral": 0}


def link_weight(link: dict) -> int:
    """-2..+2 sensitivity to the factor rising."""
    return LINK_SIGN.get(link.get("direction"), 0) * LINK_WEIGHT.get(link.get("strength"), 0)


def latest_moves(db: Client, codes: set[str]) -> dict[str, str | None]:
    """Latest 1-month move (up/down/flat) per approved factor; pending factors and ones without data map to None."""
    approved = {f["code"] for f in factor_sources(db)}
    moves: dict[str, str | None] = {}
    for code in codes:
        rows = (db.table("macro_factor_moves").select("move").eq("factor_code", code)
                .order("as_of", desc=True).limit(1).execute().data) if code in approved else []
        moves[code] = rows[0]["move"] if rows else None
    return moves


def score_links(links: list[dict], moves: dict[str, str | None]) -> list[dict]:
    out = []
    for m in links:
        move = moves.get(m.get("factor"))
        sens = link_weight(m)
        out.append({**m, "sensitivity": sens, "move": move, "effect": sens * MOVE[move] if move else None})
    return out


def macro_summary(scored: list[dict]) -> dict:
    """Today's tailwinds and headwinds added up; net banded like the Macro screen (|net| >= 3 strong, >= 1 mild)."""
    effects = [m["effect"] for m in scored if m["effect"] is not None]
    tail = [e for e in effects if e > 0]
    head = [e for e in effects if e < 0]
    net = sum(effects)
    return {
        "tailwind": sum(tail), "tailwind_links": len(tail),
        "headwind": sum(head), "headwind_links": len(head),
        "neutral_links": len(effects) - len(tail) - len(head),
        "no_data_links": len(scored) - len(effects),
        "net": net, "verdict": verdict(net),
    }


def _bau_by_year(model: dict) -> dict:
    return {r["year"]: r for r in (model.get("outputs") or {}).get("scenarios", {}).get("bau", [])}


def _what_changed(model: dict, prev: dict | None) -> dict | None:
    """BAU revenue / EPS per year against the previous analysis of the same instrument."""
    if not prev:
        return None
    cur, old = _bau_by_year(model), _bau_by_year(prev["model"])
    years = [y for y in cur if y in old]
    rows = [{
        "year": y,
        "eps_was": old[y]["eps"], "eps_now": cur[y]["eps"],
        "revenue_was": old[y]["revenue"], "revenue_now": cur[y]["revenue"],
    } for y in years]
    return {
        "previous_as_of": prev.get("data_as_of"),
        "rows": rows,
        "new_years": [y for y in cur if y not in old],
        "dropped_years": [y for y in old if y not in cur],
        "bottom_line_was": prev["model"].get("bottom_line"),
    }


def _position(db: Client, user_id: str, ticker: str) -> dict | None:
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
    for d in derived:
        if parse_t212_ticker(d["ticker"])[0] == ticker:
            return {
                "quantity": d["quantity"], "avg_price": d["avg_price"], "price": d["curr_price"],
                "value_gbp": d["value_gbp"], "ppl_gbp": d["ppl_gbp"], "ppl_pct": d["ppl_pct"],
                "weight_pct": d["value_gbp"] / book * 100 if book else None,
            }
    return None


def analysis_view(db: Client, user_id: str, ticker: str) -> dict:
    ticker = ticker.upper()
    inst = db.table("instruments").select("id, company, exchange").eq("ticker", ticker).execute().data
    if not inst:
        raise NotFound(f"No instrument {ticker}")
    iid = inst[0]["id"]
    rows = db.table("analyses").select("id, model, data_as_of, created_at, warnings, is_current, reporting_currency").eq("instrument_id", iid).execute().data
    current = next((r for r in rows if r["is_current"]), None)
    if not current:
        raise NotFound(f"No current analysis for {ticker}")
    older = sorted((r for r in rows if not r["is_current"] and (r["created_at"] or "") < (current["created_at"] or "")),
                   key=lambda r: r["created_at"] or "")
    model = current["model"]

    today = date.today().isoformat()
    calendar = sorted((e for e in model.get("calendar", []) if e.get("date", "") >= today), key=lambda e: e["date"])

    names = {r["code"]: r["name"] for r in db.table("macro_factors").select("code, name").execute().data}
    for r in db.table("macro_factor_proposals").select("code, name, status").execute().data:
        names.setdefault(r["code"], f"{r['name'] or r['code']}{' (pending)' if r['status'] == 'pending' else ''}")

    links = model.get("macro", [])
    scored = score_links(links, latest_moves(db, {m["factor"] for m in links}))

    return {
        "ticker": ticker,
        "factor_names": names,
        "analysis_id": current["id"],
        "ingested_at": current["created_at"],
        "data_as_of": current["data_as_of"],
        "meta": model.get("meta", {}),
        "bottom_line": model.get("bottom_line"),
        "macro": scored,
        "macro_summary": macro_summary(scored),
        "levers": model.get("levers", []),
        "calendar": calendar,
        "warnings": current.get("warnings") or [],
        "stale": staleness(model, current["data_as_of"], today),
        "price": latest_price(db, iid, current.get("reporting_currency")),
        "position": _position(db, user_id, ticker),
        "what_changed": _what_changed(model, older[-1] if older else None),
    }
