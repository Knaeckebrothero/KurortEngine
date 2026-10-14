"""Staff login via OpenID Connect (Keycloak or any compliant provider).

The browser talks to the provider's public URL (``KURORT_OIDC_ISSUER``); the
server fetches discovery, tokens, keys and userinfo from
``KURORT_OIDC_INTERNAL_URL`` when set. Keycloak with
``KC_HOSTNAME_BACKCHANNEL_DYNAMIC=true`` answers discovery on its internal
host with backchannel endpoints on that host and browser endpoints (and the
issuer) on the public one, which is exactly the split this needs.

The session is a signed cookie (``kurort_session``) holding the user's
claims and the id token for the logout hint. Everything except the probes,
static assets and ``/auth/*`` requires a logged-in user with a known role.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import urlencode, urlsplit

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from kurort_app.config import Settings

log = logging.getLogger(__name__)

SESSION_COOKIE = "kurort_session"
SESSION_MAX_AGE = 12 * 60 * 60
MIN_SESSION_SECRET = 32
SCOPE = "openid profile email"
ROLE_LABELS = {"leitung": "Leitung", "rezeption": "Rezeption"}  # highest first
PUBLIC_PATHS = frozenset({"/healthz", "/readyz"})
PUBLIC_PREFIXES = ("/static/", "/auth/")

# Username of the staff member behind the current request; read by audit.record().
current_actor: ContextVar[str | None] = ContextVar("kurort_current_actor", default=None)


class AuthConfigError(RuntimeError):
    """OIDC mode is on but the settings to run it are missing or unusable."""


@dataclass(frozen=True)
class User:
    sub: str
    username: str
    name: str = ""
    email: str = ""
    roles: tuple[str, ...] = field(default_factory=tuple)

    @property
    def display_name(self) -> str:
        return self.name or self.username

    @property
    def initials(self) -> str:
        parts = [p for p in self.display_name.replace(".", " ").split() if p]
        return "".join(p[0] for p in parts[:2]).upper() or "?"

    @property
    def known_roles(self) -> tuple[str, ...]:
        return tuple(r for r in ROLE_LABELS if r in self.roles)

    @property
    def has_access(self) -> bool:
        return bool(self.known_roles)

    @property
    def role_label(self) -> str:
        known = self.known_roles
        return ROLE_LABELS[known[0]] if known else "Ohne Rolle"

    def to_session(self) -> dict[str, Any]:
        return {
            "sub": self.sub,
            "username": self.username,
            "name": self.name,
            "email": self.email,
            "roles": list(self.roles),
        }

    @classmethod
    def from_session(cls, data: dict[str, Any]) -> User:
        return cls(
            sub=str(data.get("sub", "")),
            username=str(data.get("username", "")),
            name=str(data.get("name", "")),
            email=str(data.get("email", "")),
            roles=tuple(data.get("roles") or ()),
        )

    @classmethod
    def from_claims(cls, claims: dict[str, Any]) -> User:
        return cls(
            sub=str(claims.get("sub", "")),
            username=str(claims.get("preferred_username") or claims.get("sub", "")),
            name=str(claims.get("name") or ""),
            email=str(claims.get("email") or ""),
            roles=extract_roles(claims),
        )


def extract_roles(claims: dict[str, Any]) -> tuple[str, ...]:
    """Flat ``roles`` claim first (realm mapper), then Keycloak's ``realm_access.roles``."""
    roles = claims.get("roles")
    if not roles:
        roles = (claims.get("realm_access") or {}).get("roles")
    return tuple(str(r) for r in roles or ())


def auth_enabled(settings: Settings) -> bool:
    return settings.auth == "oidc"


def validate_settings(settings: Settings) -> None:
    """Fail fast at startup instead of on the first login attempt."""
    if not auth_enabled(settings):
        return
    missing = [
        env
        for env, value in (
            ("KURORT_OIDC_ISSUER", settings.oidc_issuer),
            ("KURORT_OIDC_CLIENT_ID", settings.oidc_client_id),
            ("KURORT_OIDC_CLIENT_SECRET", settings.oidc_client_secret),
            ("KURORT_SESSION_SECRET", settings.session_secret),
        )
        if not value
    ]
    problems = [f"missing {', '.join(missing)}"] if missing else []
    if settings.session_secret and len(settings.session_secret) < MIN_SESSION_SECRET:
        problems.append(f"KURORT_SESSION_SECRET must be at least {MIN_SESSION_SECRET} characters")
    for env, value in (
        ("KURORT_OIDC_ISSUER", settings.oidc_issuer),
        ("KURORT_OIDC_INTERNAL_URL", settings.oidc_internal_url),
        ("KURORT_PUBLIC_URL", settings.public_url),
    ):
        if value and urlsplit(value).scheme not in ("http", "https"):
            problems.append(f"{env} must be an http(s) URL")
    if problems:
        raise AuthConfigError(
            "KURORT_AUTH=oidc (the default) but the login is not configured: "
            + "; ".join(problems)
            + ". Set the variables, or KURORT_AUTH=off for a local, unprotected instance."
        )


