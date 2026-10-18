"""FastAPI application factory.

Run locally:  KURORT_DATABASE_URL=... uvicorn --factory kurort_app.main:create_app --reload
(``kurort-app serve`` does this). Building the app validates the login
settings, so a misconfigured instance stops at startup, not at first login.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

from kurort_app import __version__, auth
from kurort_app.apps.registry import AppRegistry
from kurort_app.config import Settings, get_settings
from kurort_app.db import get_engine
from kurort_app.routers import (
    apps,
    assistant,
    checkin,
    front_desk,
    home,
    housekeeping,
    late_arrival,
    mail,
    payments,
    reservations,
    seminar,
)
from kurort_app.services.mail import validate_settings as validate_mail_settings
from kurort_app.web import STATIC_DIR


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    auth.validate_settings(settings)
    validate_mail_settings(settings)
    enabled = auth.auth_enabled(settings)

    app = FastAPI(title="KurortEngine", version=__version__, docs_url="/api/docs", redoc_url=None)
    app.state.apps = AppRegistry([p for p in settings.app_definition_dirs.split(os.pathsep) if p])
    app.add_exception_handler(apps.AppUnavailable, apps.unavailable_handler)
    app.state.settings = settings
    app.state.oidc = auth.AuthlibProvider(settings) if enabled else None
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # Added innermost first: the session must be decoded before the gate reads it.
    app.add_middleware(auth.AuthGate, enabled=enabled)
    if enabled:
        app.add_middleware(
            SessionMiddleware,
            secret_key=settings.session_secret,
            session_cookie=auth.SESSION_COOKIE,
            max_age=auth.SESSION_MAX_AGE,
            same_site="lax",
            https_only=(settings.public_url or "").startswith("https://"),
        )

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

    @app.exception_handler(HTTPException)
    async def staff_error(request: Request, exc: HTTPException):
        if exc.status_code == 403 and not auth._wants_json(request):
            return auth._render(
                request, "auth/forbidden.html", {"user": getattr(request.state, "user", None)}, 403
            )
        return await http_exception_handler(request, exc)

    app.include_router(auth.router)
    app.include_router(home.router)
    front_desk_dependencies = [Depends(auth.require_role(*auth.FRONT_DESK_ROLES))]
    app.include_router(front_desk.router, dependencies=front_desk_dependencies)
    app.include_router(reservations.router, dependencies=front_desk_dependencies)
    app.include_router(checkin.router, dependencies=front_desk_dependencies)
    app.include_router(assistant.router, dependencies=front_desk_dependencies)
    app.include_router(seminar.router, dependencies=front_desk_dependencies)
    app.include_router(payments.router, dependencies=front_desk_dependencies)
    app.include_router(mail.router, dependencies=front_desk_dependencies)
    app.include_router(late_arrival.router, dependencies=front_desk_dependencies)
    # Apps check each app's own roles (a kitchen app is not a front-desk screen).
    app.include_router(apps.router)
    app.include_router(housekeeping.router)
    return app


def __getattr__(name: str) -> Any:
    """``kurort_app.main:app`` still works, built on first access (not at import)."""
    if name == "app":
        return create_app()
    raise AttributeError(name)
