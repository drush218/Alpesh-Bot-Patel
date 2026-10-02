#!/usr/bin/env python3
"""
Stock analysis v2 — inputs JSON -> validated, computed model -> markdown file with embedded JSON.

Usage:  python model.py inputs.json OUTPUT.md
Exit 1 on validation errors (printed). Warnings print but do not block.

The markdown tables and the ```json stock-model block are both rendered from the same computed
object, so the human view and the parsed view cannot disagree.
"""
import json, sys, re, copy
from datetime import date

SOURCES        = {"guidance", "filing", "assumption"}
SHARE_SOURCES  = {"none", "issuance_declared", "buyback_executed", "issuance_and_buyback"}
DIRECTIONS     = {"bull", "bear", "neutral"}
STRENGTHS      = {"negligible", "mild", "medium", "strong"}
SPEEDS         = {"immediate", "near", "lagged"}
EXPOSURES      = {"minor", "partial", "dominant"}
EVENT_TYPES    = {"earnings", "trading_update", "agm", "ex_dividend", "dividend_pay", "capital_markets_day",
                  "debt_maturity", "guidance", "index", "other"}
MACRO_FACTORS  = {"rates_policy", "rates_10y", "fx_usd", "oil", "natgas", "labour", "consumer_spend",
                  "credit_spreads", "inflation", "china_activity"}  # extend deliberately, not per company
# commodity_<name> (e.g. commodity_copper) is also allowed

errors, warnings = [], []

def err(m): errors.append(m)
def warn(m): warnings.append(m)

PROPOSED = set()   # filled per file from proposed_factors

def is_factor(code):
    return (code in MACRO_FACTORS or code in PROPOSED
            or (isinstance(code, str) and re.fullmatch(r"commodity_[a-z0-9_]+", code)))

def check_cell(cell, where, key="pct"):
    if not isinstance(cell, dict): err(f"{where}: expected object"); return
    if key not in cell or not isinstance(cell[key], (int, float)): err(f"{where}: missing numeric '{key}'")
    if cell.get("source") not in SOURCES: err(f"{where}: source must be one of {sorted(SOURCES)}")
    if not str(cell.get("ref", "")).strip(): err(f"{where}: 'ref' (citation or assumption reason) is required")

def check_series(lst, n, where, key="pct"):
    if not isinstance(lst, list) or len(lst) != n:
        err(f"{where}: need exactly {n} entries (one per forecast year)"); return
    for i, c in enumerate(lst): check_cell(c, f"{where}[{i}]", key)

