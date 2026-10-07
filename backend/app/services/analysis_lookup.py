from app.supabase_client import get_supabase


def modelled_tickers() -> set[str]:
    """Tickers with a current (is_current=true) analysis on file."""
    supabase = get_supabase()
    try:
        resp = supabase.table("analyses").select("ticker").eq("is_current", True).execute()
        return {row["ticker"] for row in (resp.data or [])}
    except Exception:
        return set()
