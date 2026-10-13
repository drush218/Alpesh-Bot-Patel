"""Base-year actuals: the analysis's last reported year, calculated like a forecast year.

The json block may carry an "actuals" object for meta.base_year:

    "actuals": {
      "operating_margin": {"pct": 8.4, "source": "filing", "ref": "..."},
      "net_interest":     {"value": -20.1, "source": "filing", "ref": "..."},
      "tax_rate":         {"pct": 25.6, "source": "filing", "ref": "..."},
      "nci_pct":          {"pct": 0.0, ...},          # optional, as for the forecast years
      "reported_eps":     {"value": 1.10, ...}        # the company's own figure, a check only
    }

Revenue (segment bases) and shares (shares.base_diluted) are already in the inputs. Net income
and EPS are computed the same way stock_model computes a forecast year, so current PE is on the
same basis as forward PE. The engine ignores the block; it's carried through ingest untouched.
"""

FIELDS = (("operating_margin", "pct"), ("net_interest", "value"), ("tax_rate", "pct"),
          ("nci_pct", "pct"), ("reported_eps", "value"))

EPS_CHECK_PCT = 2.0  # flag when our EPS differs from the reported figure by more than this


def with_skeleton(inputs: dict) -> dict:
    """Fill missing actuals fields with nulls so the workspace can address and edit them."""
    actuals = inputs.setdefault("actuals", {})
    for name, key in FIELDS:
        actuals.setdefault(name, {key: None})
    return inputs


def strip_empty(inputs: dict) -> dict:
    """Drop null skeleton fields before writing the json block back."""
    keys = dict(FIELDS)
    actuals = {k: v for k, v in (inputs.get("actuals") or {}).items()
               if not (k in keys and isinstance(v, dict) and v.get(keys[k]) is None)}
    if actuals:
        inputs["actuals"] = actuals
    else:
        inputs.pop("actuals", None)
    return inputs


def _num(actuals: dict, name: str, key: str):
    v = (actuals.get(name) or {}).get(key)
    return float(v) if v is not None else None


def compute(inputs: dict) -> dict:
    """{"year", "revenue", "shares", "operating_margin_pct", "costs", "net_income", "eps",
    "reported_eps", "eps_check_pct"}; income lines are None until margin, interest and tax are set."""
    revenue = sum(s["base"] for s in inputs["revenue"]["segments"])
    shares = inputs["shares"]["base_diluted"]
    a = inputs.get("actuals") or {}
    margin, interest, tax_rate = _num(a, "operating_margin", "pct"), _num(a, "net_interest", "value"), _num(a, "tax_rate", "pct")
    nci_pct = _num(a, "nci_pct", "pct") or 0.0
    reported = _num(a, "reported_eps", "value")
    out = {"year": inputs.get("meta", {}).get("base_year"), "revenue": revenue, "shares": shares,
           "operating_margin_pct": margin, "costs": None, "net_income": None, "eps": None,
           "reported_eps": reported, "eps_check_pct": None}
    if margin is not None:
        out["costs"] = revenue * (1 - margin / 100)
    if margin is None or interest is None or tax_rate is None:
        return out
    pretax = revenue * margin / 100 + interest
    ni = pretax - (pretax * tax_rate / 100 if pretax > 0 else 0.0)
    ni_attr = ni * (1 - nci_pct / 100)
    out["net_income"] = ni_attr
    out["eps"] = ni_attr / shares if shares else None
    if out["eps"] is not None and reported:
        out["eps_check_pct"] = (out["eps"] / reported - 1) * 100
    return out
