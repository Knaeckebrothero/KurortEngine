"""Generic server-rendered app catalogue, records, reports and plugin routes."""

from __future__ import annotations

import inspect
from datetime import date, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from kurort_app import web
from kurort_app.apps import installations, reports, status, store, values
from kurort_app.apps.context import AppContext
from kurort_app.apps.models import AppInstallation
from kurort_app.apps.schema import resolve_plugin
from kurort_app.auth import require_role
from kurort_app.config import today
from kurort_app.db import get_session, get_sessionmaker
from kurort_app.models import AuditEvent, Room

router = APIRouter(prefix="/apps", tags=["apps"])
DB = Depends(get_session)
ADMIN = Depends(require_role("leitung"))
ICONS = {
    "clipboard": '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 3h6v4H9zM8 12h8M8 16h6"/>',
    "thermometer": '<path d="M9 14V5a3 3 0 0 1 6 0v9a5 5 0 1 1-6 0zM12 8v10"/>',
    "box": '<path d="M3 7l9-5 9 5v10l-9 5-9-5zM3 7l9 5 9-5M12 12v10"/>',
    "broom": '<path d="M18 3l-8 12M7 12l7 5-5 5-7-5zM5 16l4 3"/>',
    "cart": '<path d="M2 3h3l3 13h11l3-10H6"/><circle cx="9" cy="21" r="1"/><circle cx="18" cy="21" r="1"/>',
    "list": '<path d="M8 5h13M8 12h13M8 19h13M3 5h1M3 12h1M3 19h1"/>',
}
web.NAV.append(
    web.NavItem(
        "/apps",
        "Apps verwalten",
        ICONS["clipboard"],
        "Verwaltung",
        roles=("leitung",),
        match="/apps/verwaltung",
    )
)


def navigation(request):
    registry = request.app.state.apps
    with get_sessionmaker()() as session:
        installed = session.scalars(
            select(AppInstallation).where(AppInstallation.enabled.is_(True))
        ).all()
    return [
        web.NavItem(
            f"/apps/{row.slug}",
            app.title,
            ICONS[app.icon],
            "Apps",
            roles=tuple(set(app.roles.view) | {"leitung"}),
            match=f"/apps/{row.slug}"
            if request.url.path == f"/apps/{row.slug}"
            else f"/apps/{row.slug}/",
        )
        for row in installed
        if (app := registry.valid.get(row.slug))
    ]


web.NAV_PROVIDERS.append(navigation)


class AppUnavailable(Exception):
    def __init__(self, errors):
        self.errors = errors


async def unavailable_handler(request, exc):
    user = getattr(request.state, "user", None)
    errors = exc.errors if user is None or "leitung" in user.roles else []
    return web.templates.TemplateResponse(
        request, "apps/broken.html", {"errors": errors}, status_code=503
    )


def context(request, session, slug, collection=None, *, edit=False):
    registry = request.app.state.apps
    if slug in registry.broken:
        raise AppUnavailable(registry.broken[slug])
    app = registry.valid.get(slug)
    installed = session.get(AppInstallation, slug)
    if app is None or installed is None or not installed.enabled:
        raise HTTPException(404, "App nicht gefunden")
    ctx = AppContext(request, session, app, getattr(request.state, "user", None))
    if collection:
        if collection not in {c.key for c in app.collections}:
            raise HTTPException(404, "Sammlung nicht gefunden")
        ctx._require(collection, "edit" if edit else "view")
    elif not ctx.allowed("view"):
        raise HTTPException(403, "Keine Berechtigung")
    return ctx


def render(ctx, template, **data):
    app, session = ctx.definition, ctx.session
    return web.templates.TemplateResponse(
        ctx.request,
        f"apps/{template}.html",
        {
            "app": app,
            "ctx": ctx,
            "show_value": lambda row, key: store.display(
                session, app, app.collection(row.collection).field(key), row.data.get(key)
            ),
            "row_title": lambda row: store.title(session, app, row),
            **data,
        },
    )


