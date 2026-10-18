"""The shared hooks features plug into: sidebar links and default rows."""

from __future__ import annotations

import sys
import types

import pytest
from sqlalchemy import text

from kurort_app import defaults, web
from tests.app.auth_helpers import FakeIdP, login

LEITUNG_LINK = web.NavItem(
    "/verwaltung/test", "Testverwaltung", "<path/>", "Verwaltung", roles=("leitung",)
)


def _rail(html: str) -> str:
    return html.split('class="rail-nav"', 1)[1].split("</nav>", 1)[0]


def test_sidebar_lists_the_static_links_in_group_order(client):
    rail = _rail(client.get("/").text)
    labels = ["Heute", "Übersicht", "Anreisen", "Abreisen", "Im Haus", "Planung", "Zimmerplan"]
    positions = [rail.index(label) for label in labels]
    assert positions == sorted(positions)
    assert 'href="/" aria-current="page"' in rail


def test_sidebar_hides_empty_groups(client):
    rail = _rail(client.get("/").text)
    assert "Verwaltung" not in rail and "Apps" not in rail


def test_appended_link_shows_in_its_group_without_login(client, monkeypatch):
    monkeypatch.setattr(web, "NAV", [*web.NAV, LEITUNG_LINK])
    rail = _rail(client.get("/").text)
    assert rail.index("Verwaltung") < rail.index("Testverwaltung")


def test_link_is_shown_only_to_its_roles(oidc_client, idp: FakeIdP, monkeypatch):
    monkeypatch.setattr(web, "NAV", [*web.NAV, LEITUNG_LINK])
    login(oidc_client)  # rezeption only
    assert "Testverwaltung" not in _rail(oidc_client.get("/").text)

    oidc_client.cookies.clear()  # log in again with more roles
    idp.claims["roles"] = ["rezeption", "leitung"]
    login(oidc_client)
    assert "Testverwaltung" in _rail(oidc_client.get("/").text)


def test_nav_providers_add_links_per_request(client, monkeypatch):
    extra = web.NavItem("/apps/demo", "Demo-App", "<path/>", "Apps")
    monkeypatch.setattr(web, "NAV_PROVIDERS", [lambda request: [extra]])
    rail = _rail(client.get("/").text)
    assert rail.index("Apps") < rail.index("Demo-App")


@pytest.fixture
def defaults_module(db, monkeypatch):
    module = types.ModuleType("kurort_test_defaults")

    def ensure_marker(session):
        session.execute(text("CREATE TABLE IF NOT EXISTS defaults_marker (n int)"))
        if not session.scalar(text("SELECT count(*) FROM defaults_marker")):
            session.execute(text("INSERT INTO defaults_marker VALUES (1)"))

    module.ensure_marker = ensure_marker
    monkeypatch.setitem(sys.modules, "kurort_test_defaults", module)
    monkeypatch.setattr(defaults, "DEFAULTS", ["kurort_test_defaults:ensure_marker"])
    yield
    db.rollback()  # release the test's lock on the table before dropping it
    db.execute(text("DROP TABLE IF EXISTS defaults_marker"))
    db.commit()


def test_registered_defaults_are_ensured_once(db, defaults_module):
    defaults.ensure_defaults(db)
    defaults.ensure_defaults(db)
    assert db.scalar(text("SELECT count(*) FROM defaults_marker")) == 1


def test_seed_reset_empties_every_table_and_restores_defaults(db, defaults_module):
    from kurort_app.seed import seed_demo_data

    defaults.ensure_defaults(db)
    db.execute(text("INSERT INTO defaults_marker VALUES (2)"))
    db.commit()
    seed_demo_data(db, reset=True)
    assert db.scalar(text("SELECT count(*) FROM defaults_marker")) == 1
