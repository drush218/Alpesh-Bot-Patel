import base64

import requests

BASE_URL = "https://live.trading212.com"


class T212Error(Exception):
    pass


def _headers(api_key: str, api_secret: str) -> dict:
    encoded = base64.b64encode(f"{api_key}:{api_secret or ''}".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


def get_cash(api_key: str, api_secret: str) -> dict:
    resp = requests.get(f"{BASE_URL}/api/v0/equity/account/cash", headers=_headers(api_key, api_secret), timeout=10)
    if not resp.ok:
        raise T212Error(f"T212 cash API error {resp.status_code}: {resp.text}")
    return resp.json()


def get_positions(api_key: str, api_secret: str) -> list[dict]:
    resp = requests.get(f"{BASE_URL}/api/v0/equity/portfolio", headers=_headers(api_key, api_secret), timeout=10)
    if not resp.ok:
        raise T212Error(f"T212 portfolio API error {resp.status_code}: {resp.text}")
    return resp.json()


def derive_position_gbp(position: dict) -> dict:
    """Apply the same FX-derivation math as pages/1_My_Portfolio.py.

    T212 doesn't expose the FX rate directly, so it's backed out from the
    relationship between total P&L (ppl) and its FX component (fxPpl):
    ppl - fxPpl = price-movement P&L at the current FX rate, in GBP.
    """
    qty = float(position.get("quantity") or 0)
    avg_price = float(position.get("averagePrice") or 0)
    curr_price = float(position.get("currentPrice") or 0)
    pos_ppl = float(position.get("ppl") or 0)
    fx_ppl = float(position.get("fxPpl") or 0)

    price_pnl_local = (curr_price - avg_price) * qty
    if abs(price_pnl_local) > 0.0001:
        fx_rate = (pos_ppl - fx_ppl) / price_pnl_local
    else:
        fx_rate = 1.0

    value_gbp = qty * curr_price * fx_rate
    cost_gbp = qty * avg_price * fx_rate
    ppl_pct = (pos_ppl / cost_gbp * 100) if cost_gbp else 0.0

    return {
        "ticker": position.get("ticker", ""),
        "quantity": qty,
        "avg_price": avg_price,
        "curr_price": curr_price,
        "cost_gbp": cost_gbp,
        "value_gbp": value_gbp,
        "ppl_gbp": pos_ppl,
        "ppl_pct": ppl_pct,
    }
