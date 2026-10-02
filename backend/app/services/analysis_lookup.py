from supabase import Client


def modelled_tickers(supabase: Client) -> set[str]:
    """Tickers with a current (is_current=true) analysis on file."""
    try:
        resp = supabase.table("analyses").select("instruments(ticker)").eq("is_current", True).execute()
        return {row["instruments"]["ticker"] for row in (resp.data or [])}
    except Exception:
        return set()
