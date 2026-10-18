# App definition format (F3)

An app is one UTF-8 YAML file named `<slug>.yaml` in
`src/kurort_app/apps/definitions/`, or in an additional directory configured by
`KURORT_APP_DEFINITION_DIRS` (directories separated by `os.pathsep`). Definitions
are developer-maintained configuration, not executable YAML or browser-authored
content. This is the public reference for definition authors.

## Complete example

This example needs no plugin, installation, database or other file to validate.
Save it as `geraetecheck.yaml`. It is an example only; F3 ships no app definitions.

```yaml
slug: geraetecheck
version: 1
title: Gerätecheck
description: Geräte täglich prüfen und Abweichungen dokumentieren.
icon: thermometer
roles:
  view: [rezeption]
  edit: [rezeption]
collections:
  - key: geraete
    title: Geräte
    item: Gerät
    master: true
    title_field: name
    list_fields: [name, soll_min, soll_max, pruefung_bis]
    order_by: name
    roles: {edit: []}
    fields:
      - {key: name, label: Name, type: text, required: true, max_length: 80}
      - {key: soll_min, label: Soll min, type: decimal, decimals: 1, unit: "°C"}
      - {key: soll_max, label: Soll max, type: decimal, decimals: 1, unit: "°C"}
      - {key: aktiv, label: Aktiv, type: boolean, default: true}
      - {key: intervall, label: Intervall, type: integer, min: 1, default: 1}
      - {key: pruefung_bis, label: Prüfung gültig bis, type: date, default: today+3}
      - {key: ausgemustert, label: Ausgemustert, type: boolean}
  - key: messungen
    title: Messungen
    item: Messung
    title_field: geraet
    date_field: gemessen_am
    list_fields: [gemessen_am, geraet, temperatur, mitarbeiter]
    order_by: -gemessen_am
    fields:
      - {key: geraet, label: Gerät, type: reference, collection: geraete, required: true}
      - {key: gemessen_am, label: Zeitpunkt, type: datetime, required: true, default: now}
      - key: temperatur
        label: Temperatur
        type: decimal
        decimals: 1
        unit: "°C"
        required: true
        min: -40
        max: 100
        range:
          min: {from: geraet.soll_min}
          max: {from: geraet.soll_max}
          severity: warn
        require_when_out_of_range: [massnahme]
      - key: massnahme
        label: Maßnahme
        type: textarea
        help: Bei einer Abweichung die Korrektur eintragen.
        placeholder: Was wurde getan?
        max_length: 1000
      - {key: mitarbeiter, label: Mitarbeiter, type: staff, default: current_user}
      - {key: tag, label: Tag, type: date, default: today}
      - {key: zeit, label: Uhrzeit, type: time}
      - {key: anzahl, label: Anzahl, type: integer, min: 0}
      - {key: kontrolliert, label: Kontrolliert, type: boolean}
      - key: zustand
        label: Zustand
        type: select
        options: [{key: gut, label: Gut}, {key: defekt, label: Defekt}]
      - key: merkmale
        label: Merkmale
        type: multiselect
        options: [{key: innen, label: Innen}, {key: aussen, label: Außen}]
      - {key: zimmer, label: Zimmer, type: room}
schedules:
  - key: taeglich
    title: Gerät prüfen
    target: geraete
    record: messungen
    via: geraet
    at_field: gemessen_am
    every_days: 1
    when: aktiv
alerts:
  - key: abgelaufen
    title: Prüfplakette
    collection: geraete
    field: pruefung_bis
    offset_days: 0
    warn_days: 30
    unless: ausgemustert
reports:
  - key: monat
    title: Geräteprotokoll
    sections:
      - collection: messungen
        columns: [gemessen_am, geraet, temperatur, mitarbeiter, massnahme]
```

## Common conventions and validation

- `slug` matches `^[a-z][a-z0-9_]{1,30}$` (2–31 ASCII characters) and must
  equal the file stem. All other keys, including option keys, match
  `^[a-z][a-z0-9_]*$`.
- Unknown YAML properties are errors. Duplicate YAML mapping keys are errors,
  not last-value-wins. Collection keys are unique within an app; field keys
  within their collection; option keys within their field; schedule, alert,
  report and view keys within their respective lists. The same field key may
  be used in different collections.
- Collection keys cannot be `neu`, `bericht`, `ansicht`, `installieren`,
  `aktivieren`, `deaktivieren`, `deinstallieren` or `export` (reserved routes).
- Names and labels are non-empty strings. Technical keys stay stable; UI copy
  should be short German text. The version is an integer, not a quoted number or
  boolean; numeric bounds must be finite.
