from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import account, book, market, scenarios, scorecard, settings as settings_router

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


@app.get("/health")
def health():
    return {"status": "ok"}
