"""Macro screen: factor cards, per-holding factor effects, verdict bands and book tilt.

Effects come from each holding's current analysis (analysis_macro), crossed with the factor's
latest 1-month move: a bear link on a factor that's rising is a headwind; on a falling factor it
flips to a tailwind (as v_macro_cross). Holdings without an analysis have no effects; there is
no sector prior yet, so they're listed as unscored rather than guessed.

Score per link = sign(direction) x strength (negligible 0, mild 1, medium 2, strong 3) x move
(+1 up, -1 down, 0 flat). Combined = sum over links. Bands as the design handoff: <= -3 strong
headwind, <= -1 headwind, < 1 neutral, < 3 tailwind, else strong tailwind.
"""

from supabase import Client

from app.crypto import get_t212_credentials
from app.services import t212_client
from app.services.macro_data import UNITS, factor_sources
from app.services.market_data import parse_t212_ticker

STRENGTH = {"negligible": 0, "mild": 1, "medium": 2, "strong": 3}
DIRECTION = {"bull": 1, "bear": -1, "neutral": 0}
MOVE = {"up": 1, "down": -1, "flat": 0}
SPARK_POINTS = 120


def verdict(score: float) -> str:
    if score <= -3:
        return "strong headwind"
    if score <= -1:
        return "headwind"
    if score < 1:
        return "neutral"
    if score < 3:
        return "tailwind"
    return "strong tailwind"


def link_score(direction: str, strength: str, move: str | None) -> int:
    return DIRECTION.get(direction, 0) * STRENGTH.get(strength, 0) * MOVE.get(move or "flat", 0)


def _state(rows: list[dict]) -> str:
    """'Accelerating up' etc. from the last two monthly changes."""
    if len(rows) < 2:
        return "No data yet"
    last = rows[-1]
    before = next((r for r in reversed(rows[:-1]) if r["as_of"] <= _month_back(last["as_of"])), rows[0])
    if last["move"] == "flat":
        return "Flat"
    word = "up" if last["move"] == "up" else "down"
    faster = abs(last["change"]) > abs(before["change"]) and (last["change"] > 0) == (before["change"] > 0)
    return f"{'Accelerating' if faster else 'Moving'} {word}"


def _month_back(d: str) -> str:
    y, m, day = (int(x) for x in d.split("-"))
    m -= 1
    if m == 0:
        y, m = y - 1, 12
    return f"{y:04d}-{m:02d}-{min(day, 28):02d}"


def _holdings(db: Client, user_id: str) -> tuple[list[dict], list[str]]:
    api_key, secret = get_t212_credentials(db, user_id)
    if not api_key:
        return [], ["No Trading212 credentials, so weights are unknown."]
    try:
        positions = t212_client.get_positions(api_key, secret or "")
        cash = t212_client.get_cash(api_key, secret or "")
    except t212_client.T212Error as e:
        return [], [f"Trading212 unavailable: {e}"]
    derived = [t212_client.derive_position_gbp(p) for p in positions]
    book = sum(d["value_gbp"] for d in derived) + float(cash.get("free", 0))
    return [{"ticker": parse_t212_ticker(d["ticker"])[0], "weight_pct": d["value_gbp"] / book * 100 if book else 0} for d in derived], []


def macro_view(db: Client, user_id: str) -> dict:
    sources = {f["code"]: f for f in factor_sources(db)}
    # Per factor with a limit: one query for every row would hit PostgREST's 1,000-row cap.
    by_factor: dict[str, list[dict]] = {}
    for code in sources:
        recent = (db.table("macro_factor_moves").select("factor_code, as_of, value, change, move")
                  .eq("factor_code", code).order("as_of", desc=True).limit(SPARK_POINTS + 40).execute().data)
        by_factor[code] = sorted(recent, key=lambda r: r["as_of"])

    current = {a["id"]: a["instruments"] for a in db.table("analyses").select("id, instruments(ticker, company)").eq("is_current", True).execute().data}
    links = [{**m, "instrument": current[m["analysis_id"]]}
             for m in db.table("analysis_macro").select("analysis_id, factor_code, channel, direction, strength, speed, ref").execute().data
             if m["analysis_id"] in current]
    holdings, warnings = _holdings(db, user_id)
    weights = {h["ticker"]: h["weight_pct"] for h in holdings}

    per_ticker: dict[str, dict] = {}
    for link in links:
        if link["factor_code"] not in sources:      # pending / rejected proposal: excluded from the cross
            continue
        inst = link["instrument"]
        latest = (by_factor.get(link["factor_code"]) or [None])[-1]
        move = latest["move"] if latest else None
        t = per_ticker.setdefault(inst["ticker"], {"ticker": inst["ticker"], "company": inst.get("company"), "links": []})
        t["links"].append({
            "factor": link["factor_code"], "channel": link["channel"], "direction": link["direction"],
            "strength": link["strength"], "speed": link.get("speed"), "ref": link.get("ref"),
            "move": move, "score": link_score(link["direction"], link["strength"], move),
        })

    rows = []
    tickers = sorted(set(weights) | set(per_ticker))
    for tk in tickers:
        t = per_ticker.get(tk)
        if t:
            combined = sum(l["score"] for l in t["links"])
            by_f: dict[str, int] = {}
            for l in t["links"]:
                by_f[l["factor"]] = by_f.get(l["factor"], 0) + l["score"]
            rows.append({**t, "weight_pct": weights.get(tk), "modelled": True, "score": combined,
                         "verdict": verdict(combined), "factor_scores": by_f})
        else:
            rows.append({"ticker": tk, "company": None, "weight_pct": weights.get(tk), "modelled": False,
                         "links": [], "score": None, "verdict": None, "factor_scores": {}})
    rows.sort(key=lambda r: (r["score"] is None, r["score"] if r["score"] is not None else 0, -(r["weight_pct"] or 0)))

    used = sorted({l["factor"] for t in per_ticker.values() for l in t["links"]})
    factors = []
    for code, f in sources.items():
        series = by_factor.get(code, [])
        latest = series[-1] if series else None
        factors.append({
            "code": code, "name": f["name"], "series": f["series"], "provider": f["provider"],
            "unit": UNITS.get(f["kind"], "%"),
            "value": latest["value"] if latest else None, "as_of": latest["as_of"] if latest else None,
            "change": latest["change"] if latest else None, "move": latest["move"] if latest else None,
            "state": _state(series),
            "spark": [r["value"] for r in series[-SPARK_POINTS:]],
            "affected": sum(1 for t in per_ticker.values() if any(l["factor"] == code for l in t["links"])),
            "used": code in used,
        })
    factors.sort(key=lambda f: (not f["used"], f["code"]))

    scored = [r for r in rows if r["modelled"] and r["weight_pct"]]
    wsum = sum(r["weight_pct"] for r in scored)
    tilt = sum(r["score"] * r["weight_pct"] for r in scored) / wsum if wsum else None
    return {
        "factors": factors,
        "matrix_factors": used,
        "holdings": rows,
        "tilt": {"score": tilt, "verdict": verdict(tilt) if tilt is not None else None,
                 "modelled": len([r for r in rows if r["modelled"]]), "total": len(rows)},
        "warnings": warnings,
    }
