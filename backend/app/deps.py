from fastapi import Header, HTTPException

from app.supabase_client import get_supabase


def get_current_user_id(authorization: str = Header(...)) -> str:
    """Verify the Supabase access token and return the user id.

    Uses supabase.auth.get_user() (a network call to Supabase Auth) rather than
    local JWT decoding, since this project uses Supabase's newer publishable-key
    format and we can't assume a legacy HS256 JWT secret is available. Latency
    is not a concern for a single-user app.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()

    try:
        resp = get_supabase().auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if not resp or not resp.user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return resp.user.id
