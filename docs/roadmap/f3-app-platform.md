# F3: App platform

| | |
|---|---|
| Wave | 1 |
| Depends on | – (branch from today's `main`) |
| Branch | `feature/f3-app-platform` |
| Migration | `0003_app_platform` (revision id `"0003_app_platform"`, `down_revision = "0001"`) |
| Size | L |

## Why

The owner proposed, and the manager liked, an **"Apps" area in the sidebar**
where small hotel apps plug in. About 95 % of them are CRUD: a form in, a list
and a report out. The first two are already waiting: the owner's HACCP
prototype (F7) and an inventory and ordering app (F8). Writing each as a new
router with its own tables, migration and templates repeats the same work
every time and keeps every new app a developer job.

The platform makes an app a **declarative definition**: one YAML file that
names the collections, fields, validation ranges, due schedules, date alerts
and reports. The core renders forms, lists, the app's start page and PDF/CSV
reports from it. Because it is data, a later assistant (or SRW) can write a
definition from a description; that authoring step is not built now, but the
format is documented as a stable public reference so it can be.

## What to build

- A definition format (pydantic schema) and a registry that loads YAML
  definitions shipped in the package, plus extra directories for tests.
- Two tables: installations and records (JSONB). No migration per app.
- Screens: app catalogue for `leitung`, the app's start page, list, form,
  detail, report page; an "Apps" sidebar section.
- Schedules ("each device needs a reading every day"), date alerts ("use by"),
  out-of-range flags ("Abweichung") with a required corrective action.
- PDF reports (reportlab) and CSV export for a date range.
- A small code-plugin hook for the 5 % that is not CRUD (F8's order
  suggestion) and a demo-data hook so each app seeds its own records.
- CLI: `kurort-app apps list|validate|install`.
- The public reference `docs/apps/definition-format.md`.

## Scope

Everything in "What to build", with one test fixture app (not HACCP).

## Not in scope

- HACCP and inventory definitions (F7, F8).
- Authoring apps in the browser or by the assistant.
- Data migrations between definition versions (see Rules: versions).
- File or photo fields, signatures, computed fields, formulas, multi-level
  references (`a.b.c`), per-record permissions, notifications or e-mail.
- Showing app warnings on the front-desk dashboard or as sidebar counters.
- Any change to `auth.py`, `deploy/` or the engine library.

## Data model

Migration `src/kurort_app/migrations/versions/0003_app_platform.py`. Note that
the existing first migration's revision id is `"0001"` (file
`0001_initial_schema.py`), so `down_revision = "0001"`.

`app_installations`

| Column | Type | Notes |
|---|---|---|
| `slug` | `String(40)` PK | the definition's slug |
| `version` | `Integer` not null | definition version at install time |
| `enabled` | `Boolean` not null, default true | |
| `installed_at` | `DateTime(tz)` not null, default now() | |
| `installed_by` | `String(60)` not null | username or `rezeption` (auth off) |

`app_records`

| Column | Type | Notes |
|---|---|---|
| `id` | `BigInteger` PK | |
| `app_slug` | `String(40)` not null | no foreign key: uninstalling keeps records |
| `collection` | `String(40)` not null | collection key |
| `data` | `JSONB` not null, default `{}` | field values, see storage formats |
| `out_of_range` | `Boolean` not null, default false | judged at save time |
| `definition_version` | `Integer` not null | version used at the last write |
| `created_at` / `created_by` | `DateTime(tz)` default now() / `String(60)` | |
| `updated_at` / `updated_by` | nullable | |
| `deleted_at` / `deleted_by` | nullable | soft delete |

Indexes: `(app_slug, collection, deleted_at)`, `created_at`, and
`GIN (data jsonb_path_ops)`. Models `AppInstallation` and `AppRecord` live in
`src/kurort_app/apps/models.py` (on the shared `Base`; import them in
`migrations/env.py` next to `kurort_app.models`), not in `models.py`, to keep
merges with the other wave-1 features clean.

**Storage formats in `data`** (one per field type; `values.py` converts both
ways):

