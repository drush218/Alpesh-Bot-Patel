from fastapi import APIRouter, Depends, Query

from app.deps import CurrentUser, get_current_user
from app.services import sizer

router = APIRouter()


@router.get("/sizer/context")
def context(ticker: str = Query(min_length=1, max_length=20), user: CurrentUser = Depends(get_current_user)) -> dict:
    """Live price in native currency + GBP rate, conservative book value, holding, analysis band."""
    return sizer.sizer_context(user.db, user.id, ticker)
