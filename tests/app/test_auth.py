"""Staff login (KURORT_AUTH=oidc) against a fake identity provider.

The fake stands in for Keycloak at the ``OIDCProvider`` seam; one test drives
the real Authlib client far enough to check the authorization request it
builds (PKCE, scope, redirect URI) without any network.
"""

from __future__ import annotations

import time
from datetime import timedelta
from typing import Any
from urllib.parse import parse_qs, quote, urlsplit

import pytest
from authlib.integrations.base_client.errors import MismatchingStateError
from fastapi import Depends
from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient
from sqlalchemy import select

from kurort_app.auth import AuthConfigError, require_role
from kurort_app.config import Settings
from kurort_app.main import create_app
from kurort_app.models import CHECKED_IN, RESERVED, AuditEvent, Reservation
from tests.app.conftest import BUSINESS_DATE

ISSUER = "http://auth.kurort.localhost:8090/realms/hotel-rheinland"
END_SESSION = f"{ISSUER}/protocol/openid-connect/logout"


def oidc_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "auth": "oidc",
        "oidc_issuer": ISSUER,
        "oidc_internal_url": "http://keycloak.kurort.svc.cluster.local:8080/realms/hotel-rheinland",
        "oidc_client_secret": "client-secret",
        "session_secret": "s" * 40,
        "public_url": "http://testserver",
    }
    values.update(overrides)
    return Settings(**values)


class FakeIdP:
    """Records what the app asks for and answers like a provider would."""

    def __init__(self) -> None:
        self.claims: dict[str, Any] = {
            "sub": "u-1",
            "preferred_username": "m.schmidt",
            "name": "Maria Schmidt",
            "email": "m.schmidt@hotel-rheinland.example",
            "roles": ["rezeption", "offline_access"],
        }
        self.userinfo_claims: dict[str, Any] | None = None
        self.redirect_uri: str | None = None

    async def authorize_redirect(self, request, redirect_uri):
        self.redirect_uri = redirect_uri
        request.session["fake_state"] = "st4te"
        return RedirectResponse(
            f"{ISSUER}/protocol/openid-connect/auth?state=st4te&redirect_uri={quote(redirect_uri)}",
            status_code=302,
        )

    async def authorize_access_token(self, request):
        if request.query_params.get("state") != request.session.pop("fake_state", None):
            raise MismatchingStateError()
        return {"access_token": "at", "id_token": "fake-id-token", "userinfo": dict(self.claims)}

    async def userinfo(self, token):
        return dict(self.userinfo_claims or self.claims)

    async def end_session_endpoint(self):
        return END_SESSION


@pytest.fixture
def idp() -> FakeIdP:
    return FakeIdP()


@pytest.fixture
def oidc_client(db, idp):
    app = create_app(oidc_settings())
    app.state.oidc = idp

    @app.get("/_test/leitung")
    def leitung_only(user=Depends(require_role("leitung"))):
        return {"user": user.username}

    with TestClient(app) as client:
        yield client


def login(client: TestClient, next_path: str = "/"):
    started = client.get(f"/auth/login?next={quote(next_path)}", follow_redirects=False)
    assert started.status_code == 302
    return client.get("/auth/callback?code=c0de&state=st4te", follow_redirects=False)


# --- gate --------------------------------------------------------------------


def test_page_without_session_redirects_to_login_with_next(oidc_client):
    response = oidc_client.get("/reservierungen?q=m%C3%BCller", follow_redirects=False)
    assert response.status_code == 303
    assert (
        response.headers["location"] == "/auth/login?next=%2Freservierungen%3Fq%3Dm%25C3%25BCller"
    )


def test_htmx_request_without_session_gets_401_and_hx_redirect(oidc_client):
    response = oidc_client.get(
        "/reservierungen?q=mu&partial=1",
        headers={"HX-Request": "true", "HX-Current-URL": "http://testserver/reservierungen?q=mu"},
        follow_redirects=False,
    )
    assert response.status_code == 401
    assert response.headers["HX-Redirect"] == "/auth/login?next=%2Freservierungen%3Fq%3Dmu"