| Type | Stored as | Form input |
|---|---|---|
| `text`, `textarea` | string | `<input>` / `<textarea>` |
| `integer` | JSON number | `inputmode="numeric"` |
| `decimal` | string, `"3.5"` (exact `Decimal`) | `inputmode="decimal"`, German comma accepted |
| `date` | `"2026-10-14"` | `type="date"` |
| `datetime` | ISO 8601 in UTC, `"2026-10-14T05:30:00+00:00"` | `type="datetime-local"`, read as Europe/Berlin |
| `time` | `"07:30"` | `type="time"` |
| `boolean` | `true`/`false` | checkbox |
| `select` | option key | `<select>` (radio buttons when ≤ 3 options) |
| `multiselect` | list of option keys | checkboxes |
| `room` | room number string, must exist in `rooms` | `<select>` of rooms |
| `staff` | string (username) | text input, default the current username |
| `reference` | record id (number) of a non-deleted record in the same app | `<select>` labelled by the target's `title_field` |

Missing or empty values are absent from `data` (not `null`).

## The definition format

One file per app: `src/kurort_app/apps/definitions/<slug>.yaml`, loaded with
`yaml.safe_load` and validated by pydantic models in `apps/schema.py`.
Abridged example (the full reference goes into `docs/apps/definition-format.md`):

```yaml
slug: geraetecheck            # ^[a-z][a-z0-9_]{1,30}$, equals the file stem
version: 1                    # integer >= 1, bump on every change
title: Gerätecheck
description: Kühlgeräte täglich prüfen.
icon: thermometer             # one of: clipboard, thermometer, box, broom, cart, list
roles:                        # leitung is always allowed and need not be listed
  view: [rezeption]
  edit: [rezeption]
collections:
  - key: geraete
    title: Geräte
    item: Gerät               # singular, used in buttons: "Gerät erfassen"
    master: true              # master data: shown under "Stammdaten" on the start page
    title_field: name
    list_fields: [name, soll_min, soll_max]
    order_by: name            # field key or created_at; "-" prefix = descending
    roles: { edit: [] }       # optional override of the app roles (here: only leitung)
    fields:
      - { key: name, label: Name, type: text, required: true, max_length: 80 }
      - { key: soll_min, label: "Soll min", type: decimal, decimals: 1, unit: "°C" }
      - { key: soll_max, label: "Soll max", type: decimal, decimals: 1, unit: "°C" }
      - { key: aktiv, label: Aktiv, type: boolean, default: true }
      - { key: pruefung_bis, label: "Prüfung gültig bis", type: date }
      - { key: ausgemustert, label: Ausgemustert, type: boolean }
  - key: messungen
    title: Messungen
    item: Messung
    title_field: geraet
    date_field: gemessen_am   # period filter for lists, exports and reports; default created_at
    list_fields: [gemessen_am, geraet, temperatur]
    order_by: -gemessen_am
    fields:
      - { key: geraet, label: Gerät, type: reference, collection: geraete, required: true }
      - { key: gemessen_am, label: Zeitpunkt, type: datetime, required: true, default: now }
      - key: temperatur
        label: Temperatur
        type: decimal
        decimals: 1
        unit: "°C"
        required: true
        min: -40              # plausible input limits: always blocking
        max: 100
        range:                # expected range: decides "Abweichung"
          min: { from: geraet.soll_min }   # a number, or a numeric field of the referenced record
          max: { from: geraet.soll_max }
          severity: warn      # warn = save flagged; block = refuse
        require_when_out_of_range: [massnahme]
      - { key: massnahme, label: Maßnahme, type: textarea }
      - { key: mitarbeiter, label: Mitarbeiter, type: staff, default: current_user }
schedules:
  - key: taeglich
    title: Temperatur prüfen
    target: geraete           # every (active) record of this collection ...
    record: messungen         # ... needs a record here ...
    via: geraet               # ... whose reference field points to it ...
    at_field: gemessen_am     # ... dated by this field (default created_at) ...
    every_days: 1             # ... this often. Or every_days_field: <integer field of target>, or every_hours: N
    when: aktiv               # optional boolean field of the target that must be true
alerts:
  - key: abgelaufen
    title: Prüfplakette
    collection: geraete
    field: pruefung_bis       # date or datetime field
    offset_days: 0            # deadline = field + offset_days
    warn_days: 30             # "läuft ab" from deadline - warn_days
    unless: ausgemustert      # optional boolean field that silences the alert when true
reports:
  - key: monat
    title: Temperaturprotokoll
    sections:
      - collection: messungen
        columns: [gemessen_am, geraet, temperatur, mitarbeiter, massnahme]
views:                        # code plugins, optional
  - key: auswertung
    title: Auswertung
    handler: geraetecheck:auswertung   # module:function inside kurort_app.apps.plugins
demo: geraetecheck:seed_demo  # optional demo-data hook, same lookup
```

