import datetime as dt
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.deps import CurrentUser, get_current_user
from app.services import dividends, scorecard, workspace

router = APIRouter()


class Catalyst(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    date: dt.date | None = None
    status: Literal["open", "hit", "missed"] = "open"


class ScorecardIn(BaseModel):
    growth: int = Field(ge=0, le=3)
    value: int = Field(ge=0, le=3)
    income: int = Field(ge=0, le=3)
    macro: int | None = Field(default=None, ge=0, le=3)  # no longer scored in the UI; the screener's macro net covers it
    bull_catalysts: list[Catalyst] = []
    bear_catalysts: list[Catalyst] = []
    note: str | None = None
    target_pe: float | None = Field(default=None, gt=0, le=1000)
    target_pe_note: str | None = Field(default=None, max_length=2000)


class DividendIn(BaseModel):
    mode: Literal["per_payment", "half", "annual", "uneven"]
    amount: float | None = Field(default=None, ge=0)
    frequency: Literal[1, 2, 4, 12] | None = None
    payments: list[float] = []


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


@router.get("/analysis/{ticker}/dividend")
def get_dividend(ticker: str, user: CurrentUser = Depends(get_current_user)) -> dict:
    """Your dividend input (null until set), its annual total, and Yahoo's trailing 12 months for reference."""
    try:
        return dividends.get_dividend(user.db, user.id, ticker)
    except workspace.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/analysis/{ticker}/dividend")
def save_dividend(ticker: str, body: DividendIn, user: CurrentUser = Depends(get_current_user)) -> dict:
    try:
        return dividends.save_dividend(user.db, user.id, ticker, body.model_dump())
    except workspace.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/analysis/{ticker}/dividend")
def clear_dividend(ticker: str, user: CurrentUser = Depends(get_current_user)) -> dict:
    try:
        return dividends.clear_dividend(user.db, user.id, ticker)
    except workspace.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
