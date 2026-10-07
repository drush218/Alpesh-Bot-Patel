from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import account, book, market, scenarios, scorecard, settings as settings_router, macro, dashboard, sizer

app = FastAPI(title="Portfolio Terminal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(account.router, prefix="/api")
app.include_router(book.router, prefix="/api")
app.include_router(market.router, prefix="/api")
app.include_router(scenarios.router, prefix="/api")
app.include_router(scorecard.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(macro.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(sizer.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


# In production (Docker / Render) the built React app is served from the same origin, so the
# frontend calls /api/... with no CORS. Locally, vite serves it on :5173 and this is skipped.
_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="frontend")
