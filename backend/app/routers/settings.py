from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.crypto import save_t212_credentials
from app.deps import CurrentUser, get_current_user
from app.services import ingest, settings_status

router = APIRouter()


class Credentials(BaseModel):
    api_key: str = Field(min_length=1)
    api_secret: str = ""


class AnalysisFile(BaseModel):
    markdown: str = Field(min_length=1)
    filename: str | None = None


@router.get("/settings/status")
def get_status(user: CurrentUser = Depends(get_current_user)) -> dict:
    return settings_status.status(user.db, user.id)


@router.post("/settings/t212", status_code=204)
def set_credentials(body: Credentials, user: CurrentUser = Depends(get_current_user)) -> None:
    """Encrypt and store Trading212 credentials. They are never sent back to the browser."""
    save_t212_credentials(user.db, user.id, body.api_key.strip(), body.api_secret.strip())


@router.post("/analyses/preview")
def preview_analysis(body: AnalysisFile, user: CurrentUser = Depends(get_current_user)) -> dict:
    """Parse an analysis file and say what storing it would do. Writes nothing."""
    return ingest.preview(user.db, body.markdown, body.filename)


@router.post("/analyses")
def store_analysis(body: AnalysisFile, user: CurrentUser = Depends(get_current_user)) -> dict:
    """Store an analysis as the ticker's current one (a byte-identical file is not duplicated)."""
    try:
        return ingest.store(user.db, body.markdown, body.filename)
    except ingest.IngestError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/factors/proposals/{code}/{decision}", status_code=204)
def decide(code: str, decision: str, user: CurrentUser = Depends(get_current_user)) -> None:
    if decision not in ("approve", "reject"):
        raise HTTPException(status_code=404, detail="Use approve or reject")
    try:
        settings_status.decide_proposal(user.db, code, decision == "approve")
    except settings_status.ProposalNotFound:
        raise HTTPException(status_code=404, detail=f"No proposal {code}")
