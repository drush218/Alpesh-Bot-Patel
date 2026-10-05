"""Analysis upload for the webapp: parse a stock-analysis markdown file, preview it, store it.

The parser (markdown_to_json.py) and the write path (analysis_db.py) live at the repo root
because the Streamlit app shares them; they're imported from there rather than duplicated.
"""

import sys
from pathlib import Path

from supabase import Client

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import analysis_db  # noqa: E402
from markdown_to_json import AnalysisValidationError, parse_analysis  # noqa: E402


class IngestError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def _parse(markdown: str, filename: str | None) -> dict:
    try:
        payload = parse_analysis(markdown, filename)
    except AnalysisValidationError as e:
        raise IngestError(e.errors)
    if payload.get("schema_version") != 2:
        raise IngestError(["No ```json stock-model block found. Only stock-analysis v2 output can be stored; "
                           "an older v1 analysis needs re-running through the skill."])
    if not payload["analysis"].get("ticker"):
        raise IngestError(["No ticker in meta.ticker."])
    return payload


def preview(db: Client, markdown: str, filename: str | None) -> dict:
    """What would be stored, and how it relates to what's already there. Writes nothing."""
    try:
        payload = _parse(markdown, filename)
    except IngestError as e:
        return {"ok": False, "filename": filename, "errors": e.errors}

    head, model = payload["analysis"], payload["model"]
    ticker = head["ticker"].upper()
    status, current_as_of = "new", None
    inst = db.table("instruments").select("id").eq("ticker", ticker).execute().data
    if inst:
        rows = db.table("analyses").select("id, content_hash, data_as_of, is_current").eq("instrument_id", inst[0]["id"]).execute().data
        if any(r["content_hash"] == payload["content_hash"] for r in rows):
            status = "duplicate"
        else:
            cur = [r for r in rows if r["is_current"]]
            if cur:
                status, current_as_of = "replaces", cur[0]["data_as_of"]

    bau = [r for r in payload["forecast"] if r["scenario"] == "bau"]
    return {
        "ok": True,
        "filename": filename,
        "ticker": ticker,
        "company": head.get("company"),
        "exchange": head.get("exchange"),
        "data_as_of": head.get("data_as_of"),
        "status": status,                  # new | replaces | duplicate
        "replaces_as_of": current_as_of,
        "bau_eps": [{"year": r["fiscal_year"], "eps": r["eps"]} for r in bau],
        "currency": head.get("data_currency"),
        "macro_count": len(payload["macro"]),
        "lever_count": len(payload["levers"]),
        "event_count": len(payload["calendar"]),
        "proposed_factors": [f["code"] for f in payload.get("proposed_factors") or []],
        "warnings": payload["warnings"],
        "errors": [],
        "bottom_line": model.get("bottom_line"),
    }


def store(db: Client, markdown: str, filename: str | None) -> dict:
    payload = _parse(markdown, filename)
    analysis_id, existed = analysis_db.confirm_ingest(payload, supabase=db)
    return {"analysis_id": analysis_id, "already_existed": existed, "ticker": payload["analysis"]["ticker"].upper()}
