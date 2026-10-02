"""
Scenario workspace overrides (CLAUDE_CODE_PROMPT_model_v2.md section 5).

An override is {"path": ..., "value": ..., "base_value": ...} against the model inputs.
Paths address segments by name and years by forecast_years label, never by index, so a
re-run that reorders segments or rolls the years forward can't misapply them:

    revenue.segments[Company-operated].growth[FY2027].pct
    operating_margin[FY2026].pct
    shares.annual_change[FY2028].pct
    scenarios.low.growth_pp
"""

import copy
import re

_TOKEN_RE = re.compile(r"([^.\[\]]+)|\[([^\]]+)\]")


class PathError(KeyError):
    pass


def _tokens(path: str) -> list:
    out = []
    for key, sel in _TOKEN_RE.findall(path):
        out.append(("key", key) if key else ("sel", sel))
    return out


def _resolve(inputs: dict, path: str):
    """Return (container, key) for the final step of path. Raises PathError if it doesn't exist."""
    years = inputs.get("meta", {}).get("forecast_years") or []
    node, parent, last = inputs, None, None
    for kind, tok in _tokens(path):
        parent = node
        if kind == "key":
            if not isinstance(node, dict) or tok not in node:
                raise PathError(path)
            last = tok
        else:
            if not isinstance(node, list):
                raise PathError(path)
            named = [i for i, x in enumerate(node) if isinstance(x, dict) and x.get("name") == tok]
            if named:
                last = named[0]
            elif tok in years and years.index(tok) < len(node):
                last = years.index(tok)
            else:
                raise PathError(path)
        node = parent[last]
    if parent is None:
        raise PathError(path)
    return parent, last


def get_at(inputs: dict, path: str):
    container, key = _resolve(inputs, path)
    return container[key]


def make_override(base_inputs: dict, path: str, value) -> dict:
    """Build an override for saving, capturing the base value at save time."""
    return {"path": path, "value": value, "base_value": get_at(base_inputs, path)}


def apply_overrides(base_inputs: dict, overrides: list) -> tuple[dict, list, list]:
    """
    Apply overrides to a copy of base_inputs (which may be a newer analysis than the one the
    scenario was saved against). Returns (inputs, could_not_apply, base_moved):
      could_not_apply - paths that no longer exist; the override is dropped
      base_moved      - [{"path", "saved_base", "current_base", "note"}]; override still applied
    """
    inputs = copy.deepcopy(base_inputs)
    could_not_apply, base_moved = [], []
    for o in overrides:
        try:
            container, key = _resolve(inputs, o["path"])
        except PathError:
            could_not_apply.append(o["path"])
            continue
        current = container[key]
        if "base_value" in o and current != o["base_value"]:
            base_moved.append({
                "path": o["path"],
                "saved_base": o["base_value"],
                "current_base": current,
                "note": f"base moved: {o['base_value']} → {current}",
            })
        container[key] = o["value"]
    return inputs, could_not_apply, base_moved
