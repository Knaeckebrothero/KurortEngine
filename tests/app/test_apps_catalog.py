"""HTTP catalogue lifecycle, isolated broken apps and role-aware navigation."""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from kurort_app.apps import store
from kurort_app.apps.installations import install
from kurort_app.main import create_app
from kurort_app.models import AuditEvent
from tests.app.auth_helpers import login


@pytest.fixture
def app_client(app_definitions, client):
    return client


@pytest.fixture
def app_oidc(app_definitions, oidc_client):
    return oidc_client


def test_catalogue_lifecycle_preserves_records_and_sidebar(db, app_oidc, idp):
    idp.claims["roles"] = ["leitung"]
    login(app_oidc)
    app = app_oidc.app.state.apps.valid["geraetecheck"]
    assert "Nicht installiert" in app_oidc.get("/apps").text
    assert app_oidc.get("/apps/geraetecheck").status_code == 404
    for action, event in [
        ("installieren", "installed"),
        ("deaktivieren", "disabled"),
        ("aktivieren", "enabled"),
        ("deinstallieren", "uninstalled"),
        ("installieren", "installed"),
    ]:
        response = app_oidc.post(f"/apps/geraetecheck/{action}", follow_redirects=False)
        assert response.status_code == 303
        if action == "installieren" and event == "installed" and not store.records(db, app):
            store.create(db, app, "geraete", {"name": "Bleibt erhalten"})
            db.commit()
        visible = action in ("installieren", "aktivieren")
        page = app_oidc.get("/apps/geraetecheck")
        assert page.status_code == (200 if visible else 404)
        nav = app_oidc.get("/apps").text.split('<nav class="rail-nav">')[1].split("</nav>")[0]
        assert ('href="/apps/geraetecheck"' in nav) == visible
        if visible:
            active = re.findall(
                r'<a class="rail-link" href="([^"]+)" aria-current="page"', page.text
            )
            assert active == ["/apps/geraetecheck"]
        assert db.scalars(select(AuditEvent).where(AuditEvent.action == f"app.{event}")).all()
    assert len(store.records(db, app)) == 1
    assert (
        db.scalars(select(AuditEvent).where(AuditEvent.action == "app.installed")).all()[0].actor
        == "m.schmidt"
    )


def test_roles_override_and_view_only_actions(db, app_oidc, idp):
    app = app_oidc.app.state.apps.valid["geraetecheck"]
    install(db, app)
    row = store.create(db, app, "geraete", {"name": "Küche", "aktiv": True})
    db.commit()
    login(app_oidc)
    assert app_oidc.get("/apps").status_code == 403
    assert app_oidc.post("/apps/geraetecheck/deaktivieren").status_code == 403
    assert app_oidc.post("/apps/geraetecheck/geraete/neu", data={"name": "Nein"}).status_code == 403
    assert app_oidc.get("/apps/geraetecheck/geraete/neu").status_code == 403
    assert "Bearbeiten" not in app_oidc.get(f"/apps/geraetecheck/geraete/{row.id}").text
    app.roles.edit = []
    assert "Jetzt erfassen" not in app_oidc.get("/apps/geraetecheck").text
    assert "Messung erfassen" not in app_oidc.get("/apps/geraetecheck/messungen").text
    assert app_oidc.post("/apps/geraetecheck/messungen/neu", data={}).status_code == 403
    app.roles.view = []
    assert app_oidc.get("/apps/geraetecheck").status_code == 403
    nav = app_oidc.get("/").text.split('<nav class="rail-nav">')[1].split("</nav>")[0]
    assert "Apps verwalten" not in nav and 'href="/apps/geraetecheck"' not in nav
    assert 'class="rail-label">Apps<' not in nav


def test_broken_definition_isolated_and_errors_only_for_management(
    db, app_definitions, monkeypatch
):
    from kurort_app.config import get_settings

    fixtures = Path(__file__).parent / "fixtures"
    monkeypatch.setenv(
        "KURORT_APP_DEFINITION_DIRS", f"{fixtures / 'apps'}:{fixtures / 'apps_broken'}"
    )
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        registry = client.app.state.apps
        assert "geraetecheck" in registry.valid and registry.broken
        slug = next(iter(registry.broken))
        page = client.get("/apps")
        assert page.status_code == 200 and "Fehlerhaft" in page.text and slug in page.text
        assert client.get(f"/apps/{slug}").status_code == 503
        install(db, registry.valid["geraetecheck"])
        db.commit()
        assert client.get("/apps/geraetecheck").status_code == 200
