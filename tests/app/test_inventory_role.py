"""F8's kitchen role plumbing when F7 has not landed yet."""

import pytest

from kurort_app.auth import ROLE_LABELS, User
from tests.app.auth_helpers import login


def test_kueche_is_a_known_limited_role_after_housekeeping():
    user = User(sub="kitchen-1", username="j.becker", name="Jana Becker", roles=("kueche",))

    assert ROLE_LABELS["kueche"] == "Küche"
    assert list(ROLE_LABELS).index("kueche") == list(ROLE_LABELS).index("housekeeping") + 1
    assert user.has_access
    assert user.known_roles == ("kueche",)
    assert user.role_label == "Küche"


def test_kueche_start_keeps_the_haccp_default(oidc_client, idp):
    idp.claims.update(roles=["kueche"], preferred_username="j.becker", name="Jana Becker")
    login(oidc_client)

    # Keep F7's decided destination; this plumbing does not install HACCP.
    response = oidc_client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/apps/haccp"


def test_kueche_cannot_open_or_write_front_desk_screens(oidc_client, idp):
    idp.claims.update(roles=["kueche"], preferred_username="j.becker", name="Jana Becker")
    login(oidc_client)

    for path in (
        "/anreisen",
        "/abreisen",
        "/im-haus",
        "/reservierungen",
        "/zimmerplan",
        "/zimmerstatus",
        "/seminarraum",
        "/check-in/1/abschluss",
        "/zahlungen/offen",
        "/e-mails",
        "/spaetanreisen",
    ):
        response = oidc_client.get(path, follow_redirects=False)
        assert response.status_code == 403, path
        assert 'href="/apps/haccp"' in response.text
        assert "Zu Ihrem Bereich" in response.text
        assert "assistant-bar" not in response.text
        assert "Neue Reservierung" not in response.text

    denied = oidc_client.get("/anreisen", headers={"Accept": "application/json"})
    assert denied.status_code == 403
    assert denied.json() == {"detail": "Rolle fehlt"}

    for path in ("/check-in/1/abschluss", "/check-out/1", "/zimmerstatus/1/clean"):
        response = oidc_client.post(path, follow_redirects=False)
        assert response.status_code == 403, path

    denied = oidc_client.post("/assistent/plan", json={"text": "Anreisen"})
    assert denied.status_code == 403
    assert denied.headers["content-type"].startswith("application/json")


@pytest.mark.parametrize("front_desk_role", ["rezeption", "leitung"])
def test_kueche_does_not_override_a_front_desk_role(oidc_client, idp, front_desk_role):
    idp.claims["roles"] = ["kueche", front_desk_role]
    login(oidc_client)

    home = oidc_client.get("/", follow_redirects=False)
    assert home.status_code == 200
    assert "Neue Reservierung" in home.text
    assert oidc_client.get("/anreisen").status_code == 200
