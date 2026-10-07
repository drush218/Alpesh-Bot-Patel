import logging
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from supabase import Client

from app.supabase_client import get_supabase, user_client

logger = logging.getLogger("uvicorn.error")


def _bearer_token(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return authorization.removeprefix("Bearer ").strip()


def get_current_user_id(token: str = Depends(_bearer_token)) -> str:
    """Verify the Supabase access token and return the user id.

    Uses supabase.auth.get_user() (a network call to Supabase Auth) rather than
    local JWT decoding, since this project uses Supabase's newer publishable-key
    format and we can't assume a legacy HS256 JWT secret is available. Latency
    is not a concern for a single-user app.
    """
    try:
        resp = get_supabase().auth.get_user(token)
    except Exception as e:
        logger.warning("Token rejected: %s: %s", type(e).__name__, e)
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if not resp or not resp.user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return resp.user.id


@dataclass
class CurrentUser:
    id: str
    db: Client   # queries run as this user, so RLS applies


def get_current_user(
    token: str = Depends(_bearer_token),
    user_id: str = Depends(get_current_user_id),
) -> CurrentUser:
    return CurrentUser(id=user_id, db=user_client(token))
