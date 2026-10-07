from fastapi import APIRouter, Depends

from app.crypto import get_t212_credentials
from app.deps import CurrentUser, get_current_user
from app.services import market_data, t212_client

router = APIRouter()


@router.post("/market/refresh")
def refresh_market(user: CurrentUser = Depends(get_current_user)) -> dict:
    """Map held positions to instruments, then refresh any price/FX older than 15 minutes."""
    warnings = []
    api_key, api_secret = get_t212_credentials(user.db, user.id)
    if api_key:
        try:
            positions = t212_client.get_positions(api_key, api_secret or "")
            market_data.sync_instruments(user.db, [p["ticker"] for p in positions if p.get("ticker")])
        except t212_client.T212Error as e:
            warnings.append(f"Trading212 positions not synced: {e}")
    else:
        warnings.append("No Trading212 credentials; only existing instruments refreshed.")

    summary = market_data.refresh_market_data(user.db)
    summary["warnings"] = warnings
    return summary
