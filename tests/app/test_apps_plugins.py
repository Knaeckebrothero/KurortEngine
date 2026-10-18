"""Plugin context permissions, shared validation/audit and demo reset hook."""

from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from kurort_app.apps.registry import AppRegistry
from kurort_app.auth import User
from kurort_app.models import AuditEvent


def test_context_writes_share_validation_and_flush_without_commit(db, app_definitions):
    from kurort_app.apps.context import AppContext
    from kurort_app.apps.store import RecordValidationError

    app = AppRegistry().valid["geraetecheck"]
    ctx = AppContext(None, db, app, None)
    with pytest.raises(RecordValidationError) as exc:
        ctx.create("geraete", {})
    assert exc.value.errors["name"] == "Name ist Pflicht."
    row = ctx.create("geraete", {"name": "Plugin-Gerät"})
    assert row.id and ctx.records("geraete")[0].id == row.id
    assert ctx.value(row, "name") == "Plugin-Gerät"
    assert db.scalars(select(AuditEvent).where(AuditEvent.action == "app_record.created")).one()
    db.rollback()
    assert ctx.records("geraete") == []
    user = User(sub="1", username="m.schmidt", roles=("rezeption",))
    ctx = AppContext(None, db, app, user)
    assert ctx.can_view("geraete") and not ctx.can_edit("geraete")
    with pytest.raises(HTTPException) as exc:
        ctx.create("geraete", {"name": "Forbidden"})
    assert exc.value.status_code == 403


def test_demo_reset_installs_and_runs_hook(db, app_definitions):
    from kurort_app.apps.models import AppInstallation, AppRecord
    from kurort_app.seed import seed_demo_data

    for _ in range(2):
        db.expunge_all()
        assert seed_demo_data(db, reset=True, anchor=date(2026, 10, 14)) > 0
        assert db.get(AppInstallation, "geraetecheck").enabled
        rows = db.scalars(
            select(AppRecord).where(AppRecord.app_slug == "geraetecheck").order_by(AppRecord.id)
        ).all()
        assert len(rows) == 2
        assert rows[1].out_of_range


def test_http_plugin_view_uses_shared_context(db, app_definitions, client):
    from kurort_app.apps.installations import install

    install(db, client.app.state.apps.valid["geraetecheck"])
    db.commit()
    page = client.get("/apps/geraetecheck/ansicht/auswertung")
    assert page.status_code == 200 and "Auswertung" in page.text
    assert client.post("/apps/geraetecheck/ansicht/auswertung").status_code == 200
    assert db.scalars(select(AuditEvent).where(AuditEvent.action == "app_record.created")).one()


def test_plugin_can_create_restricted_child_only_of_its_new_editable_parent(db, app_definitions):
    from kurort_app.apps.context import AppContext
    from kurort_app.apps.schema import Roles

    app = AppRegistry().valid["geraetecheck"]
    app.collection("geraete").roles = Roles(edit=["rezeption"])
    app.collection("messungen").roles = Roles(edit=[])
    user = User(sub="1", username="m.schmidt", roles=("rezeption",))
    ctx = AppContext(None, db, app, user)
    parent = ctx.create("geraete", {"name": "Plugin-Gerät"})
    data = {"geraet": parent.id, "gemessen_am": "2026-10-14T08:00", "temperatur": "4"}
    with pytest.raises(HTTPException):
        ctx.create("messungen", data)
    child = ctx.create("messungen", data, parent=parent)
    assert child.created_by == "m.schmidt" and not ctx.can_edit("messungen")
    with pytest.raises(HTTPException):
        AppContext(None, db, app, user).create("messungen", data, parent=parent)
    with pytest.raises(HTTPException):
        ctx.create("messungen", {**data, "geraet": parent.id + 1}, parent=parent)
    db.rollback()
    assert ctx.records("messungen") == []


@pytest.mark.parametrize(
    "path",
    [
        "../base.html",
        "/base.html",
        "inventur/../base.html",
        "inventur\\\\base.html",
        "inventur//base.html",
    ],
)
def test_plugin_templates_reject_unsafe_paths(db, app_definitions, path):
    from kurort_app.apps.context import AppContext

    with pytest.raises(ValueError):
        AppContext(None, db, AppRegistry().valid["geraetecheck"], None).render(path)