def test_form_post_without_session_returns_to_the_form_page(oidc_client):
    response = oidc_client.post(
        "/check-out/1", headers={"Referer": "http://testserver/abreisen"}, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/auth/login?next=%2Fabreisen"


def test_probes_and_static_assets_stay_public(oidc_client):
    assert oidc_client.get("/healthz").text == "ok\n"
    assert oidc_client.get("/readyz").status_code == 200
    assert oidc_client.get("/static/app.css").status_code == 200


def test_api_docs_require_login(oidc_client):
    for path in ("/api/docs", "/openapi.json"):
        assert oidc_client.get(path, follow_redirects=False).status_code == 303


# --- login / callback -------------------------------------------------------------


def test_login_sends_browser_to_provider_with_public_callback(oidc_client, idp):
    response = oidc_client.get("/auth/login", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"].startswith(f"{ISSUER}/protocol/openid-connect/auth")
    assert idp.redirect_uri == "http://testserver/auth/callback"


def test_callback_stores_user_and_lands_on_next(oidc_client):
    response = login(oidc_client, "/anreisen?filter=offen")
    assert response.status_code == 303
    assert response.headers["location"] == "/anreisen?filter=offen"

    page = oidc_client.get("/anreisen").text
    assert "Maria Schmidt" in page
    assert "Rezeption" in page
    assert 'action="/auth/logout"' in page
    assert "Ohne Anmeldung" not in page


def test_session_cookie_is_lax_and_named(oidc_client):
    response = login(oidc_client)
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("kurort_session=")
    assert "samesite=lax" in cookie.lower()
    assert "httponly" in cookie.lower()


@pytest.mark.parametrize(
    "evil", ["https://evil.example/", "//evil.example/x", "/\\evil.example", "javascript:alert(1)"]
)
def test_next_cannot_leave_the_app(oidc_client, evil):
    assert login(oidc_client, evil).headers["location"] == "/"


def test_state_mismatch_shows_retry_page(oidc_client):
    oidc_client.get("/auth/login", follow_redirects=False)
    response = oidc_client.get("/auth/callback?code=c0de&state=forged", follow_redirects=False)
    assert response.status_code == 400
    assert "Erneut anmelden" in response.text
    assert oidc_client.get("/", follow_redirects=False).status_code == 303  # still logged out


def test_provider_error_shows_retry_page(oidc_client):
    response = oidc_client.get("/auth/callback?error=access_denied", follow_redirects=False)
    assert response.status_code == 400
    assert "abgebrochen" in response.text


def test_user_without_known_role_is_forbidden(oidc_client, idp):
    idp.claims["roles"] = ["offline_access"]
    login(oidc_client)
    response = oidc_client.get("/", follow_redirects=False)
    assert response.status_code == 403
    assert "Kein Zugriff – Rolle fehlt" in response.text


def test_roles_fall_back_to_realm_access(oidc_client, idp):
    del idp.claims["roles"]
    idp.claims["realm_access"] = {"roles": ["leitung"]}
    login(oidc_client)
    page = oidc_client.get("/").text
    assert "Leitung" in page


def test_roles_missing_from_id_token_are_fetched_from_userinfo(oidc_client, idp):
    del idp.claims["roles"]
    idp.userinfo_claims = {**idp.claims, "roles": ["leitung"]}
    login(oidc_client)
    assert oidc_client.get("/_test/leitung").json() == {"user": "m.schmidt"}


def test_require_role(oidc_client, idp):
    login(oidc_client)
    assert oidc_client.get("/_test/leitung").status_code == 403


# --- logout -----------------------------------------------------------------------


def test_logout_clears_session_and_ends_provider_session(oidc_client):
    login(oidc_client)
    response = oidc_client.post("/auth/logout", follow_redirects=False)
    assert response.status_code == 303
    target = urlsplit(response.headers["location"])
    assert f"{target.scheme}://{target.netloc}{target.path}" == END_SESSION
    params = parse_qs(target.query)
    assert params["id_token_hint"] == ["fake-id-token"]
    assert params["post_logout_redirect_uri"] == ["http://testserver/"]
    assert params["client_id"] == ["kurort-app"]
    assert oidc_client.get("/", follow_redirects=False).status_code == 303


# --- audit actor ----------------------------------------------------------------


def test_audit_records_the_logged_in_user_async_endpoint(oidc_client, seeded):
    future = seeded.scalar(
        select(Reservation)
        .where(
            Reservation.status == RESERVED, Reservation.arrival > BUSINESS_DATE + timedelta(days=3)
        )
        .order_by(Reservation.id)
    )
    login(oidc_client)
    oidc_client.post(f"/reservierungen/{future.id}/stornieren", data={"grund": "Test"})
    event = seeded.scalar(select(AuditEvent).where(AuditEvent.entity_id == str(future.id)))
    assert event.actor == "m.schmidt"
    detail = oidc_client.get(f"/reservierungen/{future.id}").text
    assert "m.schmidt" in detail


def test_audit_records_the_logged_in_user_sync_endpoint(oidc_client, seeded):
    departing = seeded.scalar(
        select(Reservation)
        .where(Reservation.status == CHECKED_IN, Reservation.departure == BUSINESS_DATE)
        .order_by(Reservation.id)
    )
    login(oidc_client)
    oidc_client.post(f"/check-out/{departing.id}", follow_redirects=False)
    event = seeded.scalar(select(AuditEvent).where(AuditEvent.entity_id == str(departing.id)))
    assert event.actor == "m.schmidt"


def test_audit_actor_defaults_without_login(client, seeded):
    future = seeded.scalar(
        select(Reservation).where(Reservation.status == RESERVED).order_by(Reservation.id.desc())
    )
    client.post(f"/reservierungen/{future.id}/stornieren")
    event = seeded.scalar(select(AuditEvent).where(AuditEvent.entity_id == str(future.id)))
    assert event.actor == "rezeption"


def test_auth_off_marks_the_instance(client, db):
    assert "Ohne Anmeldung" in client.get("/").text


# --- configuration ----------------------------------------------------------------


def test_oidc_mode_refuses_to_start_unconfigured():
    with pytest.raises(AuthConfigError) as excinfo:
        create_app(Settings(auth="oidc"))
    message = str(excinfo.value)
    for env in ("KURORT_OIDC_ISSUER", "KURORT_OIDC_CLIENT_SECRET", "KURORT_SESSION_SECRET"):
        assert env in message


def test_short_session_secret_is_rejected():
    with pytest.raises(AuthConfigError, match="at least 32"):
        create_app(oidc_settings(session_secret="too-short"))


def test_real_client_builds_pkce_request_against_public_endpoint(db):
    """Authlib wiring: discovery from the internal URL, browser sent to the public one."""
    app = create_app(oidc_settings())
    provider = app.state.oidc
    assert provider.server_metadata_url == (
        "http://keycloak.kurort.svc.cluster.local:8080/realms/hotel-rheinland"
        "/.well-known/openid-configuration"
    )
    # What Keycloak (KC_HOSTNAME_BACKCHANNEL_DYNAMIC) answers on the internal host.
    provider._client.server_metadata.update(
        {
            "issuer": ISSUER,
            "authorization_endpoint": f"{ISSUER}/protocol/openid-connect/auth",
            "token_endpoint": "http://keycloak.kurort.svc.cluster.local:8080/realms/hotel-rheinland/protocol/openid-connect/token",
            "end_session_endpoint": END_SESSION,
            "_loaded_at": time.time(),
        }
    )
    with TestClient(app) as client:
        response = client.get("/auth/login?next=/zimmerplan", follow_redirects=False)
    assert response.status_code == 302
    target = urlsplit(response.headers["location"])
    assert (
        f"{target.scheme}://{target.netloc}{target.path}"
        == f"{ISSUER}/protocol/openid-connect/auth"
    )
    params = parse_qs(target.query)
    assert params["client_id"] == ["kurort-app"]
    assert params["redirect_uri"] == ["http://testserver/auth/callback"]
    assert params["scope"] == ["openid profile email"]
    assert params["code_challenge_method"] == ["S256"]
    assert params["code_challenge"] and params["state"] and params["nonce"]
