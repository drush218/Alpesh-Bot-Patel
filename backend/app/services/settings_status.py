"""What Settings shows: credentials, analyses on file, pipeline freshness, factor proposals."""

from datetime import datetime, timezone

from supabase import Client

from app.crypto import get_t212_credentials
from app.services import expected_move, t212_client
from app.services.index_map import index_for_ticker
from app.services.analysis_view import staleness
from app.services.market_data import parse_t212_ticker


def status(db: Client, user_id: str) -> dict:
    api_key, _ = get_t212_credentials(db, user_id)
    out: dict = {
        "credentials": {"saved": bool(api_key), "key_hint": f"…{api_key[-4:]}" if api_key and len(api_key) > 4 else None},
        "warnings": [],
    }

    current = db.table("analyses").select("id, instrument_id, model, data_as_of, created_at, warnings, instruments(ticker, company)").eq("is_current", True).execute().data
    stale = {r["id"]: staleness(r["model"], r.get("data_as_of")) for r in current}
    analyses = sorted(({
        "ticker": r["instruments"]["ticker"],
        "company": r["instruments"].get("company"),
        "data_as_of": r.get("data_as_of"),
        "ingested_at": r.get("created_at"),
        "warning_count": len(r.get("warnings") or []),
        "is_stale": bool(stale.get(r["id"], {}).get("is_stale")),
        "last_earnings": stale.get(r["id"], {}).get("last_earnings"),
    } for r in current), key=lambda a: a["ticker"])
    out["analyses"] = analyses

    held: list[str] = []
    out["model"] = []
    if api_key:
        _, secret = get_t212_credentials(db, user_id)
        try:
            positions = t212_client.get_positions(api_key, secret or "")
            held = sorted({parse_t212_ticker(p["ticker"])[0] for p in positions if p.get("ticker")})
            fits = expected_move.explain_holdings([
                {"ticker": t, "yahoo": parse_t212_ticker(p["ticker"])[1], "index": index_for_ticker(t)}
                for p in positions for t in [parse_t212_ticker(p["ticker"])[0]]
            ])
            out["model"] = sorted(({
                "ticker": t, "index": (m or {}).get("index_code"), "beta": (m or {}).get("betas", {}).get("index"),
                "r2": (m or {}).get("r2"), "n": (m or {}).get("n"), "fit_from": (m or {}).get("fit_from"),
                "fit_to": (m or {}).get("fit_to"), "sigma_pct": (m or {}).get("sigma_pct"),
            } for t, m in fits.items()), key=lambda r: r["ticker"])
        except t212_client.T212Error as e:
            out["warnings"].append(f"Couldn't read holdings from Trading212: {e}")
    modelled = {a["ticker"] for a in analyses}
    out["holdings"] = {"count": len(held), "modelled": sum(t in modelled for t in held),
                       "without_analysis": [t for t in held if t not in modelled]}
    dated = [a["data_as_of"] for a in analyses if a["data_as_of"]]
    out["oldest_strike"] = min(dated) if dated else None

    prices = db.table("prices").select("fetched_at").execute().data
    instruments = db.table("instruments").select("ticker, yahoo_symbol").execute().data
    out["prices"] = {
        "last_fetched": max((p["fetched_at"] for p in prices), default=None),
        "unmapped": sorted(i["ticker"] for i in instruments if not i.get("yahoo_symbol")),
    }

    ds = db.table("user_settings").select("deposit_stats_cached_at").eq("id", user_id).execute().data
    out["deposits_cached_at"] = ds[0].get("deposit_stats_cached_at") if ds else None

    out["proposals"] = sorted(
        db.table("macro_factor_proposals").select("code, name, series, provider, scope, rationale, proposed_by_tickers, status").eq("status", "pending").execute().data,
        key=lambda p: p["code"],
    )
    return out


class ProposalNotFound(LookupError):
    pass


def decide_proposal(db: Client, code: str, approve: bool) -> None:
    rows = db.table("macro_factor_proposals").select("*").eq("code", code).execute().data
    if not rows:
        raise ProposalNotFound(code)
    p = rows[0]
    if approve:
        db.table("macro_factors").upsert({
            "code": code, "name": p.get("name") or code, "series": p.get("series"),
            "provider": p.get("provider"), "scope": p.get("scope") or "company",
        }, on_conflict="code").execute()
    db.table("macro_factor_proposals").update({
        "status": "approved" if approve else "rejected",
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }).eq("code", code).execute()
