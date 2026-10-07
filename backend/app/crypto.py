import logging
from functools import lru_cache

from cryptography.fernet import Fernet

from app.config import settings
from app.supabase_client import get_supabase

logger = logging.getLogger(__name__)


@lru_cache
def _fernet() -> Fernet:
    key = settings.fernet_key
    return Fernet(key.encode() if isinstance(key, str) else key)


def get_t212_credentials(user_id: str) -> tuple[str | None, str | None]:
    """Return decrypted (api_key, api_secret) or (None, None) if not saved."""
    supabase = get_supabase()
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
        logger.exception("Failed to load T212 credentials for user %s", user_id)
        return None, None