Other field keys: `help` (hint under the input), `placeholder`, `options` for
`select`/`multiselect` as a list of `{key, label}`, `max_length` for text,
`decimals` and `unit` for numbers. `default` is a literal or one of `today`,
`today+N` (N days), `now`, `current_user`. A `title_field` that is a
reference shows the referenced record's title ("Kühlschrank Küche").

**Validation** (`apps/schema.py` plus a cross-check pass) rejects a definition
when: the slug differs from the file stem; keys are duplicated or not
`^[a-z][a-z0-9_]*$`; a collection key is reserved (`neu`, `bericht`,
`ansicht`, `installieren`, `aktivieren`, `deaktivieren`, `deinstallieren`,
`export`); a referenced collection, field, `title_field`, `list_fields` entry,
`order_by`, `date_field`, report column or `require_when_out_of_range` field
does not exist; `range.from` is not `<reference field>.<numeric field of its
target>`; `range` sits on a non-numeric field; a schedule's `via` is not a
reference to `target`, its `at_field` is not a date/datetime of `record`, or
it sets none or more than one of `every_days`/`every_days_field`/`every_hours`;
an alert field is not date/datetime; `when`/`unless` are not boolean fields; a
role is not a key of `auth.ROLE_LABELS`; a `handler`/`demo` string is not
`module:function` with identifier characters, or the module cannot be imported
from `kurort_app.apps.plugins`, or the attribute is not callable.

## Package layout

```
src/kurort_app/apps/
  __init__.py
  schema.py       pydantic models + cross-checks, AppDefinition
  registry.py     load definitions; AppRegistry with .valid and .broken (slug -> errors)
  values.py       parse form input / serialize / display per field type
  store.py        create, update, delete, query records: validation + audit (router and plugins use it)
  status.py       schedules, alerts, recent deviations (pure functions taking today/now)
  reports.py      PDF (reportlab platypus) and CSV
  models.py       AppInstallation, AppRecord
  plugins/__init__.py
  definitions/    YAML files (empty in F3; F7 and F8 add theirs)
src/kurort_app/routers/apps.py
src/kurort_app/templates/apps/  catalog, home, list, _rows, form, _field, detail, report, broken
src/kurort_app/static/apps.css
```

The registry loads `definitions/` plus every directory in
`KURORT_APP_DEFINITION_DIRS` (new setting in `config.py`, `os.pathsep`
separated, default empty; tests point it at `tests/app/fixtures/apps/`). It is
built once in `create_app` and kept on `app.state.apps`.

