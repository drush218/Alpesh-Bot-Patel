"""Net deposited and first-deposit date, ported from pages/1_My_Portfolio.py.

T212 has no deposits endpoint, so every transaction page is scanned client-side (newest
first). Results are cached in user_settings, shared with the Streamlit app. When the cache
is over a day old only the pages newer than last_tx_fetched_at are scanned and the delta
is added to the stored total.

The dated net flows (one entry per day) are cached too, so the Dashboard can show a
money-weighted return (XIRR) instead of treating every deposit as made on day one. A cache
written before flows existed triggers one full rescan.
"""

import time
from datetime import date, datetime, timedelta, timezone

from supabase import Client

from app.services import t212_client

STALE_AFTER = timedelta(hours=24)
MIN_DEPOSIT = 5.0   # interest on cash arrives as small DEPOSITs
HISTORY_PATH = "/api/v0/equity/history/transactions"
_COLUMNS = "deposit_total, first_deposit_date, deposit_stats_cached_at, last_tx_fetched_at, deposit_flows"


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def load_cached(db: Client, user_id: str) -> dict | None:
    rows = db.table("user_settings").select(_COLUMNS).eq("id", user_id).execute().data
    row = rows[0] if rows else None
    if not row or not row.get("deposit_stats_cached_at"):
        return None
    return {
        "total_deposited": float(row["deposit_total"] or 0),
        "first_deposit_date": row.get("first_deposit_date") or None,
        "cached_at": row["deposit_stats_cached_at"],
        "last_tx_fetched_at": row.get("last_tx_fetched_at"),
        "flows": row.get("deposit_flows"),   # {"YYYY-MM-DD": net GBP in}; None on caches from before flows
    }


def scan_page(items: list[dict], since: datetime | None, flows: dict[str, float] | None = None) -> tuple[float, str | None, bool]:
    """Net deposit delta and earliest funding date on one page; done=True once we reach `since`.
    Adds each counted transaction to `flows` by day when given."""
    net, first = 0.0, None
    for tx in items:
        when = tx.get("dateTime", "")
        if since and when and _parse(when) <= since:
            return net, first, True
        kind, amount = tx.get("type", ""), float(tx.get("amount", 0))
        if kind == "DEPOSIT" and amount >= MIN_DEPOSIT:
            delta = amount
        elif kind == "WITHDRAW":
            delta = -abs(amount)
        elif kind == "TRANSFER":
            delta = amount   # signed: positive in, negative out
        else:
            delta = None
        if delta is not None:
            net += delta
            if flows is not None and when:
                day = when[:10]
                flows[day] = round(flows.get(day, 0.0) + delta, 2)
        if kind in ("DEPOSIT", "WITHDRAW", "TRANSFER") and when and (first is None or when < first):
            first = when
    return net, first, False


def _next_path(raw: str | None) -> str | None:
    if not raw:
        return None
    return raw if raw.startswith("/") else f"{HISTORY_PATH}?{raw}"


def _wait_for_rate_limit(headers: dict, sleep) -> None:
    if int(headers.get("x-ratelimit-remaining", 1)) <= 1:
        reset_at = int(headers.get("x-ratelimit-reset", 0))
        sleep(max(0, reset_at - time.time()) + 0.5)
    else:
        sleep(0.2)


def get_deposit_stats(db: Client, user_id: str, api_key: str, api_secret: str,
                      now: datetime | None = None, fetch_page=t212_client.get_history_page,
                      sleep=time.sleep) -> dict | None:
    """Cached stats, refreshed from T212 when over a day old. Falls back to the stale cache on T212 errors."""
    now = now or datetime.now(timezone.utc)
    cached = load_cached(db, user_id)
    if cached and cached.get("flows") is not None and now - _parse(cached["cached_at"]) < STALE_AFTER:
        return cached

    # Incremental only when the cache already holds dated flows; older caches get one full rescan.
    since = _parse(cached["last_tx_fetched_at"]) if cached and cached.get("flows") is not None else None
    total = cached["total_deposited"] if since else 0.0
    first = cached["first_deposit_date"] if since else None
    flows: dict[str, float] = dict(cached["flows"]) if since else {}

    path = f"{HISTORY_PATH}?limit=50"
    try:
        while path:
            data, headers = fetch_page(api_key, api_secret, path)
            net, page_first, done = scan_page(data.get("items", []), since, flows)
            total += net
            if page_first and (first is None or page_first < first):
                first = page_first
            path = None if done else _next_path(data.get("nextPagePath"))
            if path:
                _wait_for_rate_limit(headers, sleep)
    except t212_client.T212Error:
        if cached:
            return cached
        raise

    stats = {
        "total_deposited": total,
        "first_deposit_date": first,
        "cached_at": now.isoformat(),
        "last_tx_fetched_at": now.isoformat(),
        "flows": flows,
    }
    db.table("user_settings").upsert({
        "id": user_id,
        "deposit_total": total,
        "first_deposit_date": first or "",
        "deposit_stats_cached_at": stats["cached_at"],
        "last_tx_fetched_at": stats["last_tx_fetched_at"],
        "deposit_flows": flows,
    }, on_conflict="id").execute()
    return stats


def years_since(first_deposit_date: str | None, now: datetime | None = None) -> float | None:
    start = _parse(first_deposit_date)
    if not start:
        return None
    years = ((now or datetime.now(timezone.utc)) - start).days / 365.25
    return years if years > 0 else None


def cagr_pct(end_value: float, start_value: float, years: float | None) -> float | None:
    if not years or start_value <= 0 or end_value <= 0:
        return None
    return ((end_value / start_value) ** (1 / years) - 1) * 100


def xirr_pct(flows: dict[str, float], end_value: float, end: date | None = None) -> float | None:
    """Money-weighted annual return: the rate at which the dated deposits (net of withdrawals)
    grow to end_value today. Solved by bisection; None when there's nothing to solve."""
    end = end or date.today()
    dated = sorted((date.fromisoformat(d), amt) for d, amt in flows.items() if amt)
    if not dated or end_value <= 0 or sum(a for _, a in dated) <= 0:
        return None
    start = dated[0][0]
    if (end - start).days < 1:
        return None

    def value_at(rate: float) -> float:
        # What the deposits would be worth today at `rate`, minus what the account is worth.
        return sum(a * (1 + rate) ** ((end - d).days / 365.25) for d, a in dated) - end_value

    lo, hi = -0.9999, 100.0
    if value_at(lo) > 0 or value_at(hi) < 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if value_at(mid) > 0:
            hi = mid
        else:
            lo = mid
        if hi - lo < 1e-9:
            break
    return (lo + hi) / 2 * 100
