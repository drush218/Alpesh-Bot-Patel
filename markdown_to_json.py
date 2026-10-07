"""
analysis_parser.py
Parse a stock-analysis markdown file (tables-first format, per stock-analysis SKILL.md)
into structured records ready for Supabase insertion.

Usage:
    from analysis_parser import parse_analysis
    payload = parse_analysis(markdown_text)

Design notes
------------
- Nothing is invented. If a section is absent the corresponding list is empty and the
  section name is appended to payload["warnings"]. Silent partial parses are the enemy.
- Wide tables (bridge, forward PE) are unpivoted to long rows so Supabase can index them.
- Numeric coercion is deliberately conservative: it strips $ , % x m bn bold and unicode
  minus/dash, but returns None rather than guessing on ranges or free text. The raw string
  is always retained alongside the parsed value.

Ported unchanged from HandoverFiles/markdown_to_json.py — see HandoverFiles/HANDOFF_claude_code.md
section 4: the sensitivity/factor-code ordering rules in _FACTOR_CODES are subtle
(indirect before direct, named inputs before the oil catch-all) and easy to break in a rewrite.
"""

from __future__ import annotations

import re
import json
import hashlib
from datetime import datetime, date, timezone

# ---------------------------------------------------------------- number parsing

_DASHES = {"\u2013": "-", "\u2014": "-", "\u2212": "-", "\u2011": "-"}
_NUM_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


def clean_cell(s: str) -> str:
    """Strip markdown emphasis, italic memo parens markers and whitespace."""
    if s is None:
        return ""
    s = s.strip()
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"\*(.+?)\*", r"\1", s)
    s = re.sub(r"`(.+?)`", r"\1", s)
    for k, v in _DASHES.items():
        s = s.replace(k, v)
    return s.strip()


def to_number(s: str):
    """
    Coerce a table cell to float. Returns None when the cell is not a clean scalar
    (ranges like '2.05-2.08', text, blanks). Handles $ , % x suffix, m/bn multipliers,
    parenthesised negatives, and leading em-dash bullets.
    """
    if s is None:
        return None
    t = clean_cell(s)
    if not t or t in {"-", "—", "n/a", "N/A", "TBD", "none", "flat"}:
        return None

    t = t.lstrip("-\u2014\u2248~\u2264\u2265 ").strip()   # leading em-dash bullet, approx signs
    neg = t.startswith("(") and t.endswith(")")
    if neg:
        t = t[1:-1]

    t = t.replace("$", "").replace("\u00a3", "").replace(",", "").strip()

    mult = 1.0
    low = t.lower()
    if low.endswith("bn"):
        mult, t = 1000.0, t[:-2]
    elif low.endswith("bps"):
        t = t[:-3]
    elif low.endswith("m"):
        t = t[:-1]
    elif low.endswith("x"):
        t = t[:-1]
    elif low.endswith("%"):
        t = t[:-1]
    elif low.endswith("pp"):
        t = t[:-2]

    t = t.strip().lstrip("+")
    if not _NUM_RE.match(t):
        return None
    v = float(t) * mult
    return -v if neg else v


def is_pct(s: str) -> bool:
    return "%" in (s or "")


# ---------------------------------------------------------------- table extraction

def _split_row(line: str):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def _is_sep(line: str) -> bool:
    return bool(re.match(r"^\s*\|?[\s:\-|]+\|?\s*$", line)) and "-" in line


def extract_blocks(md: str):
    """
    Walk the document once, returning a list of blocks:
      {"heading": str|None, "tables": [ {headers, rows} ], "text": [str] }
    Heading = most recent '###'-level heading above the content.
    """
    blocks = []
    current = {"heading": None, "tables": [], "text": []}
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        h = re.match(r"^(#{1,6})\s+(.*)$", line)
        if h:
            if current["heading"] is not None or current["tables"] or current["text"]:
                blocks.append(current)
            current = {"heading": clean_cell(h.group(2)), "level": len(h.group(1)),
                       "tables": [], "text": []}
            i += 1
            continue

        if line.strip().startswith("|") and i + 1 < len(lines) and _is_sep(lines[i + 1]):
            headers = [clean_cell(c) for c in _split_row(line)]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = _split_row(lines[i])
                if not _is_sep(lines[i]):
                    rows.append(cells)
                i += 1
            current["tables"].append({"headers": headers, "rows": rows})
            continue

        if line.strip():
            current["text"].append(line.rstrip())
        i += 1

    blocks.append(current)
    return blocks