## Screens and routes

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/apps` | leitung | Catalogue: every shipped app with status and actions |
| POST | `/apps/{slug}/installieren` · `/aktivieren` · `/deaktivieren` · `/deinstallieren` | leitung | Change the installation |
| GET | `/apps/{slug}` | app view | Start page |
| GET | `/apps/{slug}/{collection}` | view | List (htmx partial when `HX-Request`) |
| GET | `/apps/{slug}/{collection}/export.csv?von=&bis=` | view | CSV export |
| GET / POST | `/apps/{slug}/{collection}/neu` | edit | Form; query parameters prefill fields (`?geraet=3`) |
| GET | `/apps/{slug}/{collection}/{id}` | view | Detail |
| GET / POST | `/apps/{slug}/{collection}/{id}/bearbeiten` | edit | Edit |
| POST | `/apps/{slug}/{collection}/{id}/loeschen` | edit | Soft delete |
| GET | `/apps/{slug}/bericht` | view | Report page: report and period |
| GET | `/apps/{slug}/bericht.pdf?bericht=&von=&bis=` | view | PDF download |
| GET / POST | `/apps/{slug}/ansicht/{view}` | view (or the view's own `roles`) | Plugin view |

Register the fixed paths before the parametrised ones; `{id}` is an `int`.

**Sidebar.** Through the hooks in `web.py`, not by editing `base.html`:
`routers/apps.py` appends to `web.NAV_PROVIDERS` a function that returns one
`NavItem(f"/apps/{slug}", title, icon, "Apps", roles=<the app's view roles +
leitung>)` per installed, enabled, valid app (one query on
`app_installations` per request), and does
`NAV.append(NavItem("/apps", "Apps verwalten", <icon>, "Verwaltung",
roles=("leitung",), match="/apps"))`. `nav_groups` already hides empty groups,
filters by role and shows everything with login off. Because `/apps/haccp`
also starts with `/apps`, give "Apps verwalten" `match="/apps"` only if the
active-link check stays correct; otherwise set `match` to a path no app link
uses and test that only the right link is marked active.

**Catalogue `/apps`.** One row per shipped definition: title, description,
version, status (*Nicht installiert*, *Aktiv*, *Deaktiviert*, *Fehlerhaft*)
and the actions that fit. A broken definition shows its errors in a
`<details>` and cannot be installed. Uninstalling asks for confirmation inline
(a `<details>` "Deinstallieren …" with the real button inside, no JavaScript
dialog) and says that records are kept.

**Start page `/apps/{slug}`.** Top to bottom: *Fällig* (schedule items due or
overdue, each with "Jetzt erfassen" → the `neu` form with the reference
prefilled), *Warnungen* (alerts: *läuft ab* / *abgelaufen*, linked to the
record), *Abweichungen* (records flagged in the last 7 days), then one card
per non-master collection (title, number of records, "<Item> erfassen",
"Alle anzeigen"), plugin views and "Berichte". Master collections sit in a
closed `<details>` *Stammdaten*. An empty panel is left out; when nothing is
due and nothing warns, show "Alles erledigt." On a phone the panels stack and
the buttons are full width.

**List.** Columns: `list_fields` (at most 4 shown; the rest on the detail
page), an *Abweichung* badge, an alert badge. Filters: search `q` (case-
insensitive over the record's values), `von`/`bis` on the `date_field`, "Nur
Abweichungen" (only when the collection has a `range`). Sorted by `order_by`,
50 rows per page, "Weitere anzeigen" loads the next page via htmx. Below
860 px the table becomes stacked cards (reuse the `.fd-queue` pattern).

**Form.** One column, labels above inputs, `help` below, 44 px targets,
German error text next to the field and a summary at the top; on error the
form re-renders with status 422 and the entered values. Save redirects to the
detail page with a notice ("Messung gespeichert."; with a deviation:
"Messung gespeichert – Abweichung dokumentiert.").

**Detail.** All fields with labels and units, *Abweichung* badge, created and
changed by/at, "Bearbeiten", "Löschen" (inline confirmation as above), the
record's audit history, and *Verknüpfte Einträge*: records of the same app
whose reference field points here (per collection, newest 20, link to the
filtered list). Fields present in `data` but not in the current definition
appear read-only under "Weitere Felder (ältere Version)".

**Report page.** Select the report, `von`/`bis` (default: first of the current
month to today, business date), a "Vormonat" link, buttons "PDF" and, per
section, "CSV".

## Rules

- **Access.** View and edit are checked per app, overridden per collection
  when the collection sets `roles`. `leitung` may always do everything. With
  `KURORT_AUTH=off` everything is allowed. No view right → 403; app not
  installed or disabled → 404 "App nicht gefunden"; app broken → 503 page
  "Diese App ist gerade nicht verfügbar" (errors visible to `leitung` only).
  Buttons the user may not use are not rendered.
- **Validation order** for a save: parse each field by type, then `required`,
  `max_length`, `min`/`max`, select options, reference and room existence,
  then `range`. `range` with `severity: block` refuses the save ("Wert
  außerhalb des zulässigen Bereichs (0,0 bis 7,0 °C)."). With `warn`, the
  record is saved with `out_of_range = true`, but only if every field in
  `require_when_out_of_range` is filled; otherwise 422 with "Bei einer
  Abweichung ist „Maßnahme" Pflicht." A range bound taken `from` a referenced
  record that is empty leaves that side open.
- **Out-of-range is judged at save time** and stored; later changes to a
  device's limits do not rewrite old records. Editing re-judges.
- **Schedules** (computed in `status.py` from `today` and `now`, both
  injectable for tests). For `every_days`/`every_days_field`: last = the
  latest `at_field` date among non-deleted records pointing to the target;
  due date = last + interval. Status *erledigt* while today < due date,
  *fällig* on the due date, *überfällig* after it; no record yet →
  *überfällig* with "noch nie erfasst". For `every_hours`: *überfällig* when
  now > last + interval, else *erledigt*. Targets with `when` false or
  deleted are skipped.
- **Alerts:** deadline = field + `offset_days`. *abgelaufen* when today >
  deadline; *läuft ab* when today ≥ deadline − `warn_days`; else nothing.
  Silenced when the `unless` field is true. Deleted records never alert.
- **Defaults:** `today`/`today+N` use `config.today()`; `now` is the business
  date combined with the current Europe/Berlin time (so pinned demo dates
  stay consistent); `current_user` is the logged-in username, or `rezeption`
  with login off. Query parameters on `neu` override defaults.
- **Soft delete** hides the record everywhere (lists, start page, schedules,
  alerts, back-references, reports, exports); its detail URL answers 404.
- **Versions.** The shipped definition is the only one rendered. A write
  stores the current `version` in `definition_version`. Values whose field
  was removed are kept in `data`, shown read-only and preserved on edit.
  A value that no longer parses as the field's new type is shown as text and
  must be corrected on the next edit. There is no data-migration engine;
  `app_installations.version` records the version at install time for a
  later one. Authoring rule (documented): never reuse a removed field key with
  a different type.
- **Plugins.** `handler: "<module>:<function>"` resolves to
  `kurort_app.apps.plugins.<module>.<function>` only; anything else is a
  validation error. The function gets an `AppContext` (request, session, the
  definition, user, `can_view(collection)`, `can_edit(collection)`,
  `records(collection, where=None)`, `create(collection, data)`,
  `update(record, data)`, `value(record, field)` for typed values,
  `render(template, **context)` for templates under `templates/apps/plugins/`)
  and returns a response; it handles GET and POST. `create`/`update` run the
  same validation and audit as the form, raise `RecordValidationError`
  (field → German message) on bad data, and flush without committing, so a
  plugin can save several records in one transaction and commit once.
- **Demo hook.** `seed_demo_data(..., reset=True)` already empties every
  table (including `app_records` and `app_installations`). After the base
  demo data it installs every valid shipped app and runs its `demo` hook as
  `fn(session, anchor_date)`. With no
  definitions shipped (F3 alone) the seed behaves as today. F7 and F8 add
  their demo data through this hook, not by editing `seed.py`. Demo hooks
  write through `store.create(session, app, collection, data, actor=...,
  created_at=...)`, which accepts an explicit actor and creation time for
  seeding.
- **Reports.** A4 portrait, landscape above 5 columns; header with hotel
  name, report title, period, "Erstellt am … von …"; one table per section
  with the column labels; *Abweichung* rows marked in text; the signature
  lines of the prototype ("Unterschrift Verantwortliche/r", "Datum") at the
  end. Text goes through a cp1252 fallback like `_pdf_text` in
  `services/checkin_pdf.py` (WinAnsi fonts); copy those ~15 lines into
  `apps/reports.py`, because F1 deletes `checkin_pdf.py` in parallel.
  Filename `<slug>-<report>-<von>-<bis>.pdf`.
- **CSV:** `;` separator, UTF-8 with BOM, header row with labels, dates
  `14.10.2026`, datetimes `14.10.2026 07:30` (Europe/Berlin), decimals with
  a comma, booleans `ja`/`nein`, references and selects as their labels, a
  final column `Abweichung`.
- **Audit:** `app.installed`, `app.enabled`, `app.disabled`,
  `app.uninstalled` (entity `app`, id = slug); `app_record.created`,
  `app_record.updated`, `app_record.deleted` (entity `app_record`, id = record
  id, payload `{app, collection, changes: {field: [old, new]}}`), summary
  in German, e.g. "Gerätecheck · Messung angelegt: Kühlschrank Küche 8,5 °C
  (Abweichung)".

## CLI

`kurort-app apps list` (slug, version, status), `kurort-app apps validate
[PATH ...]` (default: all registry directories; prints `OK <file>` or each
error; exit 1 on any error), `kurort-app apps install <slug>` (idempotent).

## Acceptance criteria

1. **AC-1** Migration `0003_app_platform` creates both tables with the
   columns and indexes above on a database at `0001`; `downgrade()` removes
   them.
2. **AC-2** With a valid and an invalid fixture definition on the registry
   path, `create_app()` starts; the valid app works; the invalid one is listed
   in `/apps` as *Fehlerhaft* with its errors, and `/apps/<slug>` answers 503.
3. **AC-3** `kurort-app apps validate` exits 0 for the valid fixtures and 1
   for each of: unknown reference collection, `range.from` through a
   non-reference field, reserved collection key, unknown role, plugin handler
   outside `kurort_app.apps.plugins`; each error names the file and key.
4. **AC-4** `leitung` installs, disables, enables and uninstalls an app from
   `/apps`; each step writes the audit event; a disabled or uninstalled app
   answers 404 and leaves the sidebar; records survive uninstall and show
   again after reinstall. A `rezeption` user gets 403 on `/apps`.
5. **AC-5** The sidebar shows *Apps* with exactly the installed, enabled,
   valid apps the user may view, and "Apps verwalten" only for `leitung`; no
   *Apps* heading when none is visible.
6. **AC-6** Creating a record through the form stores every field type in
   its storage format, redirects to the detail page with the notice, and
   writes `app_record.created` with the logged-in username as actor.
7. **AC-7** A missing required field, a text over `max_length`, a number
   outside `min`/`max`, an unknown select option and a non-existent reference
   or room each give 422 with the German message, and nothing is stored.
8. **AC-8** A temperature outside a `warn` range taken from the referenced
   device: without *Maßnahme* → 422 with "Bei einer Abweichung ist
   „Maßnahme" Pflicht."; with it → saved, `out_of_range = true`,
   *Abweichung* in list and detail. A `block` range refuses with the range in
   the message. An empty device limit leaves that side open.
9. **AC-9** Editing updates the values, `updated_at/by` and
   `definition_version`, writes old and new values into the audit payload,
   and keeps values of fields no longer in the definition (shown under
   "Weitere Felder (ältere Version)").
10. **AC-10** Deleting soft-deletes: the record disappears from list, start
    page, schedules, alerts, reports and CSV; its URL answers 404; the audit
    event is written.
11. **AC-11** The list filters by `q`, `von`/`bis` and "Nur Abweichungen",
    returns only the rows partial for htmx requests, pages at 50, and orders
    by `order_by` (descending with `-`), including decimal and datetime keys.
12. **AC-12** Schedule statuses for fixed `today`/`now`: never recorded →
    *überfällig* "noch nie erfasst"; recorded yesterday with `every_days: 1`
    → *fällig*; two days ago → *überfällig*; `every_days_field` read per
    target; `when: aktiv` false → skipped; `every_hours` both states. The
    start page lists due items with a "Jetzt erfassen" link whose form has the
    reference preselected.
13. **AC-13** Alert statuses for fixed `today`: *läuft ab* inside
    `warn_days`, *abgelaufen* after the deadline, none before the window,
    none when `unless` is true; shown on the start page and as a list badge.
14. **AC-14** `bericht.pdf` returns `application/pdf` with the filename
    above and contains only records of the period (test the row builder
    directly, and that the bytes start with `%PDF-`). `export.csv` matches
    the CSV rules byte for byte for a small fixture set.
15. **AC-15** The fixture app's plugin view renders at
    `/apps/geraetecheck/ansicht/auswertung`; `ctx.create(...)` with an
    invalid value raises `RecordValidationError` with the same message as the
    form; with a valid one it writes the audit event.
16. **AC-16** A user with view but not edit right sees no "erfassen",
    "Bearbeiten" or "Löschen" and gets 403 on the POST routes; a collection
    `roles` override restricts master data to `leitung`; with login off every
    action is allowed.
17. **AC-17** `seed_demo_data(reset=True)` with the fixture app on the path
    empties the app tables, installs the app and runs its demo hook; without
    any shipped definition it creates exactly what it creates today.
18. **AC-18** `docs/apps/definition-format.md` documents every key above; its
    first ```` ```yaml ```` block is a complete example without `views` and
    `demo`, and a test extracts that block and validates it with the schema.