def validate(m):
    for i, f in enumerate(m.get("proposed_factors", [])):
        code = f.get("code", "")
        if not re.fullmatch(r"[a-z][a-z0-9_]+", code): err(f"proposed_factors[{i}]: snake_case code required")
        if code in MACRO_FACTORS: err(f"proposed_factors[{i}]: '{code}' already on the fixed list")
        for k in ["name", "series", "provider", "rationale"]:
            if not f.get(k): err(f"proposed_factors[{i}].{k} required")
        if f.get("scope") not in {"master", "company"}: err(f"proposed_factors[{i}].scope master|company")
        if f.get("scope") == "master" and len(f.get("other_names", [])) < 2:
            warn(f"proposed_factors[{i}]: master scope but <2 other names listed — likely a company factor")
        PROPOSED.add(code)
    meta = m.get("meta", {})
    for k in ["ticker", "company", "exchange", "reporting_currency", "price_currency", "units",
              "base_year", "forecast_years", "data_as_of", "data_sources"]:
        if k not in meta: err(f"meta.{k} missing")
    yrs = meta.get("forecast_years", [])
    n = len(yrs)
    if n == 0: err("meta.forecast_years empty"); return
    segs = m.get("revenue", {}).get("segments", [])
    if not segs: err("revenue.segments: at least one (use a single 'Total' segment if no split)")
    for s in segs:
        if not s.get("name"): err("segment missing name")
        if not isinstance(s.get("base"), (int, float)): err(f"segment {s.get('name')}: numeric base required")
        if not str(s.get("base_ref", "")).strip(): err(f"segment {s.get('name')}: base_ref required")
        check_series(s.get("growth"), n, f"revenue.{s.get('name')}.growth")
    check_series(m.get("operating_margin"), n, "operating_margin")
    check_series(m.get("net_interest"), n, "net_interest", key="value")
    check_series(m.get("tax_rate"), n, "tax_rate")
    if "nci_pct" in m: check_series(m["nci_pct"], n, "nci_pct")
    sh = m.get("shares", {})
    if not isinstance(sh.get("base_diluted"), (int, float)): err("shares.base_diluted required")
    if not str(sh.get("base_ref", "")).strip(): err("shares.base_ref required")
    ch = sh.get("annual_change", [])
    if len(ch) != n: err(f"shares.annual_change: need {n} entries")
    for i, c in enumerate(ch):
        if c.get("source") not in SHARE_SOURCES: err(f"shares.annual_change[{i}]: source must be {sorted(SHARE_SOURCES)}")
        if c.get("pct", 0) != 0 and c.get("source") == "none": err(f"shares.annual_change[{i}]: non-zero change needs a declared basis")
        if c.get("source") != "none" and not str(c.get("ref", "")).strip(): err(f"shares.annual_change[{i}]: ref required")
    sc = m.get("scenarios", {})
    for k in ["low", "high"]:
        s = sc.get(k)
        if not s: err(f"scenarios.{k} missing"); continue
        for f in ["growth_pp", "margin_pp"]:
            if not isinstance(s.get(f), (int, float)): err(f"scenarios.{k}.{f} numeric required")
        if not str(s.get("ref", "")).strip(): err(f"scenarios.{k}.ref required")
    if sc.get("low", {}).get("growth_pp", 0) > 0 or sc.get("high", {}).get("growth_pp", 0) < 0:
        warn("scenario growth deltas have unexpected sign (LOW should be <=0, HIGH >=0)")
    for i, e in enumerate(m.get("calendar", [])):
        try: date.fromisoformat(e.get("date", ""))
        except Exception: err(f"calendar[{i}]: ISO date required")
        if e.get("type") not in EVENT_TYPES: err(f"calendar[{i}]: type must be {sorted(EVENT_TYPES)}")
        if not isinstance(e.get("confirmed"), bool): err(f"calendar[{i}]: confirmed true/false required")
    for i, x in enumerate(m.get("macro", [])):
        if not is_factor(x.get("factor")): err(f"macro[{i}]: unknown factor '{x.get('factor')}'")
        if x.get("direction") not in DIRECTIONS: err(f"macro[{i}]: direction {sorted(DIRECTIONS)}")
        if x.get("strength") not in STRENGTHS: err(f"macro[{i}]: strength {sorted(STRENGTHS)}")
        if x.get("speed") not in SPEEDS: err(f"macro[{i}]: speed {sorted(SPEEDS)}")
    fac = [(x.get("factor"), x.get("channel")) for x in m.get("macro", [])]
    if len(fac) != len(set(fac)): err("macro: duplicate factor+channel row (split channels must have distinct channel names)")
    for i, b in enumerate(m.get("backtests", [])):
        if not is_factor(b.get("factor")): err(f"backtests[{i}]: unknown factor")
        for k in ["series", "provider", "hypothesis"]:
            if not b.get(k): err(f"backtests[{i}].{k} required")
    sc_s = m.get("scorecard_suggested")
    if sc_s is None: err("scorecard_suggested required")
    else:
        for k in ["growth", "value", "income"]:
            c = sc_s.get(k, {})
            if c.get("score") not in {1, 2, 3, 4, 5}: err(f"scorecard_suggested.{k}.score 1–5")
            if not str(c.get("ref", "")).strip(): err(f"scorecard_suggested.{k}.ref required")
        for k in ["bull_catalysts", "bear_catalysts"]:
            lst = sc_s.get(k, [])
            if not lst: err(f"scorecard_suggested.{k}: at least one")
            for j, c in enumerate(lst):
                if not c.get("text"): err(f"scorecard_suggested.{k}[{j}].text required")
                if c.get("date"):
                    try: date.fromisoformat(c["date"])
                    except Exception: err(f"scorecard_suggested.{k}[{j}].date ISO")
    for i, l in enumerate(m.get("levers", [])):
        if l.get("base") not in {"revenue", "cost"}: err(f"levers[{i}].base revenue|cost")
        if l.get("exposure") not in EXPOSURES: err(f"levers[{i}].exposure {sorted(EXPOSURES)}")
        if l.get("speed") not in SPEEDS: err(f"levers[{i}].speed {sorted(SPEEDS)}")
        if l.get("direction") not in {"bull", "bear", None}: err(f"levers[{i}].direction bull|bear|null")
        if l.get("macro_factor_code") and not is_factor(l["macro_factor_code"]): err(f"levers[{i}]: unknown macro_factor_code")

