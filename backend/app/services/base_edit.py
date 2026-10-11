"""Save workspace edits as the new base analysis.

Scenarios are deviations from BAU; when the analysis's own BAU inputs are wrong, the user
corrects them and stores the result as a new version of the analysis. This goes through the
real ingest path: the edits are written into the stored markdown's ```json stock-model block,
the engine reruns the outputs, and the file is parsed and stored like an upload. The old
analysis stays as history and saved scenarios rebase onto the new one.
"""

import json
import re
from datetime import date

from supabase import Client

from app.services import ingest, scenarios
from app.services.workspace import NotFound, _inputs_of, _run

_BLOCK_RE = re.compile(r"(```json stock-model\s*\n)(.*?)(\n```)", re.S)


class BaseEditError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def _tag(inputs: dict, path: str, old, new, today: str) -> None:
    """Mark an edited cell as the user's: source 'assumption' (shares keep their share source), ref says what changed."""
    container, key = scenarios._resolve(inputs, path)
    if key not in ("pct", "value") or not isinstance(container, dict):
        return
    was = f"{container.get('source', '')}: {container.get('ref', '')}".strip(": ")
    if path.startswith("shares."):
        container.setdefault("source", "none")
    else:
        container["source"] = "assumption"
    container["ref"] = f"Edited in Portfolio Terminal {today}: {old} → {new}" + (f" (was {was})" if was else "")


def save_as_base(db: Client, ticker: str, overrides: list[dict]) -> dict:
    ticker = ticker.upper()
    if not overrides:
        raise BaseEditError(["No edits to save."])
    inst = db.table("instruments").select("id").eq("ticker", ticker).execute().data
    if not inst:
        raise NotFound(f"No instrument {ticker}")
    rows = (db.table("analyses").select("id, model, raw_markdown, data_as_of")
            .eq("instrument_id", inst[0]["id"]).eq("is_current", True).execute().data)
    if not rows:
        raise NotFound(f"No current analysis for {ticker}")
    current = rows[0]
    md = current.get("raw_markdown") or ""
    if not _BLOCK_RE.search(md):
        raise BaseEditError(["The stored analysis has no json stock-model block to edit."])

    today = date.today().isoformat()
    base_inputs = _inputs_of(current["model"])
    inputs, could_not_apply, _ = scenarios.apply_overrides(base_inputs, overrides)
    if could_not_apply:
        raise BaseEditError([f"Not an input in the current analysis: {p}" for p in could_not_apply])
    changes = []
    for o in overrides:
        old_container, old_key = scenarios._resolve(base_inputs, o["path"])
        old = old_container[old_key]
        if old == o["value"]:
            continue
        _tag(inputs, o["path"], old, o["value"], today)
        changes.append(f"{o['path']}: {old} → {o['value']}")
    if not changes:
        raise BaseEditError(["Every edit matches the current base."])

    model, errors, _ = _run(inputs)
    if errors:
        raise BaseEditError(errors)

    block = json.dumps(model, indent=1, ensure_ascii=False)
    note = (f"> **Base edited in Portfolio Terminal on {today}** (replaces analysis #{current['id']}): "
            + "; ".join(changes) + ". The json block is the source of truth; tables above may show the earlier numbers.\n\n")
    new_md = note + _BLOCK_RE.sub(lambda m: m.group(1) + block + m.group(3), md, count=1)

    filename = f"{ticker}_{current.get('data_as_of') or today}_edited_{today}.md"
    stored = ingest.store(db, new_md, filename)
    return {**stored, "changes": changes}