def find_block(blocks, *keywords, require_table=True):
    """Return first block whose heading contains all keywords (case-insensitive)."""
    for b in blocks:
        h = (b.get("heading") or "").lower()
        if all(k.lower() in h for k in keywords):
            if not require_table or b["tables"]:
                return b
    return None


# ---------------------------------------------------------------- header

def parse_header(md: str, blocks) -> dict:
    out = {"company": None, "ticker": None, "price": None, "price_currency": None,
           "price_date": None, "data_currency": None, "exchange": None,
           "calibration_note": None}

    m = re.search(r"^#\s+(.+?)\s*[\(\[]([A-Z0-9\.\-]+)[\)\]]\s*(?:—|-|–)?\s*(.*)$",
                  md, re.M)
    if m:
        out["company"] = clean_cell(m.group(1))
        out["ticker"] = m.group(2).strip()

    pm = re.search(r"\*\*Price:\*\*\s*([^\·\n]+)", md)
    if pm:
        raw = pm.group(1).strip()
        out["price_raw"] = raw
        cur = re.search(r"([\$\u00a3\u20ac])", raw)
        out["price_currency"] = {"$": "USD", "\u00a3": "GBP", "\u20ac": "EUR"}.get(
            cur.group(1)) if cur else None
        num = re.search(r"[\d,]+(?:\.\d+)?", raw)
        if num:
            out["price"] = float(num.group(0).replace(",", ""))
            if raw.strip().lower().endswith("p") or re.search(r"\dp\b", raw):
                out["price_currency"] = "GBp"
        dm = re.search(r"\(([^)]+)\)", raw)
        if dm:
            out["price_date"] = _parse_date(dm.group(1))

    dc = re.search(r"\*\*Data:\*\*\s*([^\·\n]+)", md)
    if dc:
        out["data_currency"] = clean_cell(dc.group(1))

    ex = re.search(r"\*\*Data:\*\*[^\n]*?\u00b7\s*\*\*([A-Za-z ]+)\*\*", md)
    if ex:
        out["exchange"] = ex.group(1).strip()

    for b in blocks[:2]:
        for t in b["text"]:
            if "calibrat" in t.lower():
                out["calibration_note"] = clean_cell(t)
                break
    return out


_MONTHS = {m.lower(): i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def _parse_date(s: str):
    s = clean_cell(s)
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})", s)
    if m:
        mon = _MONTHS.get(m.group(2)[:3].lower())
        if mon:
            return date(int(m.group(3)), mon, int(m.group(1))).isoformat()
    m = re.search(r"([A-Za-z]{3,})\s+(\d{1,2}),?\s+(\d{4})", s)
    if m:
        mon = _MONTHS.get(m.group(1)[:3].lower())
        if mon:
            return date(int(m.group(3)), mon, int(m.group(2))).isoformat()
    return None


# ---------------------------------------------------------------- year columns

_YEAR_RE = re.compile(r"(20\d{2})\s*([AE])?", re.I)


def year_columns(headers):
    """Map column index -> (fiscal_year, actual_flag) for year-shaped headers."""
    cols = {}
    for i, h in enumerate(headers):
        m = _YEAR_RE.search(clean_cell(h))
        if m:
            cols[i] = (int(m.group(1)), (m.group(2) or "E").upper() == "A")
    return cols


# ---------------------------------------------------------------- section parsers

def parse_pe_table(blocks):
    b = find_block(blocks, "PE from earnings")
    if not b:
        return []
    t = b["tables"][0]
    out = []
    for r in t["rows"]:
        if len(r) < 5:
            continue
        out.append({
            "basis": clean_cell(r[0]),
            "net_income_m": to_number(r[1]),
            "shares_m": to_number(r[2]),
            "eps": to_number(r[3]),
            "pe": to_number(r[4]),
        })
    return out


