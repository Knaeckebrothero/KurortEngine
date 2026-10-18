"""The public, validated definition contract for small hotel apps."""

from __future__ import annotations

import importlib
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kurort_app.auth import ROLE_LABELS

KEY = r"^[a-z][a-z0-9_]*$"
RESERVED = {
    "neu",
    "bericht",
    "ansicht",
    "installieren",
    "aktivieren",
    "deaktivieren",
    "deinstallieren",
    "export",
}
NUMERIC = {"integer", "decimal"}
DATES = {"date", "datetime"}


def resolve_plugin(reference: str):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*:[A-Za-z_][A-Za-z0-9_]*", reference):
        raise ValueError(f"handler {reference}: erwartet module:function")
    module, name = reference.split(":")
    try:
        imported = importlib.import_module(f"kurort_app.apps.plugins.{module}")
    except ImportError as exc:
        raise ValueError(f"handler {reference}: Modul nicht verfügbar") from exc
    handler = getattr(imported, name, None)
    if not callable(handler):
        raise ValueError(f"handler {reference}: Funktion nicht verfügbar")
    return handler


class DefinitionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, allow_inf_nan=False)


class Roles(DefinitionModel):
    view: list[str] | None = None
    edit: list[str] | None = None

    @model_validator(mode="after")
    def known(self):
        for roles in (self.view, self.edit):
            for role in roles or []:
                if role not in ROLE_LABELS:
                    raise ValueError(f"roles: unbekannte Rolle {role}")
        return self


class Named(DefinitionModel):
    key: str = Field(pattern=KEY)


class Option(Named):
    label: str = Field(min_length=1)


