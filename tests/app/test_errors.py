"""Errors as staff see them: a German page in the app frame for the browser, JSON for calls."""

from __future__ import annotations

import pytest

from tests.app.auth_helpers import login

HTML = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}


def test_unknown_address_shows_a_german_page_in_the_app_frame(client):
    response = client.get("/gibt-es-nicht", headers=HTML)
    assert response.status_code == 404
    assert "<h1>Seite nicht gefunden</h1>" in response.text
    assert 'class="rail"' in response.text  # sidebar and top bar stay
    assert '<a class="btn primary" href="/">Zur Übersicht</a>' in response.text
    assert '{"detail"' not in response.text


@pytest.mark.parametrize(
    "path,heading",
    [
        ("/check-out/999999", "Reservierung nicht gefunden"),
        ("/seminarraum/999999", "Buchung nicht gefunden"),
        ("/e-mails/999999", "Eintrag nicht gefunden"),
        ("/apps/gibt-es-nicht", "App nicht gefunden"),
    ],
)
def test_missing_record_uses_the_screens_own_sentence(client, path, heading):
    response = client.get(path, headers=HTML)
    assert response.status_code == 404
    assert f"<h1>{heading}</h1>" in response.text
    assert "Der Link ist vielleicht veraltet" in response.text


def test_invalid_value_in_the_address(client, db):
    response = client.get("/check-out/abc", headers=HTML)
    assert response.status_code == 422
    assert "<h1>Ungültige Adresse</h1>" in response.text

    form = client.post("/check-out/abc", headers=HTML)
    assert form.status_code == 422
    assert "<h1>Ungültige Eingabe</h1>" in form.text


def test_calls_from_scripts_keep_json(client, db):
    assert client.get("/gibt-es-nicht").json() == {"detail": "Not Found"}
    assert client.get("/check-out/999999", headers={"Accept": "application/json"}).json() == {
        "detail": "Reservierung nicht gefunden"
    }
    htmx = client.get("/check-out/999999", headers={**HTML, "HX-Request": "true"})
    assert htmx.json() == {"detail": "Reservierung nicht gefunden"}
    assistant = client.get("/assistent/gibt-es-nicht", headers=HTML)
    assert assistant.json() == {"detail": "Not Found"}
    invalid = client.get("/check-out/abc", headers={"Accept": "application/json"})
    assert invalid.status_code == 422 and invalid.json()["detail"][0]["loc"] == [
        "path",
        "reservation_id",
    ]


def test_error_page_without_login_shows_no_app(oidc_client):
    response = oidc_client.get("/auth/gibt-es-nicht", headers=HTML)
    assert response.status_code == 404
    assert "Seite nicht gefunden" in response.text
    assert 'class="rail"' not in response.text and "Neue Reservierung" not in response.text
    assert 'href="/auth/login">Zur Anmeldung</a>' in response.text


def test_error_page_links_to_the_staff_members_own_area(oidc_client, idp):
    idp.claims.update(roles=["housekeeping"], preferred_username="s.klein", name="Sandra Klein")
    login(oidc_client)
    response = oidc_client.get("/gibt-es-nicht", headers=HTML)
    assert response.status_code == 404
    assert '<a class="btn primary" href="/zimmerstatus">Zu Ihrem Bereich</a>' in response.text
    assert "Sandra Klein" in response.text


def test_pages_are_not_kept_in_the_browser_cache(client, db):
    assert client.get("/").headers["cache-control"] == "no-store"
    assert client.get("/gibt-es-nicht", headers=HTML).headers["cache-control"] == "no-store"
    assert "cache-control" not in client.get("/static/app.css").headers
    assert "cache-control" not in client.get("/healthz").headers
    # A form's result page stays cacheable, so Back doesn't show "resubmit the form".
    assert "cache-control" not in client.post("/reservierungen/neu", data={}).headers


def test_forbidden_page_offers_the_way_back(oidc_client, idp):
    login(oidc_client)  # rezeption
    response = oidc_client.get("/_test/leitung")
    assert response.status_code == 403
    assert '<a class="btn primary" href="/">Zur Übersicht</a>' in response.text
    assert "Abmelden" in response.text
    assert response.headers["cache-control"] == "no-store"


def test_forbidden_page_without_role_only_offers_logout(oidc_client, idp):
    idp.claims["roles"] = ["offline_access"]
    login(oidc_client)
    response = oidc_client.get("/")
    assert response.status_code == 403
    assert "Zur Übersicht" not in response.text and "Zu Ihrem Bereich" not in response.text
    assert "Abmelden" in response.text


def test_notice_is_taken_out_of_the_address_after_showing(client, db):
    shown = client.get("/abreisen?notice=Check-out+gespeichert&notice_kind=success").text
    assert "Check-out gespeichert" in shown
    assert 'url.searchParams.delete("notice")' in shown
    assert "history.replaceState" not in client.get("/abreisen").text