_LINE_MAP = [
    (r"^revenue \(total\)", "revenue_total", False),
    (r"company-operated", "revenue_company_operated", False),
    (r"franchise", "revenue_franchise_other", False),
    (r"^cost of sales$", "cost_of_sales", False),
    (r"cos % of rev", "cos_pct_rev", True),
    (r"^sg&a$", "sga", False),
    (r"sg&a % of rev", "sga_pct_rev", True),
    (r"^ebit$", "ebit", False),
    (r"ebit margin", "ebit_margin_pct", True),
    (r"\+d&a", "d_and_a", False),
    (r"\bebitda\b", "ebitda", False),
    (r"net interest", "net_interest", False),
    (r"^pretax$", "pretax", False),
    (r"^tax", "tax", False),
    (r"net income \(total\)", "net_income_total", False),
    (r"net income attributable|attributable", "net_income_attributable", False),
    (r"economic shares", "shares_economic_m", False),
    (r"^shares", "shares_m", False),
    (r"^eps", "eps", False),
]


def map_line(label: str):
    l = clean_cell(label).lower().lstrip("-\u2014 ").strip()
    l = re.sub(r"^\(memo\)\s*", "", l)
    for pat, key, pct in _LINE_MAP:
        if re.search(pat, l):
            return key, pct
    return None, False


def parse_bridge(blocks):
    b = find_block(blocks, "bridge")
    if not b:
        return [], []
    t = b["tables"][0]
    ycols = year_columns(t["headers"])
    rows, unmapped = [], []
    for r in t["rows"]:
        label = r[0]
        key, pct = map_line(label)
        if key is None:
            unmapped.append(clean_cell(label))
        for idx, (fy, is_actual) in ycols.items():
            if idx >= len(r):
                continue
            raw = r[idx]
            val = to_number(raw)
            if val is None and not clean_cell(raw):
                continue
            rows.append({
                "fiscal_year": fy,
                "is_actual": is_actual,
                "line_label": clean_cell(label).lstrip("-\u2014 ").strip(),
                "line_key": key,
                "value": val,
                "unit": "pct" if (pct or is_pct(raw)) else "m",
                "raw": clean_cell(raw),
            })
    return rows, unmapped


def parse_forward_pe(blocks):
    b = find_block(blocks, "forward pe")
    if not b:
        return []
    t = b["tables"][0]
    ycols = year_columns(t["headers"])
    out = []
    for r in t["rows"]:
        scen = clean_cell(r[0]).upper()
        for idx, (fy, is_actual) in ycols.items():
            if idx < len(r):
                v = to_number(r[idx])
                if v is not None:
                    out.append({"scenario": scen, "fiscal_year": fy,
                                "is_actual": is_actual, "pe": v})
    return out


def parse_scenario_drivers(blocks):
    """The 'Low / High — what changes...' table: Driver | LOW | BAU | HIGH | Effect."""
    b = find_block(blocks, "low", "high")
    if not b:
        return [], []
    t = b["tables"][0]
    hdr = [clean_cell(h).upper() for h in t["headers"]]
    try:
        scen_idx = {s: hdr.index(s) for s in ("LOW", "BAU", "HIGH")}
    except ValueError:
        return [], []
    eff_idx = len(hdr) - 1

    drivers, outcomes = [], []
    for r in t["rows"]:
        label = clean_cell(r[0])
        low = label.lower()
        target = re.search(r"20(\d{2})\s*(eps|pe)", low)
        for scen, idx in scen_idx.items():
            if idx >= len(r):
                continue
            raw = clean_cell(r[idx])
            if not raw:
                continue
            if target:
                outcomes.append({
                    "scenario": scen,
                    "fiscal_year": 2000 + int(target.group(1)),
                    "metric": target.group(2).lower(),
                    "value": to_number(raw),
                    "raw": raw,
                })
            else:
                drivers.append({
                    "scenario": scen,
                    "driver": label,
                    "value_raw": raw,
                    "value": to_number(raw),
                    "effect": clean_cell(r[eff_idx]) if eff_idx < len(r) else None,
                })
    return drivers, outcomes