@router.get("")
def catalog(request: Request, session: Session = DB, user=ADMIN):
    registry = request.app.state.apps
    installed = {row.slug: row for row in session.scalars(select(AppInstallation))}
    entries = []
    for slug, app in registry.valid.items():
        row = installed.get(slug)
        state = "Nicht installiert" if row is None else ("Aktiv" if row.enabled else "Deaktiviert")
        entries.append(
            {
                "slug": slug,
                "title": app.title,
                "description": app.description,
                "version": app.version,
                "state": state,
                "errors": [],
            }
        )
    entries.extend(
        {
            "slug": slug,
            "title": slug,
            "description": "Definition konnte nicht geladen werden.",
            "version": "–",
            "state": "Fehlerhaft",
            "errors": errors,
        }
        for slug, errors in registry.broken.items()
    )
    return web.templates.TemplateResponse(request, "apps/catalog.html", {"entries": entries})


@router.post("/{slug}/installieren")
@router.post("/{slug}/aktivieren")
@router.post("/{slug}/deaktivieren")
@router.post("/{slug}/deinstallieren")
def lifecycle(slug: str, request: Request, session: Session = DB, user=ADMIN):
    app = request.app.state.apps.valid.get(slug)
    if app is None:
        raise HTTPException(404, "App nicht gefunden")
    installations.change(session, app, request.url.path.rsplit("/", 1)[-1])
    session.commit()
    return web.redirect_with_notice("/apps", "App-Status geändert.")


def period(request):
    day = today()
    try:
        start = date.fromisoformat(
            request.query_params.get("von") or day.replace(day=1).isoformat()
        )
        end = date.fromisoformat(request.query_params.get("bis") or day.isoformat())
    except ValueError as exc:
        raise HTTPException(422, "Bitte einen gültigen Zeitraum wählen.") from exc
    if end < start:
        raise HTTPException(422, "Das Ende liegt vor dem Beginn.")
    return start, end


def permitted_reports(ctx):
    return [
        r for r in ctx.definition.reports if all(ctx.can_view(s.collection) for s in r.sections)
    ]


def selected_report(ctx):
    choices = permitted_reports(ctx)
    key = ctx.request.query_params.get("bericht")
    selected = (
        next((r for r in choices if r.key == key), None)
        if key
        else (choices[0] if choices else None)
    )
    if selected is None and key:
        raise HTTPException(404, "Bericht nicht gefunden")
    return choices, selected


@router.get("/{slug}/bericht")
def report_page(slug: str, request: Request, session: Session = DB):
    ctx = context(request, session, slug)
    start, end = period(request)
    previous_end = today().replace(day=1) - timedelta(days=1)
    choices, selected = selected_report(ctx)
    return render(
        ctx,
        "report",
        reports=choices,
        selected=selected,
        start=start,
        end=end,
        previous_start=previous_end.replace(day=1),
        previous_end=previous_end,
    )


@router.get("/{slug}/bericht.pdf")
def pdf(slug: str, request: Request, session: Session = DB):
    ctx = context(request, session, slug)
    _, report = selected_report(ctx)
    if report is None:
        raise HTTPException(404, "Bericht nicht gefunden")
    start, end = period(request)
    content = reports.pdf_export(
        session, ctx.definition, report, start, end, ctx.user.username if ctx.user else "rezeption"
    )
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{slug}-{report.key}-{start}-{end}.pdf"'
        },
    )


@router.api_route("/{slug}/ansicht/{view}", methods=["GET", "POST"])
async def plugin(slug: str, view: str, request: Request, session: Session = DB):
    ctx = context(request, session, slug)
    definition = next((v for v in ctx.definition.views if v.key == view), None)
    if definition is None:
        raise HTTPException(404, "Ansicht nicht gefunden")
    if not ctx.allowed("view", definition.roles):
        raise HTTPException(403, "Keine Berechtigung")
    result = resolve_plugin(definition.handler)(ctx)
    return await result if inspect.isawaitable(result) else result


