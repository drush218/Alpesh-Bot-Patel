"""User scorecards (CLAUDE_CODE_PROMPT_model_v2.md section 6).

Append-only: every save writes a new row and the latest is current, so history is kept.
The user's card is never prefilled; Claude's scorecard_suggested from the current analysis
is returned alongside it for reference only.
"""

from supabase import Client

from app.services.workspace import current_analysis

DIMENSIONS = ("growth", "value", "income", "macro")
# User cards score 0–3; analyses still suggest 1–5, so suggestions are mapped for display.
SUGGESTED_TO_CARD = {1: 0, 2: 1, 3: 2, 4: 3, 5: 3}
STATUSES = ("open", "hit", "missed")


def _history(db: Client, user_id: str, instrument_id: int) -> list[dict]:
    rows = (db.table("scorecards").select("*")
            .eq("user_id", user_id).eq("instrument_id", instrument_id).execute().data)
    return sorted(rows, key=lambda r: (r.get("created_at") or "", r["id"]))


def _card(row: dict) -> dict:
    return {
        "id": row["id"],
        **{d: row.get(d) for d in DIMENSIONS},
        "bull_catalysts": row.get("bull_catalysts") or [],
        "bear_catalysts": row.get("bear_catalysts") or [],
        "note": row.get("note"),
        "target_pe": float(row["target_pe"]) if row.get("target_pe") is not None else None,
        "target_pe_note": row.get("target_pe_note"),
        "created_at": row.get("created_at"),
    }


def _rescaled(dim: dict | None) -> dict | None:
    if not dim:
        return None
    raw = dim.get("score")
    return {**dim, "score": SUGGESTED_TO_CARD.get(raw), "score_1_5": raw}


def _suggested(inputs: dict) -> dict | None:
    s = inputs.get("scorecard_suggested")
    if not s:
        return None
    return {
        "as_of": inputs.get("meta", {}).get("data_as_of"),
        **{d: _rescaled(s.get(d)) for d in DIMENSIONS},   # {"score" (0–3), "score_1_5", "ref"}
        "bull_catalysts": s.get("bull_catalysts") or [],
        "bear_catalysts": s.get("bear_catalysts") or [],
    }


def get_scorecard(db: Client, user_id: str, ticker: str) -> dict:
    base = current_analysis(db, ticker)
    history = _history(db, user_id, base["instrument_id"])
    return {
        "current": _card(history[-1]) if history else None,
        "versions": len(history),
        "suggested": _suggested(base["inputs"]),
    }


def save_scorecard(db: Client, user_id: str, ticker: str, card: dict) -> dict:
    """Write a new version. card: growth/value/income/macro (0-3), bull/bear_catalysts, note."""
    base = current_analysis(db, ticker)
    db.table("scorecards").insert({
        "user_id": user_id,
        "instrument_id": base["instrument_id"],
        **{d: card[d] for d in DIMENSIONS},
        "bull_catalysts": card.get("bull_catalysts", []),
        "bear_catalysts": card.get("bear_catalysts", []),
        "note": card.get("note"),
        "target_pe": card.get("target_pe"),
        "target_pe_note": card.get("target_pe_note"),
    }).execute()
    return get_scorecard(db, user_id, ticker)
