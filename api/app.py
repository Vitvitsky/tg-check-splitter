from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes.ocr import router as ocr_router
from api.routes.quota import router as quota_router
from api.routes.sessions import router as sessions_router
from api.routes.voting import router as voting_router
from api.routes.ws import router as ws_router
from api.ws import ConnectionManager
from bot.config import get_settings
from bot.db import get_engine

WEBAPP_DIST = Path(__file__).resolve().parent.parent / "webapp" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_engine()  # Initialize DB connection pool
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Check Splitter API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.webapp_url, "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # In-memory photo storage for mini-app uploads (keyed by placeholder tg_file_id)
    app.state.photo_storage = {}

    # WebSocket connection manager for real-time updates
    app.state.ws_manager = ConnectionManager()

    # Routers
    app.include_router(ocr_router)
    app.include_router(quota_router)
    app.include_router(sessions_router)
    app.include_router(voting_router)
    app.include_router(ws_router)

    # Health check
    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    # Serve built frontend (SPA with fallback to index.html)
    if WEBAPP_DIST.is_dir():
        app.mount("/", StaticFiles(directory=WEBAPP_DIST, html=True), name="spa")

    return app
