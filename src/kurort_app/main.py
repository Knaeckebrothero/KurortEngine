"""FastAPI application factory.

Run locally:  KURORT_DATABASE_URL=... uvicorn kurort_app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from kurort_app import __version__
from kurort_app.db import get_engine
from kurort_app.routers import checkin, front_desk, reservations
from kurort_app.web import STATIC_DIR


def create_app() -> FastAPI:
    app = FastAPI(title="KurortEngine", version=__version__, docs_url="/api/docs", redoc_url=None)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/healthz", response_class=PlainTextResponse, include_in_schema=False)
    def healthz() -> str:
        """Liveness: the process answers."""
        return "ok\n"

    @app.get("/readyz", response_class=PlainTextResponse, include_in_schema=False)
    def readyz() -> PlainTextResponse:
        """Readiness: the database answers."""
        try:
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:  # noqa: BLE001 - any DB failure means not ready
            return PlainTextResponse("database unavailable\n", status_code=503)
        return PlainTextResponse("ok\n")

    app.include_router(front_desk.router)
    app.include_router(reservations.router)
    app.include_router(checkin.router)
    return app


app = create_app()