# ---------------------------------------------------------------------------
# Provider client
# ---------------------------------------------------------------------------


class OIDCProvider(Protocol):
    """What the auth routes need from the identity provider (faked in tests)."""

    async def authorize_redirect(self, request: Request, redirect_uri: str) -> Response: ...

    async def authorize_access_token(self, request: Request) -> dict[str, Any]: ...

    async def userinfo(self, token: dict[str, Any]) -> dict[str, Any]: ...

    async def end_session_endpoint(self) -> str | None: ...


class AuthlibProvider:
    """Authorization code flow with PKCE (S256) via Authlib's Starlette client."""

    def __init__(self, settings: Settings) -> None:
        from authlib.integrations.starlette_client import OAuth

        self.issuer = settings.oidc_issuer.rstrip("/")
        backchannel = (settings.oidc_internal_url or settings.oidc_issuer).rstrip("/")
        self.server_metadata_url = f"{backchannel}/.well-known/openid-configuration"
        self._client = OAuth().register(
            name="keycloak",
            client_id=settings.oidc_client_id,
            client_secret=settings.oidc_client_secret,
            server_metadata_url=self.server_metadata_url,
            client_kwargs={"scope": SCOPE, "code_challenge_method": "S256"},
        )

    async def authorize_redirect(self, request: Request, redirect_uri: str) -> Response:
        # Staff UI is German; don't let the browser's language pick an English login page.
        return await self._client.authorize_redirect(request, redirect_uri, ui_locales="de")

    async def authorize_access_token(self, request: Request) -> dict[str, Any]:
        # Pin the issuer to the configured public URL rather than trusting
        # whatever the (internal) discovery document claims.
        return await self._client.authorize_access_token(
            request, claims_options={"iss": {"essential": True, "values": [self.issuer]}}
        )

    async def userinfo(self, token: dict[str, Any]) -> dict[str, Any]:
        return dict(await self._client.userinfo(token=token))

    async def end_session_endpoint(self) -> str | None:
        metadata = await self._client.load_server_metadata()
        return metadata.get("end_session_endpoint")


# ---------------------------------------------------------------------------
# Request gate
# ---------------------------------------------------------------------------


def _is_public(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES)


def safe_next(value: str | None) -> str:
    """Only same-site relative paths survive; anything else returns to the overview."""
    if not value or not value.startswith("/") or value.startswith("//") or "\\" in value:
        return "/"
    parts = urlsplit(value)
    if parts.scheme or parts.netloc:
        return "/"
    return value


def _path_of(url: str | None, host: str | None) -> str | None:
    """Path+query of a same-host absolute URL (from HX-Current-URL or Referer)."""
    if not url:
        return None
    parts = urlsplit(url)
    if parts.netloc and host and parts.netloc != host:
        return None
    return (parts.path or "/") + (f"?{parts.query}" if parts.query else "")


def _login_url(request: Request) -> str:
    """Where to send someone who is not logged in, remembering where they were going."""
    host = request.headers.get("host")
    if request.headers.get("hx-request") == "true":
        target = _path_of(request.headers.get("hx-current-url"), host)
    elif request.method in ("GET", "HEAD"):
        target = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    else:  # an expired session mid-form: return to the page the form was on
        target = _path_of(request.headers.get("referer"), host)
    return "/auth/login?" + urlencode({"next": safe_next(target)})


class AuthGate:
    """ASGI middleware: attaches ``request.state.user`` and enforces login.

    Must run inside SessionMiddleware (it reads ``scope["session"]``). Pure ASGI
    rather than BaseHTTPMiddleware so the actor contextvar reaches endpoints,
    including sync ones running in the threadpool.
    """

    def __init__(self, app: ASGIApp, *, enabled: bool) -> None:
        self.app = app
        self.enabled = enabled

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        user: User | None = None
        if self.enabled:
            data = scope.get("session", {}).get("user")
            user = User.from_session(data) if data else None
        state = scope.setdefault("state", {})
        state["user"] = user
        state["auth_enabled"] = self.enabled

        if self.enabled and not _is_public(scope["path"]):
            request = Request(scope, receive)
            response: Response | None = None
            if user is None:
                login = _login_url(request)
                if request.headers.get("hx-request") == "true":
                    response = Response(status_code=401, headers={"HX-Redirect": login})
                else:
                    response = RedirectResponse(login, status_code=303)
            elif not user.has_access:
                response = _render(request, "auth/forbidden.html", {"user": user}, 403)
            if response is not None:
                await response(scope, receive, send)
                return

        token = current_actor.set(user.username if user else None)
        try:
            await self.app(scope, receive, send)
        finally:
            current_actor.reset(token)


