"""
analysis_db.py
Supabase writes for the analysis ingestion flow (HandoverFiles/HANDOFF_claude_code.md section 4).

insert_analysis() stages the new analysis as is_current=false and inserts all child
rows; only once every child insert succeeds does promote_analysis() flip is_current
old->new. If any child insert fails, the staged row is deleted (children cascade) and
the previously-current analysis is left untouched — postgrest has no multi-statement
transaction here, so this stage/promote split is what keeps a failed ingest from ever
leaving a ticker without a valid current analysis.
"""

from datetime import date

from auth import init_supabase


def _non_null(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


def upsert_instrument(ticker: str, company: str | None, exchange: str | None, currency: str | None) -> None:
    supabase = init_supabase()
    row = _non_null({
        "ticker": ticker,
        "company": company,
        "exchange": exchange,
        "currency": currency,
    })
    supabase.table("instruments").upsert(row, on_conflict="ticker").execute()


def find_existing_analysis(ticker: str, content_hash: str) -> str | None:
    supabase = init_supabase()
    resp = (
        supabase.table("analyses")
        .select("id")
        .eq("ticker", ticker)
        .eq("content_hash", content_hash)
        .execute()
    )
    return resp.data[0]["id"] if resp.data else None


def insert_analysis(payload: dict) -> str:
    """Stage the analysis (is_current=false) and all child rows. Returns the new analysis id."""
    supabase = init_supabase()
    header = payload["analysis"]
    ticker = header["ticker"]

    analysis_row = {
        "ticker": ticker,
        "analysis_date": header.get("price_date") or date.today().isoformat(),
        "price_at_analysis": header.get("price"),
        "price_currency": header.get("price_currency"),
        "data_currency": header.get("data_currency"),
        "calibration_note": header.get("calibration_note"),
        "schema_version": payload.get("schema_version", 1),
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


def _insert_children(supabase, analysis_id: str, payload: dict) -> None:
    if payload["pe_basis"]:
        supabase.table("analysis_pe_basis").insert(
            [{**r, "analysis_id": analysis_id} for r in payload["pe_basis"]]
        ).execute()

    if payload["bridge"]:
        supabase.table("analysis_bridge").insert([
            {
                "analysis_id": analysis_id,
                "scenario": "BAU",
                "fiscal_year": r["fiscal_year"],
                "is_actual": r["is_actual"],
                "line_key": r["line_key"],
                "line_label": r["line_label"],
                "value": r["value"],
                "unit": r["unit"],
                "raw": r["raw"],
            }
            for r in payload["bridge"]
        ]).execute()

    if payload["scenario_outcomes"]:
        supabase.table("analysis_scenario_outcomes").insert([
            {
                "analysis_id": analysis_id,
                "scenario": r["scenario"],
                "fiscal_year": r["fiscal_year"],
                "metric": r["metric"],
                "value": r["value"],
            }
            for r in payload["scenario_outcomes"]
        ]).execute()

    if payload["scenario_drivers"]:
        supabase.table("analysis_scenario_drivers").insert(
            [{**r, "analysis_id": analysis_id} for r in payload["scenario_drivers"]]
        ).execute()

    if payload["scenario_assumptions"]:
        supabase.table("analysis_scenario_assumptions").insert(
            [{**r, "analysis_id": analysis_id} for r in payload["scenario_assumptions"]]
        ).execute()

    if payload["forward_pe"]:
        supabase.table("analysis_forward_pe").insert([
            {
                "analysis_id": analysis_id,
                "scenario": r["scenario"],
                "fiscal_year": r["fiscal_year"],
                "pe": r["pe"],
            }
            for r in payload["forward_pe"]
        ]).execute()

    if payload["sensitivities"]:
        supabase.table("analysis_sensitivities").insert(
            [{**r, "analysis_id": analysis_id} for r in payload["sensitivities"]]
        ).execute()

    if payload["risks"]:
        supabase.table("analysis_risks").insert(
            [{**r, "analysis_id": analysis_id} for r in payload["risks"]]
        ).execute()

    if payload["peers"]:
        supabase.table("analysis_peers").insert(
            [{**r, "analysis_id": analysis_id} for r in payload["peers"]]
        ).execute()


def promote_analysis(analysis_id: str, ticker: str) -> None:
    supabase = init_supabase()
    supabase.table("analyses").update({"is_current": False}).eq("ticker", ticker).eq("is_current", True).execute()
    supabase.table("analyses").update({"is_current": True}).eq("id", analysis_id).execute()


def confirm_ingest(payload: dict) -> tuple[str, bool]:
    """
    Write payload to Supabase. Returns (analysis_id, already_existed).
    Dedupes on (ticker, content_hash) per HANDOFF section 4.
    """
    header = payload["analysis"]
    ticker = header["ticker"]
    if not ticker:
        raise ValueError("Cannot ingest: no ticker parsed from the markdown header.")

    existing_id = find_existing_analysis(ticker, payload["content_hash"])
    if existing_id:
        return existing_id, True

    upsert_instrument(ticker, header.get("company"), header.get("exchange"), header.get("price_currency"))
    analysis_id = insert_analysis(payload)
    promote_analysis(analysis_id, ticker)
    return analysis_id, False
