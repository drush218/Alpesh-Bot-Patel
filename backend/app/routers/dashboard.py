from fastapi import APIRouter, Depends

from app.deps import CurrentUser, get_current_user
from app.services import dashboard

router = APIRouter()


@router.get("/dashboard")
def get_dashboard(user: CurrentUser = Depends(get_current_user)) -> dict:
    """Tile data: Book day move, Macro read, Analysis subject, Indices, Calendar + dividends."""
    return dashboard.dashboard(user.db, user.id)