- All collection and field references are checked within this app, never
  against another app. Ordinary field references are single keys; only range
  sources use a two-part path. There are no formulas, computed fields,
  multi-level references, file/photo fields or per-record permissions.

## App properties

| Key | Type / default | Meaning |
|---|---|---|
| `slug` | required string | Stable app identity and filename stem. |
| `version` | required integer ≥ 1 | Increase on every definition change. |
| `title` | required non-empty string | Catalogue, sidebar and page title. |
| `description` | string, `""` | Short catalogue description. |
| `icon` | enum, `clipboard` | `clipboard`, `thermometer`, `box`, `broom`, `cart` or `list`. |
| `roles` | required role mapping | Both `view` and `edit` lists must be specified at app level. |
| `collections` | required non-empty list | Collection definitions below; declaration order is preserved. |
| `schedules` | list, `[]` | Due-item rules. |
| `alerts` | list, `[]` | Date warnings. |
| `reports` | list, `[]` | Report definitions. |
| `views` | list, `[]` | Optional code-plugin views. Not needed for a CRUD app. |
| `demo` | optional string | Code-plugin demo-data hook. No hook by default. |

### Role mapping (app, collection or view)

`roles` has two keys: `view` and `edit`, each a list of role names from
`kurort_app.auth.ROLE_LABELS`. Currently these are `rezeption` and `leitung`;
future features may add roles to that authoritative mapping. Unknown roles are errors. `leitung` always has access even when not
listed, and auth-off permits everything.

At app level both lists are required. On a collection or plugin view, omit
`roles`, or omit either key inside it, to inherit that permission from the app.
An explicit empty list means **only Leitung**, not inheritance. For example,
`roles: {edit: []}` restricts edits while preserving the app's view permission.
A null override also inherits. View and edit permissions are independent; the
runtime checks the appropriate permission for the requested operation.

## Collections

| Key | Type / default | Meaning |
|---|---|---|
| `key` | required key | Stable collection identity; not a reserved route word. |
| `title` | required string | Plural heading, e.g. `Messungen`. |
| `item` | required string | Singular name, e.g. `Messung` for “Messung erfassen”. |
| `master` | boolean, `false` | Show under the closed “Stammdaten” disclosure. |
| `title_field` | required field key | Existing field that labels records and reference choices. A reference field displays the target record's title. |
| `list_fields` | list of field keys, `[]` | Existing fields for list columns, in order. UI shows at most four; details show all fields. |
| `order_by` | string, `created_at` | Existing field key or system `created_at`; prefix with `-` for descending. |
| `date_field` | field key, `created_at` | Existing date/datetime field, or system `created_at`, used for period filtering of lists, exports and reports. |
| `roles` | optional role mapping | Per-permission overrides described above. |
| `fields` | required non-empty list | Field definitions, in form/detail order. |

`created_at` is an implicit timestamp accepted by `order_by`, `date_field` and a
schedule's `at_field`; it is not an implicit field for `title_field`,
`list_fields` or report `columns`.

## Fields

| Key | Type / default | Meaning |
|---|---|---|
| `key` | required key | Stable property name in a record's JSON data. |
| `label` | required string | Form label, detail label and report column heading. |
| `type` | required enum | One of the field types below. |
| `required` | boolean, `false` | A value must be present on save. |
| `help` | optional string | Hint under the input. |
| `placeholder` | optional string | Input placeholder; not a replacement for a label. |
| `default` | literal or special string; absent by default | Initial value for a new form, not a constraint on existing records. |
| `max_length` | optional positive integer | Maximum length for `text`, `textarea` or `staff`. |
| `min`, `max` | optional finite numbers | Blocking plausible input limits for `integer`/`decimal`. If both present, `min ≤ max`. |
| `decimals` | optional integer ≥ 0 | Decimal display precision for numeric fields. |
| `unit` | optional string | Numeric unit shown with values, e.g. `°C`. |
| `options` | list of option mappings, `[]` | Required non-empty for `select`/`multiselect`; each option has unique `key` and non-empty `label`. |
| `collection` | optional collection key | Required for a `reference`; its target collection in the same app. |
| `range` | optional range mapping | Expected range for a numeric field; see below. |
| `require_when_out_of_range` | list of field keys, `[]` | Fields in this collection that must be filled when this field deviates. Requires a `range`; all named fields must exist. |

### Types and storage