19. **AC-19** The detail page of a device lists its readings under
    *Verknüpfte Einträge*; `neu?<field>=<value>` prefills; `today+3`, `now`
    and `current_user` defaults fill the form.
20. **AC-20** All new screens render at 390 px without horizontal scrolling
    (screenshots per roadmap rule 6).

## Tests

- `tests/app/fixtures/apps/geraetecheck.yaml` (valid: master collection,
  reference with `range.from`, schedule, alert, report, view, demo hook) and
  `tests/app/fixtures/apps_broken/*.yaml` (one file per AC-3 error). Tests
  set `KURORT_APP_DEFINITION_DIRS` before building the app. The fixture's
  plugin code (`tests/app/fixtures/apps/geraetecheck_plugin.py`, view and
  demo hook) is registered as `sys.modules["kurort_app.apps.plugins.geraetecheck"]`
  in `tests/app/conftest.py` before any app is built, so the fixture
  definition is valid in every test.
- `tests/app/test_apps_schema.py`: AC-2, AC-3, AC-18.
- `tests/app/test_apps_records.py`: AC-6 to AC-11, AC-19, over HTTP with
  `client`.
- `tests/app/test_apps_status.py`: AC-12, AC-13, pure functions with
  explicit dates.
- `tests/app/test_apps_catalog.py`: AC-4, AC-5, AC-16, using the `idp` and
  `oidc_client` fixtures and `login()` from `tests/app/auth_helpers.py` for
  roles.