@router.get("/{slug}")
def home(slug: str, request: Request, session: Session = DB):
    ctx = context(request, session, slug)
    app = ctx.definition
    rows = [r for r in store.records(session, app) if ctx.can_view(r.collection)]
    schedule_app = app.model_copy(
        update={
            "schedules": [
                s for s in app.schedules if ctx.can_view(s.target) and ctx.can_view(s.record)
            ]
        }
    )
    due = [
        s
        for s in status.schedules(
            schedule_app, rows, today=today(), now=status.business_now(today())
        )
        if s.status != "erledigt"
    ]
    due_editable = {s.href: ctx.can_edit(s.href.split("/")[3]) for s in due}
    cards = [
        {"collection": c, "count": sum(r.collection == c.key for r in rows)}
        for c in app.collections
        if ctx.can_view(c.key)
    ]
    return render(
        ctx,
        "home",
        due=due,
        due_editable=due_editable,
        alerts=status.alerts(app, rows, today=today()),
        deviations=status.deviations(rows, today=today()),
        cards=[c for c in cards if not c["collection"].master],
        masters=[c for c in cards if c["collection"].master],
        views=[v for v in app.views if ctx.allowed("view", v.roles)],
        reports_allowed=bool(permitted_reports(ctx)),
    )


@router.get("/{slug}/{collection}/export.csv")
def csv_download(slug: str, collection: str, request: Request, session: Session = DB):
    ctx = context(request, session, slug, collection)
    start, end = period(request)
    columns = None
    if request.query_params.get("bericht"):
        _, report = selected_report(ctx)
        section = next((s for s in report.sections if s.collection == collection), None)
        if section is None:
            raise HTTPException(404, "Abschnitt nicht gefunden")
        columns = section.columns
    content = reports.csv_export(session, ctx.definition, collection, start, end, columns=columns)
    return Response(
        content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{slug}-{collection}-{start}-{end}.csv"'
        },
    )


def form_options(ctx, collection):
    options = {}
    for field in collection.fields:
        if field.type == "reference":
            options[field.key] = (
                [
                    (str(r.id), store.title(ctx.session, ctx.definition, r))
                    for r in ctx.records(field.collection)
                ]
                if ctx.can_view(field.collection)
                else []
            )
        elif field.type == "room":
            options[field.key] = [
                (r.number, r.number)
                for r in ctx.session.scalars(select(Room).order_by(Room.number))
            ]
        else:
            options[field.key] = [(o.key, o.label) for o in field.options]
    return options


def existing(ctx, collection, id):
    row = store.record(ctx.session, ctx.definition, collection, id)
    if row is None:
        raise HTTPException(404, "Eintrag nicht vorhanden")
    return row


@router.api_route("/{slug}/{collection}/neu", methods=["GET", "POST"])
@router.api_route("/{slug}/{collection}/{id:int}/bearbeiten", methods=["GET", "POST"])
async def form(
    slug: str, collection: str, request: Request, id: int | None = None, session: Session = DB
):
    ctx = context(request, session, slug, collection, edit=True)
    coll = ctx.definition.collection(collection)
    row = existing(ctx, collection, id) if id is not None else None
    errors = {}
    if request.method == "POST":
        posted = await request.form()
        data = {
            f.key: posted.getlist(f.key)
            if f.type == "multiselect"
            else posted.get(f.key, False if f.type == "boolean" else "")
            for f in coll.fields
        }
        try:
            if row:
                store.update(session, ctx.definition, row, data)
            else:
                row = store.create(session, ctx.definition, coll, data)
            session.commit()
            notice = f"{coll.item} gespeichert" + (
                " – Abweichung dokumentiert." if row.out_of_range else "."
            )
            return web.redirect_with_notice(f"/apps/{slug}/{collection}/{row.id}", notice)
        except store.RecordValidationError as exc:
            errors = exc.errors
    else:
        data = (
            {f.key: values.form_value(f, row.data.get(f.key)) for f in coll.fields}
            if row
            else values.defaults(coll, ctx.user.username if ctx.user else "rezeption")
        )
        if row is None:
            for field in coll.fields:
                if field.key in request.query_params:
                    data[field.key] = (
                        request.query_params.getlist(field.key)
                        if field.type == "multiselect"
                        else request.query_params[field.key]
                    )
    response = render(
        ctx,
        "form",
        collection=coll,
        row=row,
        data=data,
        errors=errors,
        options=form_options(ctx, coll),
        action=request.url.path,
    )
    response.status_code = 422 if errors else 200
    return response


