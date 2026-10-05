from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.deps import CurrentUser, get_current_user
from app.services import scenarios, workspace
from app.services.analysis_lookup import modelled_tickers

router = APIRouter()


class Edit(BaseModel):
    path: str
    value: float | int | str | bool | None


class PreviewRequest(BaseModel):
    overrides: list[Edit] = []


class SaveRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    note: str | None = None
    overrides: list[Edit]


def _not_found(e: workspace.NotFound):
    raise HTTPException(status_code=404, detail=str(e))


@router.get("/analysis")
def list_analysed(user: CurrentUser = Depends(get_current_user)) -> list[str]:
    """Tickers that have a current analysis, for the Analysis nav."""
    return sorted(modelled_tickers(user.db))


@router.post("/analysis/{ticker}/workspace")
def preview(ticker: str, body: PreviewRequest, user: CurrentUser = Depends(get_current_user)) -> dict:
    """Model outputs for the current analysis with unsaved edits applied, next to the base outputs."""
    try:
        return workspace.preview(user.db, ticker, [e.model_dump() for e in body.overrides])
    except workspace.NotFound as e:
        _not_found(e)


@router.get("/analysis/{ticker}/scenarios")
def list_scenarios(ticker: str, user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    try:
        return workspace.list_scenarios(user.db, user.id, ticker)
    except workspace.NotFound as e:
        _not_found(e)


@router.post("/analysis/{ticker}/scenarios")
def save_scenario(ticker: str, body: SaveRequest, user: CurrentUser = Depends(get_current_user)) -> dict:
    """Create the named scenario, or replace it (and move it onto the current base) if the name exists."""
    try:
        return workspace.save_scenario(user.db, user.id, ticker, body.name, body.note,
                                       [e.model_dump() for e in body.overrides])
    except workspace.NotFound as e:
        _not_found(e)
    except scenarios.PathError as e:
        raise HTTPException(status_code=400, detail=f"Not an input in the current analysis: {e.args[0]}")


@router.get("/analysis/{ticker}/scenarios/{scenario_id}")
def load_scenario(ticker: str, scenario_id: int, user: CurrentUser = Depends(get_current_user)) -> dict:
    try:
        return workspace.load_scenario(user.db, user.id, ticker, scenario_id)
    except workspace.NotFound as e:
        _not_found(e)


@router.delete("/analysis/{ticker}/scenarios/{scenario_id}", status_code=204)
def delete_scenario(ticker: str, scenario_id: int, user: CurrentUser = Depends(get_current_user)) -> None:
    try:
        workspace.delete_scenario(user.db, user.id, ticker, scenario_id)
    except workspace.NotFound as e:
        _not_found(e)
