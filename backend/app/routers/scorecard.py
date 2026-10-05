import datetime as dt
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.deps import CurrentUser, get_current_user
from app.services import scorecard, workspace

router = APIRouter()


class Catalyst(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    date: dt.date | None = None
    status: Literal["open", "hit", "missed"] = "open"


class ScorecardIn(BaseModel):
    growth: int = Field(ge=1, le=5)
    value: int = Field(ge=1, le=5)
    income: int = Field(ge=1, le=5)
    bull_catalysts: list[Catalyst] = []
    bear_catalysts: list[Catalyst] = []
    note: str | None = None


@router.get("/analysis/{ticker}/scorecard")
def get_scorecard(ticker: str, user: CurrentUser = Depends(get_current_user)) -> dict:
    """Your current scorecard (null until first save), how many versions exist, and Claude's suggestion."""
    try:
        return scorecard.get_scorecard(user.db, user.id, ticker)
    except workspace.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/analysis/{ticker}/scorecard")
def save_scorecard(ticker: str, body: ScorecardIn, user: CurrentUser = Depends(get_current_user)) -> dict:
    """Save a new version; earlier versions are kept."""
    try:
        return scorecard.save_scorecard(user.db, user.id, ticker, body.model_dump(mode="json"))
    except workspace.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