| `type` | JSON storage / input semantics |
|---|---|
| `text`, `textarea` | String; single-line input / multiline textarea. |
| `integer` | JSON number; numeric input. |
| `decimal` | Exact decimal string, e.g. `"3.5"`; German comma input accepted. |
| `date` | ISO date string, e.g. `"2026-10-14"`. |
| `datetime` | UTC ISO 8601 string, e.g. `"2026-10-14T05:30:00+00:00"`; input/display in Europe/Berlin. |
| `time` | `"07:30"` string. |
| `boolean` | JSON `true`/`false`; checkbox. |
| `select` | One option key; radio buttons when at most three options. |
| `multiselect` | List of option keys; checkboxes. |
| `room` | Existing room number as string. |
| `staff` | Username string. |
| `reference` | Numeric id of a non-deleted record in `collection`, within this app. Label uses the target's `title_field`. |

Empty/missing values are absent from record data, not JSON null. Definition
validation checks the contract; record validation additionally checks actual
rooms, reference records, select membership and input values.

### Defaults

`default` can be a literal (including a boolean or a list of option keys), or:

- `today`: business date from `config.today()`.
- `today+N`: business date plus N days (`today+3`, for example).
- `now`: business date combined with current Europe/Berlin time, stored in UTC.
- `current_user`: logged-in username, or `rezeption` with auth off.

Quote ISO date/time literals in YAML. A `staff` input defaults to the current
username even without an explicit default. Query parameters on a new-record
form override definition defaults. Special defaults are evaluated by the form
runtime, not while the definition is loaded.

### Expected ranges and corrective actions

A `range` is allowed only on `integer` or `decimal`. It has these keys:

| Key | Type / default | Meaning |
|---|---|---|
| `min` | optional number or `{from: reference.field}` | Inclusive expected lower bound. |
| `max` | optional number or `{from: reference.field}` | Inclusive expected upper bound. |
| `severity` | `warn` (default) or `block` | Flag-and-save or refuse an out-of-range value. |

A bound's
`from` must be exactly `<reference field>.<numeric field of its target>`: the
first field belongs to this collection and is a `reference`; the second is an
`integer` or `decimal` field of that reference's target. An empty target value
leaves that side open. More than one hop is forbidden.

`min`/`max` on the **field** always block implausible input. Bounds inside
**range** describe expected values instead: `warn` saves a deviation only when
every `require_when_out_of_range` field is filled; `block` refuses it. Deviation
status is recorded at save time and recalculated on edit, not retroactively
when master-data limits change.

## Schedules

| Key | Type / default | Meaning |
|---|---|---|
| `key` | required key | Unique schedule identity. |
| `title` | required string | Human task title. |
| `target` | required collection key | Each active record here needs a reading. |
| `record` | required collection key | Collection containing those readings. |
| `via` | required field key | A `reference` in `record` pointing to `target`. |
| `at_field` | field key, `created_at` | Date/datetime field of `record`, or implicit `created_at`. |
| `every_days` | optional positive integer | Fixed interval in days. |
| `every_days_field` | optional field key | Integer field of `target` containing each record's day interval. |
| `every_hours` | optional positive finite number | Fixed interval in hours. |
| `when` | optional field key | Boolean field of `target`; skip the target when false. |

Exactly one of `every_days`, `every_days_field`, `every_hours` must be set.
For a per-device interval replace `every_days: 1` in the example with
`every_days_field: intervall`; for hourly checks use e.g. `every_hours: 4`.
The definition can check the interval field's type, not its future record value;
authors should set `min: 1` on that field.

Use the newest non-deleted reading through `via`. No reading is overdue (“noch
nie erfasst”). Day-based tasks are complete before last date + interval, due
on that date, overdue after it. Hourly tasks are overdue strictly after last
timestamp + interval, otherwise complete. Deleted targets and false `when`
values are excluded.

## Date alerts

| Key | Type / default | Meaning |
|---|---|---|
| `key` | required key | Unique alert identity. |
| `title` | required string | Human warning title. |
| `collection` | required collection key | Records being checked. |
| `field` | required field key | Date/datetime field of that collection. |
| `offset_days` | integer, `0` | Deadline = field + offset; negative offsets are allowed. |
| `warn_days` | integer ≥ 0, `0` | Start warning this many days before the deadline. |
| `unless` | optional field key | Boolean field in the same collection; true silences the alert. |

After the deadline an item is “abgelaufen”; from deadline − `warn_days` through
the deadline it “läuft ab”. Deleted records never alert. No notifications,
e-mail or front-desk dashboard counters are generated.

## Reports

| Key | Type / default | Meaning |
|---|---|---|
| `key` | required key | Unique report identity, used in the URL and filename. |
| `title` | required string | Report heading. |
| `sections` | required non-empty list | Ordered tables, each using one collection. |

