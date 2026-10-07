from fastapi import APIRouter, Depends

from app.deps import CurrentUser, get_current_user
from app.services import macro_data, macro_view

router = APIRouter()


@router.get("/macro")
def get_macro(user: CurrentUser = Depends(get_current_user)) -> dict:
    """Factor cards, per-holding factor effects and the book tilt."""
    return macro_view.macro_view(user.db, user.id)


@router.post("/macro/refresh")
def refresh(user: CurrentUser = Depends(get_current_user)) -> dict:
    """Pull factor series from FRED; each factor at most once a day per server process."""
    return macro_data.refresh_macro(user.db)
