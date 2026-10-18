"""Public definition contract, resilient registry and CLI diagnostics."""

import re
import sys
import types
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

FIXTURE = Path(__file__).parent / "fixtures/apps/geraetecheck.yaml"


def definition_data():
    data = yaml.safe_load(FIXTURE.read_text())
    data.pop("views")
    data.pop("demo")
    return data


def test_valid_definition_and_public_reference():
    from kurort_app.apps.schema import AppDefinition

    app = AppDefinition.model_validate(definition_data())
    assert app.slug == "geraetecheck"
    assert len(app.collections) == 2
    reference = Path("docs/apps/definition-format.md").read_text()
    block = re.search(r"```yaml\n(.*?)```", reference, re.S).group(1)
    data = yaml.safe_load(block)
    assert "views" not in data and "demo" not in data
    assert AppDefinition.model_validate(data).collections


@pytest.mark.parametrize(
    "case",
    [
        "reference",
        "range",
        "reserved",
        "role",
        "handler",
        "duplicate",
        "field",
        "schedule",
        "alert",
        "icon",
    ],
)
def test_invalid_definition_names_key(case):
    from kurort_app.apps.schema import AppDefinition

    data = deepcopy(definition_data())
    expected = ""
    match case:
        case "reference":
            data["collections"][1]["fields"][0]["collection"] = "unbekannt"
            expected = "geraet"
        case "range":
            data["collections"][1]["fields"][2]["range"]["min"] = {"from": "massnahme.soll_min"}
            expected = "temperatur"
        case "reserved":
            data["collections"][0]["key"] = "neu"
            expected = "neu"
        case "role":
            data["roles"]["view"] = ["hacker"]
            expected = "hacker"
        case "handler":
            data["views"] = [{"key": "unsafe", "title": "Unsafe", "handler": "os:system"}]
            expected = "handler"
        case "duplicate":
            data["collections"][0]["fields"].append(data["collections"][0]["fields"][0])
            expected = "name"
        case "field":
            data["collections"][0]["list_fields"] = ["missing"]
            expected = "missing"
        case "schedule":
            data["schedules"][0]["every_hours"] = 2
            expected = "taeglich"
        case "alert":
            data["alerts"][0]["field"] = "name"
            expected = "abgelaufen"
        case "icon":
            data["icon"] = "unknown"
            expected = "icon"
    with pytest.raises(ValueError, match=expected):
        AppDefinition.model_validate(data)


def test_registry_keeps_valid_and_broken_and_checks_filename(tmp_path):
    from kurort_app.apps.registry import AppRegistry

    (tmp_path / "geraetecheck.yaml").write_text(yaml.safe_dump(definition_data()))
    (tmp_path / "broken.yaml").write_text("slug: broken\nversion: nope")
    registry = AppRegistry([tmp_path])
    assert "geraetecheck" in registry.valid
    assert "broken" in registry.broken
    assert "broken.yaml" in " ".join(registry.broken["broken"])
    (tmp_path / "mismatch.yaml").write_text(yaml.safe_dump(definition_data()))
    registry = AppRegistry([tmp_path])
    assert "mismatch" in registry.broken


def test_duplicate_yaml_keys_are_not_silently_overwritten(tmp_path):
    from kurort_app.apps.registry import AppRegistry

    (tmp_path / "duplicate.yaml").write_text("slug: duplicate\nslug: duplicate\n")
    assert "doppelt" in " ".join(AppRegistry([tmp_path]).broken["duplicate"])


def test_cli_validate_fixtures(capsys):
    from kurort_app.cli import main

    assert main(["apps", "validate", str(FIXTURE)]) == 0
    assert "OK" in capsys.readouterr().out
    for path in sorted((FIXTURE.parent.parent / "apps_broken").glob("*.yaml")):
        assert main(["apps", "validate", str(path)]) == 1
        output = capsys.readouterr().out
        assert path.name in output


def test_cli_install_is_idempotent_and_lists_status(db, app_definitions, capsys):
    from sqlalchemy import select

    from kurort_app.apps.models import AppInstallation
    from kurort_app.cli import main
    from kurort_app.models import AuditEvent

    assert main(["apps", "install", "geraetecheck"]) == 0
    assert main(["apps", "install", "geraetecheck"]) == 0
    assert main(["apps", "list"]) == 0
    assert "geraetecheck\t1\tAktiv" in capsys.readouterr().out
    assert len(db.scalars(select(AppInstallation)).all()) == 1
    assert (
        len(db.scalars(select(AuditEvent).where(AuditEvent.action == "app.installed")).all()) == 1
    )


def test_plugins_resolve_only_inside_namespace(monkeypatch):
    from kurort_app.apps.schema import resolve_plugin

    plugin = types.ModuleType("kurort_app.apps.plugins.example")
    plugin.good = lambda ctx: None
    plugin.bad = "no"
    monkeypatch.setitem(sys.modules, plugin.__name__, plugin)
    assert callable(resolve_plugin("example:good"))
    for handler in ("os:system", "../os:system", "example:bad", "example:missing"):
        with pytest.raises(ValueError, match="handler"):
            resolve_plugin(handler)