def parse_scenario_assumptions(blocks):
    b = find_block(blocks, "assumption")
    if not b:
        return []
    t = b["tables"][0]
    hdr = [clean_cell(h) for h in t["headers"]]
    out = []
    for r in t["rows"]:
        scen = clean_cell(r[0]).upper()
        rec = {"scenario": scen, "assumptions": {}, "justification": None}
        for i, h in enumerate(hdr[1:], start=1):
            if i >= len(r):
                continue
            v = clean_cell(r[i])
            if h.lower().startswith("justif"):
                rec["justification"] = v
            else:
                rec["assumptions"][h] = v
        out.append(rec)
    return out


def parse_peers(blocks):
    b = find_block(blocks, "peer")
    if not b:
        return []
    t = b["tables"][0]
    hdr = [clean_cell(h) for h in t["headers"]]
    out = []
    for r in t["rows"]:
        name = clean_cell(r[0])
        if not name:
            continue
        rec = {"peer": name, "metrics": {}}
        for i, h in enumerate(hdr[1:], start=1):
            if i < len(r) and clean_cell(r[i]):
                rec["metrics"][h] = {"raw": clean_cell(r[i]), "value": to_number(r[i])}
        out.append(rec)
    return out


# factor code normalisation — this is the join key to macro_factors
_FACTOR_CODES = [
    # order matters: most specific first. "indirect" before "direct" (substring),
    # and named agricultural/labour inputs before the generic oil catch-all so that
    # a line like "Coffee + dairy (non-oil)" is never coded as OIL.
    (r"(oil|gas).*indirect", "OIL_INDIRECT"),
    (r"(oil|gas).*total", "OIL_TOTAL"),
    (r"(oil|gas).*direct", "OIL_DIRECT"),
    (r"coffee|arabica", "COFFEE"),
    (r"dairy|milk", "DAIRY"),
    (r"wage|labour|labor", "WAGE"),
    (r"freight|diesel|shipping", "FREIGHT"),
    (r"rate.*(valuation|multiple)|10y", "RATES_VALUATION"),
    (r"rate.*earning|net interest", "RATES_EARNINGS"),
    (r"\brates?\b|\binterest\b", "RATES"),
    (r"\bfx\b|dxy|dollar|currency|gbpusd|eurusd", "FX"),
    (r"copper", "COPPER"),
    (r"zinc", "ZINC"),
    (r"gold", "GOLD"),
    (r"consumer|traffic|footfall", "CONSUMER"),
    (r"ecl|credit loss|npl", "CREDIT"),
    (r"tariff|trade war", "TARIFF"),
    (r"inflation|cpi", "INFLATION"),
    (r"(?<!non-)\b(oil|gas|brent|wti)\b", "OIL"),
]


def factor_code(label: str):
    l = clean_cell(label).lower()
    for pat, code in _FACTOR_CODES:
        if re.search(pat, l):
            return code
    return "OTHER:" + re.sub(r"[^a-z0-9]+", "_", l).strip("_").upper()[:40]


def parse_sensitivities(blocks):
    b = find_block(blocks, "sensitivity")
    if not b:
        return [], None
    t = b["tables"][0]
    anchor = None
    for line in b["text"]:
        if "anchor" in line.lower():
            anchor = clean_cell(line)
            break

    fy = None
    hm = re.search(r"(20\d{2})", b.get("heading") or "")
    if hm:
        fy = int(hm.group(1))

    out = []
    for r in t["rows"]:
        if len(r) < 3:
            continue
        label = clean_cell(r[0])
        if not label:
            continue
        move = clean_cell(r[1])
        impact_raw = clean_cell(r[2])
        channel = clean_cell(r[3]) if len(r) > 3 else None
        val = to_number(impact_raw)
        # em-dash prefixed negatives ("‑7%") lose their sign in cleanup — restore
        if val is not None and re.match(r"^\s*[\u2248~]?\s*[\u2010-\u2015-]", r[2].replace("*", "")):
            val = -abs(val)
        code = factor_code(label)
        out.append({
            "factor_label": label,
            "factor_code": code,
            "fiscal_year": fy,
            "move": move,
            "move_value": to_number(move),
            "eps_impact_pct": val,
            "eps_impact_raw": impact_raw,
            # TOTAL rows are the sum of their direct+indirect components. The live
            # recompute must skip these or oil gets counted twice.
            "is_aggregate": code.endswith("_TOTAL") or "total" in label.lower(),
            # rates-valuation hits the multiple, not EPS — excluded from EPS recompute,
            # applied to the target PE instead.
            "is_multiple_effect": val is None and "multiple" in impact_raw.lower(),
            "channel": channel,
        })
    return out, anchor