def _render(request: Request, template: str, context: dict[str, Any], status: int) -> Response:
    from kurort_app.web import templates

    return templates.TemplateResponse(request, template, context, status_code=status)


def require_role(*roles: str) -> Callable[[Request], User | None]:
    """Dependency: ``Depends(require_role("leitung"))``. A no-op when auth is off."""

    def dependency(request: Request) -> User | None:
        if not getattr(request.state, "auth_enabled", False):
            return None
        user: User | None = getattr(request.state, "user", None)
        if user is None or not set(roles) & set(user.roles):
            raise HTTPException(status_code=403, detail="Rolle fehlt")
        return user

    return dependency


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/auth", include_in_schema=False)


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _public_base(request: Request) -> str:
    settings = _settings(request)
    if settings.public_url:
        return settings.public_url.rstrip("/")
    return str(request.base_url).rstrip("/")


def _error(request: Request, message: str, status: int = 400) -> Response:
    return _render(request, "auth/error.html", {"message": message}, status)


@router.get("/login", name="auth_login")
async def login(request: Request, next: str | None = None) -> Response:  # noqa: A002
    target = safe_next(next)
    if not auth_enabled(_settings(request)) or request.state.user is not None:
        return RedirectResponse(target, status_code=303)
    request.session["auth_next"] = target
    provider: OIDCProvider = request.app.state.oidc
    try:
        return await provider.authorize_redirect(request, f"{_public_base(request)}/auth/callback")
    except Exception:  # noqa: BLE001 - provider down or misconfigured
        log.exception("OIDC authorize redirect failed")
        return _error(
            request,
            "Der Anmeldedienst ist gerade nicht erreichbar. Bitte gleich erneut versuchen.",
            503,
        )


@router.get("/callback", name="auth_callback")
async def callback(request: Request) -> Response:
    from authlib.integrations.base_client.errors import OAuthError

    if not auth_enabled(_settings(request)):
        return RedirectResponse("/", status_code=303)
    provider: OIDCProvider = request.app.state.oidc
    if request.query_params.get("error"):
        reason = request.query_params.get("error_description") or request.query_params["error"]
        log.info("OIDC login aborted by provider: %s", reason)
        return _error(request, "Die Anmeldung wurde abgebrochen.")
    try:
        token = await provider.authorize_access_token(request)
        claims = dict(token.get("userinfo") or {})
        if not extract_roles(claims) or not claims.get("preferred_username"):
            # Roles not mapped into the id token: ask the userinfo endpoint.
            info = await provider.userinfo(token)
            claims = {**info, **{k: v for k, v in claims.items() if v}}
    except OAuthError as exc:
        log.warning("OIDC callback rejected: %s", exc)
        return _error(request, "Die Anmeldung ist abgelaufen oder ungültig.")
    except Exception:  # noqa: BLE001 - network/provider failure
        log.exception("OIDC token exchange failed")
        return _error(request, "Der Anmeldedienst ist gerade nicht erreichbar.", 503)

    user = User.from_claims(claims)
    target = safe_next(request.session.get("auth_next"))
    request.session.clear()  # drop pre-login state: a fresh session for the new identity
    request.session["user"] = user.to_session()
    if token.get("id_token"):
        request.session["id_token"] = token["id_token"]
    log.info("login: %s roles=%s", user.username, ",".join(user.roles))
    return RedirectResponse(target, status_code=303)


@router.post("/logout", name="auth_logout")
async def logout(request: Request) -> Response:
    if not auth_enabled(_settings(request)):
        return RedirectResponse("/", status_code=303)
    id_token = request.session.get("id_token")
    request.session.clear()
    provider: OIDCProvider = request.app.state.oidc
    try:
        endpoint = await provider.end_session_endpoint()
    except Exception:  # noqa: BLE001 - logging out locally must still work
        log.exception("OIDC end-session lookup failed")
        endpoint = None
    if not endpoint:
        return RedirectResponse("/", status_code=303)
    params = {
        "client_id": _settings(request).oidc_client_id,
        "post_logout_redirect_uri": f"{_public_base(request)}/",
    }
    if id_token:
        params["id_token_hint"] = id_token
    sep = "&" if "?" in endpoint else "?"
    return RedirectResponse(f"{endpoint}{sep}{urlencode(params)}", status_code=303)
