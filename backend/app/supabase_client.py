from functools import lru_cache

from supabase import create_client, Client

from app.config import settings


@lru_cache
def get_supabase() -> Client:
    """Anonymous client. Only for auth calls; table access goes through user_client() so RLS sees the user."""
    return create_client(settings.supabase_url, settings.supabase_key)


def user_client(access_token: str) -> Client:
    """Client that queries as the logged-in user (RLS policies use auth.uid())."""
    client = create_client(settings.supabase_url, settings.supabase_key)
    client.postgrest.auth(access_token)
    return client
