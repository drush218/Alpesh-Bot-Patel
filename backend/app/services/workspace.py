"""Scenario workspace (CLAUDE_CODE_PROMPT_model_v2.md section 5): preview edits and
save / load / delete named scenarios against a ticker's current analysis.

Overrides come in from the UI as [{"path", "value"}]; base_value is captured here at save
time from the current analysis. Loading always applies against the *current* analysis, so
a scenario saved on an older base is rebased (scenarios.apply_overrides flags what moved).
base_analysis_id only changes when the user re-saves.
"""

import threading
from datetime import datetime, timezone

from supabase import Client

from app.services import scenarios, stock_model

# stock_model keeps its errors/warnings in module globals, so concurrent runs would mix them.
_engine_lock = threading.Lock()


class NotFound(LookupError):
    pass


def _run(inputs: dict) -> tuple[dict | None, list, list]:
    with _engine_lock:
        return stock_model.run(inputs)


def _inputs_of(model: dict) -> dict:
    return {k: v for k, v in model.items() if k not in ("outputs", "schema_version")}


def current_analysis(db: Client, ticker: str) -> dict:
    """{"instrument_id", "analysis_id", "inputs", "outputs"} for the ticker's current analysis."""
    inst = db.table("instruments").select("id").eq("ticker", ticker.upper()).execute().data
    if not inst:
        raise NotFound(f"No instrument {ticker}")
    rows = (db.table("analyses").select("id, model")
            .eq("instrument_id", inst[0]["id"]).eq("is_current", True).execute().data)
    if not rows:
        raise NotFound(f"No current analysis for {ticker}")
    model = rows[0]["model"]
    return {"instrument_id": inst[0]["id"], "analysis_id": rows[0]["id"],
            "inputs": _inputs_of(model), "outputs": model.get("outputs")}


def _evaluate(base: dict, saved_overrides: list) -> dict:
    inputs, could_not_apply, base_moved = scenarios.apply_overrides(base["inputs"], saved_overrides)
    model, errors, warnings = _run(inputs)
    return {
        "analysis_id": base["analysis_id"],
        "base_outputs": base["outputs"],
        "outputs": model["outputs"] if model else None,
        "errors": errors,
        "warnings": warnings,
        "could_not_apply": could_not_apply,
        "base_moved": base_moved,
    }


def preview(db: Client, ticker: str, edits: list[dict]) -> dict:
    """Run the model on the current analysis plus unsaved edits. Unknown paths are reported, not raised."""
    base = current_analysis(db, ticker)
    overrides = [{"path": e["path"], "value": e["value"]} for e in edits]
    return _evaluate(base, overrides)


def list_scenarios(db: Client, user_id: str, ticker: str) -> list[dict]:
    base = current_analysis(db, ticker)
    rows = (db.table("user_scenarios").select("id, name, note, base_analysis_id, overrides, updated_at")
            .eq("user_id", user_id).eq("instrument_id", base["instrument_id"]).execute().data)
    out = [{
        "id": r["id"], "name": r["name"], "note": r.get("note"),
        "override_count": len(r["overrides"]),
        "on_current_base": r.get("base_analysis_id") == base["analysis_id"],
        "updated_at": r.get("updated_at"),
    } for r in rows]
    return sorted(out, key=lambda r: r["name"].lower())


def save_scenario(db: Client, user_id: str, ticker: str, name: str, note: str | None, edits: list[dict]) -> dict:
    """Create or replace the named scenario. Raises scenarios.PathError for a path not in the current analysis."""
    base = current_analysis(db, ticker)
    overrides = [scenarios.make_override(base["inputs"], e["path"], e["value"]) for e in edits]
    row = db.table("user_scenarios").upsert({
        "user_id": user_id,
        "instrument_id": base["instrument_id"],
        "base_analysis_id": base["analysis_id"],
        "name": name.strip(),
        "note": note,
        "overrides": overrides,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id,instrument_id,name").execute().data[0]
    return {"id": row["id"], "name": row["name"], "override_count": len(overrides)}


def _get_row(db: Client, user_id: str, base: dict, scenario_id: int) -> dict:
    rows = (db.table("user_scenarios").select("*").eq("id", scenario_id).eq("user_id", user_id)
            .eq("instrument_id", base["instrument_id"]).execute().data)
    if not rows:
        raise NotFound(f"No scenario {scenario_id}")
    return rows[0]


def load_scenario(db: Client, user_id: str, ticker: str, scenario_id: int) -> dict:
    base = current_analysis(db, ticker)
    row = _get_row(db, user_id, base, scenario_id)
    result = _evaluate(base, row["overrides"])
    dropped = set(result["could_not_apply"])
    result["scenario"] = {
        "id": row["id"], "name": row["name"], "note": row.get("note"),
        "base_analysis_id": row.get("base_analysis_id"),
        "rebased": row.get("base_analysis_id") != base["analysis_id"],
        # What the workspace should show as edited cells: the overrides that still apply.
        "overrides": [{"path": o["path"], "value": o["value"]} for o in row["overrides"] if o["path"] not in dropped],
    }
    return result


def delete_scenario(db: Client, user_id: str, ticker: str, scenario_id: int) -> None:
    base = current_analysis(db, ticker)
    _get_row(db, user_id, base, scenario_id)
    db.table("user_scenarios").delete().eq("id", scenario_id).eq("user_id", user_id).execute()
