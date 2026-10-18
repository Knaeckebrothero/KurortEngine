"""Login helpers for app tests: a fake Keycloak and OIDC test settings.

The ``idp`` and ``oidc_client`` fixtures (in conftest.py) build an app with
KURORT_AUTH=oidc against ``FakeIdP``. Set ``idp.claims["roles"]`` before
``login(oidc_client)`` to act as a given staff role.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from authlib.integrations.base_client.errors import MismatchingStateError
from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient

from kurort_app.config import Settings

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


def login(client: TestClient, next_path: str = "/"):
    started = client.get(f"/auth/login?next={quote(next_path)}", follow_redirects=False)
    assert started.status_code == 302
    return client.get("/auth/callback?code=c0de&state=st4te", follow_redirects=False)