Each section has exactly `collection` (an existing collection key) and
`columns` (a non-empty ordered list of existing field keys in that collection).
No dotted paths, formulas or implicit timestamps are report columns. Reference
columns use target record titles. Period filtering uses each collection's
`date_field`. Deleted records are excluded.

The runtime emits A4 PDFs (landscape above five columns), with hotel, title,
period, author/time, text-marked deviations and signature lines. CSV uses `;`,
UTF-8 with BOM, German date/decimal formatting, labels for selects/references,
`ja`/`nein` for booleans and a final `Abweichung` column.

## Plugin views and demo hooks

Plugins are trusted Python code shipped under `kurort_app.apps.plugins`; a
namespace restriction is not a sandbox. A handler string is exactly
`module:function`, each part an ASCII Python identifier (letters, underscores,
then optionally digits). Dots, paths, relative imports and fully qualified
module names are not accepted. The resolver imports only
`kurort_app.apps.plugins.<module>` and checks that `<function>` is callable.
It never calls the function while validating a definition. Missing modules,
missing attributes and non-callable attributes are
validation errors.

A view mapping has these keys:

| Key | Type / default | Meaning |
|---|---|---|
| `key` | required key | Unique view identity under `/apps/<slug>/ansicht/<key>`. |
| `title` | required string | Link and page title. |
| `handler` | required string | Plugin resolver reference. |
| `roles` | optional role mapping | Override app view/edit permissions independently. |

For example, once the module is installed:

```yaml
views:
  - key: auswertung
    title: Auswertung
    handler: geraetecheck:auswertung
    roles: {view: [rezeption]}
demo: geraetecheck:seed_demo
```

A view handler receives an `AppContext` and returns a response; it handles GET
and POST. The platform context contract is `request`, `session`, `definition`,
`user`, `can_view(collection)`, `can_edit(collection)`,
`records(collection, where=None)`, `create(collection, data)`,
`update(record, data)`, `value(record, field)` and `render(template, **context)`.
Plugin templates live under `templates/apps/plugins/`. Writes use the same
record validation/audit as forms, raise `RecordValidationError` on invalid
values and flush without committing so the plugin can commit once.

The optional top-level `demo` hook uses the same resolver, but is called as
`fn(session, anchor_date)` after base demo data and app installation. It writes
through the store with explicit actor/time. `seed --reset` clears app records
and installations before running hooks. With no shipped definitions, the demo
remains unchanged.

## Loading API and diagnostics

- `AppDefinition.model_validate(data)` validates a decoded mapping, including
  cross-checks and plugin resolvability. Its `collections`, collection `fields`,
  schedules, alerts, reports and views remain ordered lists, not dictionaries.
- `load_definition(path)` in `kurort_app.apps.registry` reads safe YAML, rejects
  duplicate mapping keys and enforces the slug/file-stem match. It raises
  `DefinitionError` (a `ValueError`) with `.errors: list[str]`, including the
  filename and semantic key path. No database access is needed.
- `AppRegistry(directories=iterable_of_paths)` always includes package
  `definitions/`, then the explicit directories. When `directories` is omitted
  it instead reads `get_settings().app_definition_dirs` as a path-separated
  string. An explicit empty iterable ignores the setting. Its `.directories`
  tuple exposes the de-duplicated scan paths.
- `.valid` maps slug to `AppDefinition`; `.broken` maps file stem to a list of
  diagnostic strings. Broken files do not prevent other files loading. Duplicate
  file stems across paths are errors: none of the conflicting definitions is
  usable, rather than one silently overriding another. Valid and broken keys
  are disjoint.
- Numeric fields expose `.min`, `.max` and `.range`; range bounds are numbers
  or `RangeSource` models. A `RangeSource` exposes `.from_` (YAML alias `from`;
  use `model_dump(by_alias=True)` to serialize that spelling). Roles expose
  `.view` and `.edit`; `None` on an override means inheritance and `[]` means
  Leitung only. `resolve_plugin(reference)` is available from `apps.schema`
  and `apps.plugins` and returns the callable.

Errors name the file and key so catalogue and CLI diagnostics can identify the
broken definition. The catalogue must not install broken definitions. Loading
never imports a module outside the fixed plugin namespace on behalf of a
handler, and never executes hook functions.

## Versions and authoring rules

Increase `version` on every definition change. Never reuse a removed field key
with a different type. The shipped version is the one rendered; a write stores
its version. Removed field values remain in JSON, read-only under “Weitere
Felder (ältere Version)”, and survive edits. Old values that no longer parse
must be corrected on the next edit. Installation version records history but
there is no definition-version data-migration engine.
