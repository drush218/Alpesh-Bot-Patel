from functools import lru_cache

from cryptography.fernet import Fernet

from supabase import Client

from app.config import settings


@lru_cache
def _fernet() -> Fernet:
    key = settings.fernet_key
    return Fernet(key.encode() if isinstance(key, str) else key)


def get_t212_credentials(supabase: Client, user_id: str) -> tuple[str | None, str | None]:
    """Return decrypted (api_key, api_secret) or (None, None) if not saved. supabase must be a user client."""
    f = _fernet()

    try:
        row = (
            supabase.table("user_settings")
            .select("t212_api_key, t212_api_secret")
            .eq("id", user_id)
            .single()
            .execute()
        )
        data = row.data
        if not data or not data.get("t212_api_key"):
            return None, None

        api_key = f.decrypt(data["t212_api_key"].encode()).decode()
        api_secret = (
            f.decrypt(data["t212_api_secret"].encode()).decode()
            if data.get("t212_api_secret")
            else None
        )
        return api_key, api_secret
    except Exception:
        return None, None


def save_t212_credentials(supabase: Client, user_id: str, api_key: str, api_secret: str) -> None:
    """Encrypt and upsert Trading212 credentials (same format as the Streamlit app). supabase must be a user client."""
    f = _fernet()
    supabase.table("user_settings").upsert({
        "id": user_id,
        "t212_api_key": f.encrypt(api_key.encode()).decode(),
        "t212_api_secret": f.encrypt(api_secret.encode()).decode(),
    }, on_conflict="id").execute()
