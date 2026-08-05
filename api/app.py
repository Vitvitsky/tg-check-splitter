from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes.ocr import router as ocr_router
from api.routes.quota import router as quota_router
from api.routes.sessions import router as sessions_router
from api.routes.voting import router as voting_router
from api.routes.ws import router as ws_router
from api.ws import ConnectionManager
from core.config import get_settings
from core.db import get_engine

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

    # NOTE: uploaded receipt bytes used to live here in an unbounded process-local dict.
    # They are columns on session_photos now (migration a7c3e91b40d2) — a restart no
    # longer strands in-flight sessions, and nothing keeps growing in memory.

    # WebSocket connection manager for real-time updates.
    #
    # This one IS still per-process: broadcasts only reach clients connected to this
    # worker, so running more than one worker needs a shared backend (e.g. Redis pub/sub)
    # first. It is now the only thing standing in the way of scaling out.
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

    # Serve the built frontend.
    #
    # StaticFiles(html=True) only serves index.html for *directory* paths — it 404s on
    # unknown ones. The app uses BrowserRouter, so /session/<code>/vote is a real URL a
    # user can reload or deep-link into, and mounting StaticFiles at "/" made every one
    # of those a 404. Hashed build assets are served from /assets; everything else that
    # is not an API or WebSocket route falls through to index.html and is routed
    # client-side.
    if WEBAPP_DIST.is_dir():
        assets_dir = WEBAPP_DIST / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        index_file = WEBAPP_DIST / "index.html"

        @app.get("/{spa_path:path}", include_in_schema=False)
        async def spa_fallback(spa_path: str):
            # An unmatched /api/... path is a client bug, not a page — keep it a 404
            # instead of handing back index.html with a 200.
            if spa_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not found")

            # Serve real files at the dist root (favicon, manifest, robots.txt …)
            # but never traverse outside it.
            candidate = (WEBAPP_DIST / spa_path).resolve()
            if (
                spa_path
                and candidate.is_file()
                and candidate.is_relative_to(WEBAPP_DIST.resolve())
            ):
                return FileResponse(candidate)
            return FileResponse(index_file)

    return app