class RangeSource(DefinitionModel):
    from_: str = Field(alias="from", pattern=r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")


class ExpectedRange(DefinitionModel):
    min: float | RangeSource | None = None
    max: float | RangeSource | None = None
    severity: Literal["warn", "block"] = "warn"


class AppField(Named):
    label: str = Field(min_length=1)
    type: Literal[
        "text",
        "textarea",
        "integer",
        "decimal",
        "date",
        "datetime",
        "time",
        "boolean",
        "select",
        "multiselect",
        "room",
        "staff",
        "reference",
    ]
    required: bool = False
    help: str = ""
    placeholder: str = ""
    default: Any = None
    max_length: int | None = Field(default=None, gt=0)
    min: float | None = None
    max: float | None = None
    decimals: int | None = Field(default=None, ge=0, le=20)
    unit: str = ""
    options: list[Option] = Field(default_factory=list)
    collection: str | None = None
    range: ExpectedRange | None = None
    require_when_out_of_range: list[str] = Field(default_factory=list)


class Collection(Named):
    title: str = Field(min_length=1)
    item: str = Field(min_length=1)
    master: bool = False
    title_field: str
    list_fields: list[str] = Field(default_factory=list)
    order_by: str = "created_at"
    date_field: str = "created_at"
    roles: Roles | None = None
    fields: list[AppField] = Field(min_length=1)

    def field(self, key: str) -> AppField:
        return next(f for f in self.fields if f.key == key)


class Schedule(Named):
    title: str
    target: str
    record: str
    via: str
    at_field: str = "created_at"
    every_days: int | None = Field(default=None, gt=0)
    every_days_field: str | None = None
    every_hours: float | None = Field(default=None, gt=0)
    when: str | None = None


class Alert(Named):
    title: str
    collection: str
    field: str
    offset_days: int = 0
    warn_days: int = Field(default=0, ge=0)
    unless: str | None = None


class ReportSection(DefinitionModel):
    collection: str
    columns: list[str] = Field(min_length=1)


class Report(Named):
    title: str
    sections: list[ReportSection] = Field(min_length=1)


class View(Named):
    title: str
    handler: str
    roles: Roles | None = None


def _unique(items, label):
    seen = set()
    for item in items:
        if item.key in seen:
            raise ValueError(f"{label}.{item.key}: Schlüssel doppelt")
        seen.add(item.key)


class AppDefinition(DefinitionModel):
    slug: str = Field(pattern=r"^[a-z][a-z0-9_]{1,30}$")
    version: int = Field(ge=1, strict=True)
    title: str = Field(min_length=1)
    description: str = ""
    icon: Literal["clipboard", "thermometer", "box", "broom", "cart", "list"] = "clipboard"
    roles: Roles
    collections: list[Collection] = Field(min_length=1)
    schedules: list[Schedule] = Field(default_factory=list)
    alerts: list[Alert] = Field(default_factory=list)
    reports: list[Report] = Field(default_factory=list)
    views: list[View] = Field(default_factory=list)
    demo: str | None = None

    def collection(self, key: str) -> Collection:
        return next(c for c in self.collections if c.key == key)

    @model_validator(mode="after")
    def crosscheck(self):
        if self.roles.view is None or self.roles.edit is None:
            raise ValueError("roles: view und edit erforderlich")
        for label in ("collections", "schedules", "alerts", "reports", "views"):
            _unique(getattr(self, label), label)
        collections = {c.key: c for c in self.collections}

        def collection(key, path):
            if key not in collections:
                raise ValueError(f"{path}: unbekannte collection {key}")
            return collections[key]

        def field(coll, key, path, types=None):
            found = next((f for f in coll.fields if f.key == key), None)
            if found is None or (types and found.type not in types):
                raise ValueError(f"{path}: ungültiges Feld {key}")
            return found

        for c in self.collections:
            if c.key in RESERVED:
                raise ValueError(f"collections.{c.key}: reservierter Schlüssel")
            _unique(c.fields, c.key)
            for key in [c.title_field, *c.list_fields]:
                field(c, key, c.key)
            order = c.order_by.removeprefix("-")
            if order != "created_at":
                field(c, order, c.key)
            if c.date_field != "created_at":
                field(c, c.date_field, c.key, DATES)
            for f in c.fields:
                path = f"{c.key}.{f.key}"
                _unique(f.options, path)
                if f.type == "reference":
                    collection(f.collection, path)
                elif f.collection is not None:
                    raise ValueError(f"{path}: collection nur bei reference")
                if f.type in {"select", "multiselect"} and not f.options:
                    raise ValueError(f"{path}: options fehlen")
                if f.min is not None and f.max is not None and f.min > f.max:
                    raise ValueError(f"{path}: min größer als max")
                if f.range:
                    if f.type not in NUMERIC:
                        raise ValueError(f"{path}: range nur bei Zahlen")
                    for bound in (f.range.min, f.range.max):
                        if isinstance(bound, RangeSource):
                            first, second = bound.from_.split(".")
                            ref = field(c, first, path, {"reference"})
                            field(collection(ref.collection, path), second, path, NUMERIC)
                    for key in f.require_when_out_of_range:
                        field(c, key, path)
                elif f.require_when_out_of_range:
                    raise ValueError(f"{path}: range fehlt")
        for s in self.schedules:
            path = f"schedules.{s.key}"
            target, records = collection(s.target, path), collection(s.record, path)
            via = field(records, s.via, path, {"reference"})
            if via.collection != s.target:
                raise ValueError(f"{path}: via zeigt nicht auf target")
            if s.at_field != "created_at":
                field(records, s.at_field, path, DATES)
            if sum(x is not None for x in (s.every_days, s.every_days_field, s.every_hours)) != 1:
                raise ValueError(f"{path}: genau ein Intervall erforderlich")
            if s.every_days_field:
                field(target, s.every_days_field, path, {"integer"})
            if s.when:
                field(target, s.when, path, {"boolean"})
        for a in self.alerts:
            path = f"alerts.{a.key}"
            c = collection(a.collection, path)
            field(c, a.field, path, DATES)
            if a.unless:
                field(c, a.unless, path, {"boolean"})
        for report in self.reports:
            for section in report.sections:
                c = collection(section.collection, f"reports.{report.key}")
                for key in section.columns:
                    field(c, key, f"reports.{report.key}")
        for view in self.views:
            resolve_plugin(view.handler)
        if self.demo:
            resolve_plugin(self.demo)
        return self