def compute(m):
    yrs = m["meta"]["forecast_years"]; n = len(yrs)
    segs = m["revenue"]["segments"]
    base_total = sum(s["base"] for s in segs)
    out = {}
    for scen in ["bau", "low", "high"]:
        gd = 0 if scen == "bau" else m["scenarios"][scen]["growth_pp"]
        md = 0 if scen == "bau" else m["scenarios"][scen]["margin_pp"]
        seg_vals = {s["name"]: s["base"] for s in segs}
        shares = m["shares"]["base_diluted"]
        prev_total = base_total
        rows = []
        for i, y in enumerate(yrs):
            seg_row = {}
            for s in segs:
                g = s["growth"][i]["pct"] + gd
                seg_vals[s["name"]] *= 1 + g / 100
                seg_row[s["name"]] = {"growth_pct": round(g, 2), "revenue": round(seg_vals[s["name"]], 1)}
            total = sum(seg_vals.values())
            margin = m["operating_margin"][i]["pct"] + md
            ebit = total * margin / 100
            pretax = ebit + m["net_interest"][i]["value"]
            tax = pretax * m["tax_rate"][i]["pct"] / 100 if pretax > 0 else 0.0
            ni = pretax - tax
            nci = ni * m["nci_pct"][i]["pct"] / 100 if "nci_pct" in m else 0.0
            ni_attr = ni - nci
            shares *= 1 + m["shares"]["annual_change"][i].get("pct", 0) / 100
            rows.append({
                "year": y, "segments": seg_row,
                "revenue": round(total, 1), "revenue_growth_pct": round((total / prev_total - 1) * 100, 2),
                "operating_margin_pct": round(margin, 2), "operating_income": round(ebit, 1),
                "pretax": round(pretax, 1), "tax": round(tax, 1), "net_income": round(ni_attr, 1),
                "shares_diluted": round(shares, 2), "eps": round(ni_attr / shares, 4)})
            prev_total = total
        out[scen] = rows
    return {"base_revenue": round(base_total, 1), "scenarios": out}

def fmt(x, d=0): return f"{x:,.{d}f}"
def tag(c): return {"guidance": "G", "filing": "F", "assumption": "A"}[c["source"]]

