import base64
import threading
import time

import requests

BASE_URL = "https://live.trading212.com"


class T212Error(Exception):
    pass


def _headers(api_key: str, api_secret: str) -> dict:
    encoded = base64.b64encode(f"{api_key}:{api_secret or ''}".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


# T212 rate-limits these endpoints to roughly one call per few seconds. Book load and the
# market refresh both need positions (and React dev mode fires effects twice), so responses
# are shared for CACHE_TTL; the per-key lock makes concurrent callers wait for one fetch.
CACHE_TTL = 10.0
_cache: dict[tuple[str, str], tuple[float, object]] = {}
_locks: dict[tuple[str, str], threading.Lock] = {}
_locks_guard = threading.Lock()


def _cached_get(path: str, api_key: str, api_secret: str, label: str):
    key = (path, api_key)
    with _locks_guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:
        hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_TTL:
            return hit[1]
        resp = requests.get(f"{BASE_URL}{path}", headers=_headers(api_key, api_secret), timeout=10)
        if not resp.ok:
            raise T212Error(f"T212 {label} API error {resp.status_code}: {resp.text}")
        data = resp.json()
        _cache[key] = (time.monotonic(), data)
        return data


def get_cash(api_key: str, api_secret: str) -> dict:
    return _cached_get("/api/v0/equity/account/cash", api_key, api_secret, "cash")


def get_positions(api_key: str, api_secret: str) -> list[dict]:
    return _cached_get("/api/v0/equity/portfolio", api_key, api_secret, "portfolio")


def get_history_page(api_key: str, api_secret: str, path: str) -> tuple[dict, dict]:
    """One page of transaction history, uncached: (body, response headers). Headers carry the rate-limit state."""
    resp = requests.get(f"{BASE_URL}{path}", headers=_headers(api_key, api_secret), timeout=20)
    if not resp.ok:
        raise T212Error(f"T212 history API error {resp.status_code}: {resp.text}")
    return resp.json(), {k.lower(): v for k, v in resp.headers.items()}


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