@router.post("/{slug}/{collection}/{id:int}/loeschen")
def delete(slug: str, collection: str, id: int, request: Request, session: Session = DB):
    ctx = context(request, session, slug, collection, edit=True)
    store.delete(session, ctx.definition, existing(ctx, collection, id))
    session.commit()
    return web.redirect_with_notice(f"/apps/{slug}/{collection}", "Eintrag gelöscht.")


@router.get("/{slug}/{collection}/{id:int}")
def detail(slug: str, collection: str, id: int, request: Request, session: Session = DB):
    ctx = context(request, session, slug, collection)
    app = ctx.definition
    row = existing(ctx, collection, id)
    related = []
    for coll in app.collections:
        if not ctx.can_view(coll.key):
            continue
        for field in coll.fields:
            if field.type == "reference" and field.collection == collection:
                linked = store.records(session, app, coll.key, {field.key: id})
                linked.sort(key=lambda r: (r.created_at, r.id), reverse=True)
                if linked:
                    related.append(
                        {
                            "collection": coll,
                            "rows": linked[:20],
                            "url": f"/apps/{slug}/{coll.key}?{urlencode({field.key: id})}",
                        }
                    )
    history = session.scalars(
        select(AuditEvent)
        .where(AuditEvent.entity == "app_record", AuditEvent.entity_id == str(id))
        .order_by(AuditEvent.at.desc())
    ).all()
    coll = app.collection(collection)
    legacy = {k: v for k, v in row.data.items() if k not in {f.key for f in coll.fields}}
    return render(
        ctx, "detail", collection=coll, row=row, history=history, related=related, legacy=legacy
    )


@router.get("/{slug}/{collection}")
def listing(slug: str, collection: str, request: Request, session: Session = DB):
    ctx = context(request, session, slug, collection)
    coll = ctx.definition.collection(collection)
    filters = {k: request.query_params.get(k, "") for k in ("q", "von", "bis", "abweichungen")}
    try:
        page = max(1, int(request.query_params.get("page", 1)))
        where = {
            f.key: values.serialize(f, request.query_params[f.key])
            for f in coll.fields
            if f.key in request.query_params
        }
        rows = store.query(
            session,
            ctx.definition,
            coll,
            q=filters["q"],
            von=filters["von"] or None,
            bis=filters["bis"] or None,
            deviations=filters["abweichungen"] in {"1", "true", "on"},
            where=where,
        )
    except ValueError as exc:
        raise HTTPException(422, "Bitte die Filter prüfen.") from exc
    page_rows = rows[(page - 1) * 50 : page * 50]
    next_url = (
        f"{request.url.path}?{urlencode({**dict(request.query_params), 'page': page + 1})}"
        if len(rows) > page * 50
        else None
    )
    alert_by_id = {}
    for item in status.alerts(ctx.definition, page_rows, today=today()):
        alert_by_id.setdefault(item.record.id, []).append(item)
    return render(
        ctx,
        "_rows" if request.headers.get("HX-Request") == "true" else "list",
        collection=coll,
        page=page,
        rows=page_rows,
        next_url=next_url,
        filters=filters,
        has_range=any(f.range for f in coll.fields),
        alert_by_id=alert_by_id,
    )
