"""FastAPI application factory.

Run locally:  KURORT_DATABASE_URL=... uvicorn --factory kurort_app.main:create_app --reload
(``kurort-app serve`` does this). Building the app validates the login
settings, so a misconfigured instance stops at startup, not at first login.
"""

from __future__ import annotations

import os
from http import HTTPStatus
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.datastructures import MutableHeaders
from starlette.exceptions import HTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

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
from kurort_app.web import STATIC_DIR, templates


class NoStoreHTML:
    """ASGI middleware: the browser keeps no copy of a staff page.

    Otherwise Back after logging out shows the guest list again from the cache.
    Static assets and the probes keep normal caching.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        if (
            scope["type"] != "http"
            or scope["method"] not in ("GET", "HEAD")
            or path.startswith("/static/")
            or path in auth.PUBLIC_PATHS
        ):
            await self.app(scope, receive, send)
            return

        async def send_no_store(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                if headers.get("content-type", "").startswith("text/html"):
                    headers.setdefault("cache-control", "no-store")
            await send(message)

        await self.app(scope, receive, send_no_store)


def _wants_html(request: Request) -> bool:
    """A page the browser navigates to (link, address bar, form), not an htmx or fetch() call."""
    return (
        "text/html" in request.headers.get("accept", "")
        and request.headers.get("hx-request") != "true"
        and not auth._wants_json(request)
    )


def _error_texts(status: int, detail: Any) -> tuple[str, str]:
    """Heading and sentence for an error; a router's own German ``detail`` is shown as is.

    The default ``detail`` is the English status phrase ("Not Found"), never shown.
    """
    own = detail if isinstance(detail, str) and detail != HTTPStatus(status).phrase else ""
    if status in (404, 405):
        if own:  # a missing record: "Reservierung nicht gefunden."
            heading = own.rstrip(".")
            return heading, "Der Link ist vielleicht veraltet, oder der Eintrag wurde entfernt."
        return (
            "Seite nicht gefunden",
            "Diese Adresse gibt es nicht. Der Link ist vielleicht veraltet oder unvollständig.",
        )
    if own and own[-1] not in ".!?":
        own += "."
    if status == 422:
        return "Ungültige Eingabe", own or "Bitte prüfen Sie Ihre Angaben."
    return "Das hat nicht geklappt", own or "Bitte versuchen Sie es noch einmal."


def _error_page(
    request: Request, status: int, title: str, message: str, headers: dict | None = None
) -> Response:
    """The German error page: in the app frame for staff, on the login card for nobody."""
    user = getattr(request.state, "user", None)
    framed = not getattr(request.state, "auth_enabled", False) or bool(user and user.has_access)
    home = auth.home_path(user)
    if not framed:
        back = ("/auth/login", "Zur Anmeldung")
    else:
        back = (home, "Zur Übersicht" if home == "/" else "Zu Ihrem Bereich")
    context = {"title": title, "message": message, "framed": framed, "back": back}
    return templates.TemplateResponse(
        request, "error.html", context, status_code=status, headers=headers
    )


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
    # Outermost, so the gate's own pages (Kein Zugriff) are covered too.
    app.add_middleware(NoStoreHTML)

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

    # Starlette's HTTPException: also unknown addresses (the router's 404), not only raise sites.
    @app.exception_handler(HTTPException)
    async def staff_error(request: Request, exc: HTTPException):
        if exc.status_code == 403 and not auth._wants_json(request):
            return auth._render(
                request, "auth/forbidden.html", {"user": getattr(request.state, "user", None)}, 403
            )
        if _wants_html(request) and exc.status_code >= 400:
            title, message = _error_texts(exc.status_code, exc.detail)
            return _error_page(request, exc.status_code, title, message, exc.headers)
        return await http_exception_handler(request, exc)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        if not _wants_html(request):
            return await request_validation_exception_handler(request, exc)
        if request.method in ("GET", "HEAD"):
            return _error_page(
                request,
                422,
                "Ungültige Adresse",
                "Die Adresse enthält einen ungültigen Wert, zum Beispiel Buchstaben statt einer Zahl.",
            )
        return _error_page(
            request,
            422,
            "Ungültige Eingabe",
            "Das Formular enthielt einen ungültigen Wert. Bitte gehen Sie zurück und prüfen Sie "
            "Ihre Angaben.",
        )

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
