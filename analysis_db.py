"""
analysis_db.py
Supabase writes for the v2 analysis ingestion flow
(claude-code-handoff/handoff/CLAUDE_CODE_PROMPT_model_v2.md; schema in supabase/migrations/).

Only v2 payloads (```json stock-model block) are stored. Legacy v1 files still parse for preview
but are rejected here; re-run them through the stock-analysis skill instead.

insert_analysis() stages the new analysis as is_current=false and inserts all child
rows; only once every child insert succeeds does promote_analysis() flip is_current
old->new. If any child insert fails, the staged row is deleted (children cascade) and
the previously-current analysis is left untouched — postgrest has no multi-statement
transaction here, so this stage/promote split is what keeps a failed ingest from ever
leaving a ticker without a valid current analysis.

User-owned data (scorecards, user_scenarios) is keyed on instrument, never on analysis, and
ingest never writes to it, so re-ingesting leaves it untouched. The suggested scorecard lives
in analyses.model and so moves with each new analysis.
"""

import re


def init_supabase():
    """Streamlit's client. The webapp backend passes its own user client to confirm_ingest instead."""
    from auth import init_supabase as _streamlit_client
    return _streamlit_client()

LEVER_COLUMNS = ("base", "lever_name", "exposure", "exposure_pct", "speed", "direction",
                 "macro_factor_code", "channel_group", "watch_metric", "current_reading",
                 "pushes_low", "pushes_high")


def _non_null(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


def upsert_instrument(ticker: str, company: str | None, exchange: str | None, currency: str | None, supabase=None) -> int:
    """Create or update the instrument by ticker. Returns its id."""
    supabase = supabase or init_supabase()
    row = _non_null({
        "ticker": ticker,
        "company": company,
        "exchange": exchange,
        "currency": currency,
    })
    resp = supabase.table("instruments").upsert(row, on_conflict="ticker").execute()
    return resp.data[0]["id"]


def find_existing_analysis(instrument_id: int, content_hash: str, supabase=None) -> int | None:
    supabase = supabase or init_supabase()
    resp = (
        supabase.table("analyses")
        .select("id")
        .eq("instrument_id", instrument_id)
        .eq("content_hash", content_hash)
        .execute()
    )
    return resp.data[0]["id"] if resp.data else None


def insert_analysis(payload: dict, instrument_id: int, supabase=None) -> int:
    """Stage the analysis (is_current=false) and all child rows. Returns the new analysis id."""
    supabase = supabase or init_supabase()
    header = payload["analysis"]

    analysis_row = {
        "instrument_id": instrument_id,
        "schema_version": payload["schema_version"],
        "model": payload["model"],
        "reporting_currency": header.get("data_currency"),
        "price_currency": header.get("price_currency"),
        "data_as_of": header.get("data_as_of"),
        "content_hash": payload["content_hash"],
        "raw_markdown": payload["raw_markdown"],
        "narrative": payload.get("narrative") or {},
        "warnings": payload.get("warnings") or [],
        "is_current": False,
    }

    resp = supabase.table("analyses").insert(analysis_row).execute()
    analysis_id = resp.data[0]["id"]

    try:
        _insert_children(supabase, analysis_id, payload)
    except Exception:
        supabase.table("analyses").delete().eq("id", analysis_id).execute()
        raise

    return analysis_id


def _insert_children(supabase, analysis_id: int, payload: dict) -> None:
    def insert(table, rows):
        if rows:
            supabase.table(table).insert([{**r, "analysis_id": analysis_id} for r in rows]).execute()

    insert("analysis_forecast", payload["forecast"])
    insert("analysis_segment_forecast", payload["segment_forecast"])
    insert("analysis_calendar", payload["calendar"])
    insert("analysis_macro", payload["macro"])
    insert("analysis_backtest_requests", payload["backtest_requests"])
    insert("analysis_levers", [{k: l.get(k) for k in LEVER_COLUMNS} for l in payload["levers"]])


def promote_analysis(analysis_id: int, instrument_id: int, supabase=None) -> None:
    supabase = supabase or init_supabase()
    supabase.table("analyses").update({"is_current": False}).eq("instrument_id", instrument_id).eq("is_current", True).execute()
    supabase.table("analyses").update({"is_current": True}).eq("id", analysis_id).execute()


def record_factor_codes(payload: dict, analysis_id: int, ticker: str, supabase=None) -> None:
    """
    Proposed factors: insert new codes as pending; for known proposals, append the ticker.
    commodity_* codes are on the parser's fixed list by pattern, so they go straight into
    macro_factors rather than waiting for approval.
    """
    supabase = supabase or init_supabase()
    approved = {r["code"] for r in supabase.table("macro_factors").select("code").execute().data}

    used = {x["factor_code"] for x in payload["macro"]}
    used |= {l["macro_factor_code"] for l in payload["levers"] if l.get("macro_factor_code")}
    for code in sorted(used - approved):
        if re.fullmatch(r"commodity_[a-z0-9_]+", code):
            supabase.table("macro_factors").insert({"code": code, "name": code}).execute()
            approved.add(code)

    for f in payload.get("proposed_factors") or []:
        code = f["code"]
        if code in approved:
            continue
        resp = supabase.table("macro_factor_proposals").select("proposed_by_tickers").eq("code", code).execute()
        if resp.data:
            tickers = resp.data[0]["proposed_by_tickers"] or []
            if ticker not in tickers:
                supabase.table("macro_factor_proposals").update(
                    {"proposed_by_tickers": tickers + [ticker]}
                ).eq("code", code).execute()
        else:
            supabase.table("macro_factor_proposals").insert(_non_null({
                "code": code,
                "name": f.get("name"),
                "series": f.get("series"),
                "provider": f.get("provider"),
                "scope": f.get("scope"),
                "rationale": f.get("rationale"),
                "first_proposed_by": analysis_id,
                "proposed_by_tickers": [ticker],
            })).execute()


def confirm_ingest(payload: dict, supabase=None) -> tuple[int, bool]:
    """
    Write payload to Supabase. Returns (analysis_id, already_existed).
    Dedupes on (instrument, content_hash).
    """
    if payload.get("schema_version") != 2:
        raise ValueError("Only v2 analyses (```json stock-model block) are stored. "
                         "Re-run this file through the stock-analysis skill.")

    header = payload["analysis"]
    ticker = header["ticker"]
    if not ticker:
        raise ValueError("Cannot ingest: no ticker in meta.ticker.")

    db = supabase or init_supabase()
    instrument_id = upsert_instrument(ticker, header.get("company"), header.get("exchange"), header.get("price_currency"), supabase=db)
    existing_id = find_existing_analysis(instrument_id, payload["content_hash"], supabase=db)
    if existing_id:
        return existing_id, True

    analysis_id = insert_analysis(payload, instrument_id, supabase=db)
    promote_analysis(analysis_id, instrument_id, supabase=db)
    record_factor_codes(payload, analysis_id, ticker, supabase=db)
    return analysis_id, False