def render(m):
    meta, yrs, o = m["meta"], m["meta"]["forecast_years"], m["outputs"]
    bau = o["scenarios"]["bau"]; u = meta["units"]; cur = meta["reporting_currency"]
    L = []
    L.append(f"# {meta['company']} ({meta['ticker']}) — Stock Model v2")
    L.append(f"**Data as of:** {meta['data_as_of']} · **Sources:** {'; '.join(meta['data_sources'])} · "
             f"**{meta['exchange']}** · figures in {cur} {u} · price in {meta['price_currency']}")
    if meta.get("structure_note"): L.append(meta["structure_note"])
    if meta.get("one_offs_stripped"): L.append("**Base cleaned of:** " + "; ".join(meta["one_offs_stripped"]))
    L.append("\nSource tags: **G** guidance · **F** filing · **A** assumption. Live price → PE computed by the app.\n")
    # Revenue
    L.append("## 1. Revenue")
    hdr = "| Segment | " + f"{meta['base_year']}A | " + " | ".join(f"{y} growth | {y}" for y in yrs) + " |"
    L.append(hdr); L.append("|" + "---|" * (2 + 2 * len(yrs)))
    for s in m["revenue"]["segments"]:
        cells = [f"{s['name']}", fmt(s["base"])]
        for i, y in enumerate(yrs):
            cells += [f"{s['growth'][i]['pct']:+.1f}% {tag(s['growth'][i])}", fmt(bau[i]["segments"][s["name"]]["revenue"])]
        L.append("| " + " | ".join(cells) + " |")
    cells = ["**Total**", f"**{fmt(o['base_revenue'])}**"]
    for r in bau: cells += [f"**{r['revenue_growth_pct']:+.1f}%**", f"**{fmt(r['revenue'])}**"]
    L.append("| " + " | ".join(cells) + " |")
    L.append("\n| Ref | Basis |\n|---|---|")
    for s in m["revenue"]["segments"]:
        L.append(f"| {s['name']} base | {s['base_ref']} |")
        for i, y in enumerate(yrs): L.append(f"| {s['name']} {y} | {tag(s['growth'][i])}: {s['growth'][i]['ref']} |")
    # Margin + bridge
    L.append("\n## 2. Operating margin → net income → EPS (BAU)")
    L.append("| Line | " + " | ".join(yrs) + " |"); L.append("|" + "---|" * (1 + len(yrs)))
    L.append("| Revenue | " + " | ".join(fmt(r["revenue"]) for r in bau) + " |")
    L.append("| Operating margin | " + " | ".join(f"{c['pct']:.1f}% {tag(c)}" for c in m["operating_margin"]) + " |")
    L.append("| Operating income | " + " | ".join(fmt(r["operating_income"]) for r in bau) + " |")
    L.append("| Net interest | " + " | ".join(f"{fmt(c['value'])} {tag(c)}" for c in m["net_interest"]) + " |")
    L.append("| Tax rate | " + " | ".join(f"{c['pct']:.1f}% {tag(c)}" for c in m["tax_rate"]) + " |")
    if "nci_pct" in m: L.append("| NCI share | " + " | ".join(f"{c['pct']:.1f}% {tag(c)}" for c in m["nci_pct"]) + " |")
    L.append("| **Net income** | " + " | ".join(f"**{fmt(r['net_income'])}**" for r in bau) + " |")
    L.append("| Diluted shares (m) | " + " | ".join(fmt(r["shares_diluted"], 1) for r in bau) + " |")
    L.append("| **EPS** | " + " | ".join(f"**{r['eps']:.2f}**" for r in bau) + " |")
    L.append("\n| Ref | Basis |\n|---|---|")
    for lbl, key in [("Margin", "operating_margin"), ("Interest", "net_interest"), ("Tax", "tax_rate")]:
        for i, y in enumerate(yrs): L.append(f"| {lbl} {y} | {tag(m[key][i])}: {m[key][i]['ref']} |")
    # Shares
    sh = m["shares"]
    L.append("\n## 3. Shares")
    L.append(f"Base diluted: **{fmt(sh['base_diluted'], 1)}m** — {sh['base_ref']}\n")
    L.append("| Year | Change | Basis |\n|---|---|---|")
    for i, y in enumerate(yrs):
        c = sh["annual_change"][i]
        L.append(f"| {y} | {c.get('pct', 0):+.1f}% | {c['source']}{': ' + c['ref'] if c.get('ref') else ''} |")
    # Scenarios
    L.append("\n## 4. Scenarios (deltas vs BAU, every forecast year)")
    L.append("| | Growth Δ (pp) | Margin Δ (pp) | Basis |\n|---|---|---|---|")
    for k in ["low", "high"]:
        s = m["scenarios"][k]; L.append(f"| {k.upper()} | {s['growth_pp']:+.1f} | {s['margin_pp']:+.1f} | {s['ref']} |")
    L.append("\n| EPS | " + " | ".join(yrs) + " |"); L.append("|" + "---|" * (1 + len(yrs)))
    for k in ["low", "bau", "high"]:
        L.append(f"| {k.upper()} | " + " | ".join(f"{r['eps']:.2f}" for r in o["scenarios"][k]) + " |")
    if meta.get("reference_price"):
        p = meta["reference_price"]
        L.append(f"\nForward PE at reference price {p['value']} {meta['price_currency']} ({p['date']}; snapshot only — app uses live):")
        L.append("\n| PE | " + " | ".join(yrs) + " |"); L.append("|" + "---|" * (1 + len(yrs)))
        conv = p.get("eps_to_price_fx", 1.0)
        for k in ["low", "bau", "high"]:
            L.append(f"| {k.upper()} | " + " | ".join(
                (f"{p['value'] / (r['eps'] * conv):.1f}x" if r["eps"] > 0 else "n/m") for r in o["scenarios"][k]) + " |")
    # Calendar
    L.append("\n## 5. Calendar")
    L.append("| Date | Event | Type | Confirmed | Source |\n|---|---|---|---|---|")
    for e in sorted(m.get("calendar", []), key=lambda e: e["date"]):
        L.append(f"| {e['date']} | {e['event']} | {e['type']} | {'yes' if e['confirmed'] else 'est.'} | {e.get('source', '')} |")
    # Macro
    L.append("\n## 6. Macro")
    L.append("| Factor | Channel | Direction | Strength | Speed | Why |\n|---|---|---|---|---|---|")
    for x in m.get("macro", []):
        L.append(f"| {x['factor']} | {x.get('channel', '')} | {x['direction']} | {x['strength']} | {x['speed']} | {x.get('ref', '')} |")
    if m.get("backtests"):
        L.append("\n**Suggested backtests** (run by app against daily returns)\n")
        L.append("| Factor | Series | Provider | Frequency | Lookback | Hypothesis |\n|---|---|---|---|---|---|")
        for b in m["backtests"]:
            L.append(f"| {b['factor']} | {b['series']} | {b['provider']} | {b.get('frequency', 'weekly')} | {b.get('lookback', '5y')} | {b['hypothesis']} |")
    if m.get("proposed_factors"):
        L.append("\n**Proposed new macro factors** (not on fixed list — approve before tracking)\n")
        L.append("| Code | Name | Series | Provider | Scope | Other names affected | Why |\n|---|---|---|---|---|---|---|")
        for f in m["proposed_factors"]:
            L.append(f"| {f['code']} | {f['name']} | {f['series']} | {f['provider']} | {f['scope']} | "
                     f"{', '.join(f.get('other_names', [])) or '—'} | {f['rationale']} |")
    else:
        L.append("\n**Proposed new macro factors:** none — fixed list covers this name.")
    # Levers
    if m.get("levers"):
        L.append("\n## 7. Lever register")
        L.append("| Base | Lever | Exposure | Speed | Rising = | Factor | Watch metric | Current | Pushes LOW | Pushes HIGH |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for l in m["levers"]:
            exp = l["exposure"] + (f" ({l['exposure_pct']:g}%)" if l.get("exposure_pct") is not None else "")
            L.append(f"| {l['base']} | {l['lever_name']} | {exp} | {l['speed']} | {l.get('direction') or 'split'} | "
                     f"{l.get('macro_factor_code') or '—'} | {l.get('watch_metric', '')} | {l.get('current_reading', '')} | "
                     f"{l.get('pushes_low', '')} | {l.get('pushes_high', '')} |")
    sc_s = m["scorecard_suggested"]
    L.append("\n## 8. Scorecard — suggested starting point (yours to overwrite in the app)")
    L.append("| Dimension | Score (1–5) | Basis |\n|---|---|---|")
    for k in ["growth", "value", "income"]:
        L.append(f"| {k.title()} | {sc_s[k]['score']} | {sc_s[k]['ref']} |")
    for k, lbl in [("bull_catalysts", "Bull"), ("bear_catalysts", "Bear")]:
        L.append(f"\n**{lbl} catalysts**")
        for c in sc_s[k]:
            L.append(f"- {c['text']}" + (f" ({c['date']})" if c.get("date") else ""))
    if m.get("bottom_line"):
        L.append("\n## 9. Bottom line\n" + m["bottom_line"])
    L.append("\n## Model (parsed by webapp — do not edit by hand; regenerate with model.py)")
    L.append("```json stock-model\n" + json.dumps(m, indent=1) + "\n```")
    L.append("\n*Model figures; verify against primary sources. No buy/sell call.*")
    return "\n".join(L) + "\n"

def run(inputs):
    """Pure entry point for the webapp: validate + compute, no file I/O.
    Returns (model_with_outputs or None, errors, warnings)."""
    errors.clear(); warnings.clear(); PROPOSED.clear()
    validate(inputs)
    if errors: return None, list(errors), list(warnings)
    m = copy.deepcopy(inputs); m["schema_version"] = 2; m["outputs"] = compute(m)
    return m, [], list(warnings)

def main():
    src, dst = sys.argv[1], sys.argv[2]
    m = json.load(open(src))
    validate(m)
    for w in warnings: print("WARN:", w)
    if errors:
        for e in errors: print("ERROR:", e)
        sys.exit(1)
    m = copy.deepcopy(m)
    m["schema_version"] = 2
    m["outputs"] = compute(m)
    open(dst, "w").write(render(m))
    for k in ["low", "bau", "high"]:
        print(k.upper(), " ".join(f"{r['year']}: rev {r['revenue']:,.0f} ({r['revenue_growth_pct']:+.1f}%) "
                                  f"EPS {r['eps']:.2f}" for r in m["outputs"]["scenarios"][k]))
    print("wrote", dst)

if __name__ == "__main__":
    main()
