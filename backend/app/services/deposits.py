"""Net deposited and first-deposit date, ported from pages/1_My_Portfolio.py.

T212 has no deposits endpoint, so every transaction page is scanned client-side (newest
first). Results are cached in user_settings, shared with the Streamlit app. When the cache
is over a day old only the pages newer than last_tx_fetched_at are scanned and the delta
is added to the stored total.
"""

import time
from datetime import datetime, timedelta, timezone

from supabase import Client

from app.services import t212_client

STALE_AFTER = timedelta(hours=24)
MIN_DEPOSIT = 5.0   # interest on cash arrives as small DEPOSITs
HISTORY_PATH = "/api/v0/equity/history/transactions"
_COLUMNS = "deposit_total, first_deposit_date, deposit_stats_cached_at, last_tx_fetched_at"


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
    }


def scan_page(items: list[dict], since: datetime | None) -> tuple[float, str | None, bool]:
    """Net deposit delta and earliest funding date on one page; done=True once we reach `since`."""
    net, first = 0.0, None
    for tx in items:
        when = tx.get("dateTime", "")
        if since and when and _parse(when) <= since:
            return net, first, True
        kind, amount = tx.get("type", ""), float(tx.get("amount", 0))
        if kind == "DEPOSIT" and amount >= MIN_DEPOSIT:
            net += amount
        elif kind == "WITHDRAW":
            net -= abs(amount)
        elif kind == "TRANSFER":
            net += amount   # signed: positive in, negative out
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
    if cached and now - _parse(cached["cached_at"]) < STALE_AFTER:
        return cached

    since = _parse(cached["last_tx_fetched_at"]) if cached else None
    total = cached["total_deposited"] if since else 0.0
    first = cached["first_deposit_date"] if since else None

    path = f"{HISTORY_PATH}?limit=50"
    try:
        while path:
            data, headers = fetch_page(api_key, api_secret, path)
            net, page_first, done = scan_page(data.get("items", []), since)
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
    }
    db.table("user_settings").upsert({
        "id": user_id,
        "deposit_total": total,
        "first_deposit_date": first or "",
        "deposit_stats_cached_at": stats["cached_at"],
        "last_tx_fetched_at": stats["last_tx_fetched_at"],
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