_SEV = {"high": 3, "medium-high": 3, "medium": 2, "low-medium": 2, "low": 1}


def parse_risks(blocks):
    b = find_block(blocks, "risk")
    if not b:
        return []
    t = b["tables"][0]
    out = []
    for r in t["rows"]:
        if len(r) < 2:
            continue
        sev = clean_cell(r[1])
        base = re.sub(r"\(.*?\)", "", sev).strip().lower()
        out.append({
            "risk": clean_cell(r[0]),
            "severity": sev,
            "severity_rank": _SEV.get(base),
            "impact": clean_cell(r[2]) if len(r) > 2 else None,
        })
    return out


def parse_narrative(md: str) -> dict:
    out = {}
    for key, pat in [
        ("what_moves_the_lines", r"\*\*What moves the lines:\*\*\s*(.+?)(?:\n\n|\n\*\*|\n###)"),
        ("shares_note", r"\*\*Shares:\*\*\s*(.+?)(?:\n\n|\n\*\*|\n###)"),
        ("read", r"\*\*Read:\*\*\s*(.+?)(?:\n\n|\n\*\*|\n###)"),
        ("bottom_line", r"\*\*(?:Bottom line|One-line justification):\*\*\s*(.+?)(?:\n\n|\n---)"),
    ]:
        m = re.search(pat, md, re.S | re.I)
        if m:
            out[key] = clean_cell(" ".join(m.group(1).split()))
    return out


# ---------------------------------------------------------------- orchestrator

REQUIRED = ["pe_basis", "bridge", "forward_pe", "sensitivities"]


def parse_analysis(md: str, source_name: str | None = None) -> dict:
    blocks = extract_blocks(md)
    header = parse_header(md, blocks)
    bridge, unmapped = parse_bridge(blocks)
    drivers, outcomes = parse_scenario_drivers(blocks)
    sens, anchor = parse_sensitivities(blocks)

    payload = {
        "schema_version": 1,
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "source_name": source_name,
        "content_hash": hashlib.sha256(md.encode()).hexdigest()[:16],
        "analysis": header,
        "pe_basis": parse_pe_table(blocks),
        "bridge": bridge,
        "scenario_drivers": drivers,
        "scenario_outcomes": outcomes,
        "scenario_assumptions": parse_scenario_assumptions(blocks),
        "forward_pe": parse_forward_pe(blocks),
        "peers": parse_peers(blocks),
        "sensitivities": sens,
        "sensitivity_anchor": anchor,
        "risks": parse_risks(blocks),
        "narrative": parse_narrative(md),
        "raw_markdown": md,
        "warnings": [],
    }

    for k in REQUIRED:
        if not payload[k]:
            payload["warnings"].append(f"missing section: {k}")
    if not header.get("ticker"):
        payload["warnings"].append("could not parse ticker from H1")
    if not header.get("price"):
        payload["warnings"].append("could not parse price")
    for k in ("risks", "peers", "scenario_assumptions"):
        if not payload[k]:
            payload["warnings"].append(f"optional section absent: {k}")
    for u in unmapped:
        payload["warnings"].append(f"unmapped bridge line: {u}")

    return payload


if __name__ == "__main__":
    import sys
    with open(sys.argv[1]) as f:
        print(json.dumps(parse_analysis(f.read(), sys.argv[1]), indent=2))