- `tests/app/test_apps_reports.py`: AC-14. `tests/app/test_apps_plugins.py`:
  AC-15, AC-17. AC-1's upgrade and downgrade are covered by the existing
  generic round trip in `tests/app/test_migrations.py`; add nothing there.

## Files

New: `src/kurort_app/apps/**`, `src/kurort_app/routers/apps.py`,
`templates/apps/**`, `static/apps.css`, the migration,
`docs/apps/definition-format.md`, the tests and fixtures.
Changed (keep each change small): `main.py` (one `include_router`),
`templates/base.html` (only the `apps.css` link), `config.py`
(`app_definition_dirs`), `cli.py` (`apps` subcommand), `seed.py` (one demo
hook call), `migrations/env.py` (import). Do not import from
`services/checkin_pdf.py`: F1 deletes it in parallel. Write the few PDF
helpers `reports.py` needs there.

## Decided defaults

- Icons: a fixed set of six inline SVGs; unknown icon = validation error.
- Page size 50; start page *Abweichungen* window 7 days; report default
  period: current month.
- The fixture app is called *Gerätecheck* and is never shipped in
  `definitions/`.
- No sidebar counters: due items live on the app's start page only.
- New runtime dependencies: none (pydantic, PyYAML and reportlab are
  already installed).
