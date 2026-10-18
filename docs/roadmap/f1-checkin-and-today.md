# F1: Check-in fit to reality and the "Heute" table

| | |
|---|---|
| Wave | 1 |
| Depends on | – |
| Branch | `feature/f1-checkin-and-today` |
| Migration | `0002_meldeschein_avs` |
| Size | L |

## Why

The manager on 2026-10-15:

- "Der Meldeschein läuft über AVS." It is printed on special paper from Bad Orb
  and cannot be printed by us. His steps: 1. load the Bad Orb paper into the
  printer, 2. log into AVS, 3. enter the data in AVS and print.
- AVS prints the **Kurkarte** on the same sheet; it is torn off.
- Resavio applies the normal Kurtaxe unless someone changes it. He wants a
  "Kurtaxe bearbeiten" button, not a step.
- Dashboard: drop "Hinweise"; arrivals and departures in one table.
- In general: less information, details on demand, usable on a phone.

Today the check-in has five steps. Two of them produce things the hotel cannot
use (our own Meldeschein PDF, our own Kurkarte with QR code), and one makes
staff confirm a Kurtaxe that is almost always the normal rate. The dashboard
shows four metric cards, an arrivals queue, a "Hinweise" card and a chart; on a
phone the sidebar wraps into rows of links above the content.

## What to build

A three-step check-in: **Gäste & Daten → AVS → Abschluss**. The AVS step is a
crib sheet: the three steps the hotel follows, then each guest's data in
Meldeschein order with a copy button per value, and an "In AVS gedruckt" tick
per guest. The Kurtaxe is computed automatically and appears on the Abschluss
step as one line with a "Kurtaxe bearbeiten" disclosure for exemptions. At
Abschluss staff confirm the returned signatures and hand over the room.

The start page becomes one **"Heute" table** of today's arrivals and departures,
each row with its problems shown inline as flags that link to the fix, and one
next action. Problems come from a small registry (`services/today.py`) that
later features (F2, F4, F5) extend without touching this feature's code.

## Scope

1. Check-in steps `gaeste`, `avs`, `abschluss`; old step URLs redirect.
2. The AVS step with copy buttons, print ticks and an optional "AVS öffnen"
   link.
3. Automatic Kurtaxe; exemptions edited in a disclosure on Abschluss.
4. Remove our own Meldeschein PDF and Kurkarte from routes, screens, services,
   database and seed.
5. `services/today.py` exactly as the roadmap README specifies, plus the
   optional action fields on `engine.Blocker` described below.
6. The "Heute" table on `/`; fewer metrics; no "Hinweise" card.
7. Anreisen, Abreisen and Im Haus use the same flag providers.
8. Recording a missing signature later (reservation detail, flag link).
9. A phone menu for the sidebar (the sidebar itself is already data in
   `web.py`).
10. Layouts that work at 390 px for: Übersicht, Anreisen, Abreisen, Im Haus,
    reservation detail, all check-in steps, check-out.
11. Assistant: dashboard widgets renamed, tests updated.
12. Seed and tests updated.

## Not in scope

- Any AVS interface, export file or import. Staff type the data into AVS.
- Changes to Kurtaxe rules or to `src/kurort_engine/`.
- Room cleaning status (F2), payments (F4), late arrivals (F5): only the
  extension points they need.
- Yesterday's no-shows on the dashboard (the old "Hinweise" card showed them);
  they stay findable under Reservierungen with the status filter.
- Restyling reservation list, new and edit beyond not breaking at 390 px.

## Data model

Migration `0002_meldeschein_avs.py`, revision `0002_meldeschein_avs`,
`down_revision = "0001"`. On `reservation_guests`:

| Change | Detail |
|---|---|
| Data | `UPDATE … SET meldeschein_status = 'gedruckt' WHERE meldeschein_status = 'erzeugt'` |
| Constraint | drop check `meldeschein_status`, recreate as `meldeschein_status IN ('offen', 'gedruckt', 'unterschrieben')` (same name) |
| Rename | `meldeschein_generated_at` → `meldeschein_printed_at` |
| Drop | `meldeschein_pdf`, `meldeschein_form_id`, `kurkarte_code`, `kurkarte_qr_payload`, `kurkarte_issued_at` |

`downgrade()` re-adds the dropped columns (nullable, same types as in
`0001`), renames back, maps `gedruckt` → `erzeugt` and restores the old
constraint.

`models.py`: `MELDESCHEIN_PRINTED = "gedruckt"` replaces `MELDESCHEIN_GENERATED`;
`MELDESCHEIN_STATUSES = (MELDESCHEIN_OPEN, MELDESCHEIN_PRINTED, MELDESCHEIN_SIGNED)`;
the `ReservationGuest` columns follow the migration. `web.py` labels:
`offen` "Meldeschein offen", `gedruckt` "In AVS gedruckt · Unterschrift fehlt",
`unterschrieben` "Meldeschein unterschrieben". `config.py`: optional
`avs_url: str | None` (`KURORT_AVS_URL`, default unset).

## The extension points (`services/today.py`)

Implement the names, types and semantics in the README's "Heute rows and
extension points" section. In addition:

- `def arrival_rows(session, day) -> list[TodayRow]`,
  `def departure_rows(session, day) -> list[TodayRow]` and
  `def today_rows(session, day) -> list[TodayRow]` (departures, then arrivals),
  with relations loaded and `flags` filled by running every provider.
  Arrivals: `arrival == day`, status not `cancelled`. Departures:
  `departure == day`, status `checked_in` or `checked_out`.
- `def checkin_blockers(session, reservation) -> list[engine.Blocker]` and
  `def checkout_warnings(session, reservation) -> list[Flag]` run the
  registries.
- `engine.Blocker` gains two optional fields, `action_label: str | None = None`
  and `action_url: str | None = None`. When both are set, the Abschluss page
  renders the blocker with a POST button to `action_url` carrying a hidden
  `zurueck` field with the current path. F2 uses this for "Als sauber
  markieren".
- F1's own providers live in `today.py` and replace `arrival_flags`,
  `meldeschein_flag` and `_missing_fields` from `routers/front_desk.py`:
  - arrival status: "Angekommen" (success), "No-Show" (warning);
  - guest data incomplete: "Gästedaten fehlen · Geburtsdatum" (warning,
    href `/check-in/{id}/gaeste`);
  - exemption without proof: "Kurtaxe klären · Nachweis fehlt" (danger,
    href `/check-in/{id}/abschluss#kurtaxe`);
  - no room: "Kein Zimmer" (danger, href `/reservierungen/{id}/bearbeiten`);
  - room still occupied: "Zimmer noch belegt" (info) when another stay in the
    same room departs today and is still `checked_in`;
  - "Anreisebereit" (success) for a `reserved` arrival with no other flag;
  - departures: "Unterschrift fehlt" (warning, href
    `/reservierungen/{id}#gaeste`) while any guest is not `unterschrieben`,
    "Kurtaxe fehlt" (warning) without an assessment, "Ausgecheckt" (success).
- `def dashboard_notices(session, day) -> list[Flag]` runs `DASHBOARD_NOTICES`;
  the Übersicht renders each notice as one line (a link when `href` is set)
  between the metrics and the "Heute" card. F1 registers none; F4 ("3 offene
  Beträge") and F5 ("Spätanreise: Meldeschein ausstehend") do.
- F1 registers no `CHECKIN_BLOCKERS`; the Abschluss page runs
  `engine.readiness` plus the registry. F1 registers two
  `CHECKOUT_WARNINGS`: unsigned Meldeschein ("Meldeschein von {Name} nicht
  unterschrieben") and missing Kurtaxe ("Kurtaxe noch nicht berechnet").
- `collect_hints` and `Hint` are deleted.

## Screens and routes

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/` | rezeption, leitung | Übersicht with the "Heute" table (`?zeigen=anreisen\|abreisen`) |
| GET | `/check-in/{id}` | same | redirect to the first open step |
| GET, POST | `/check-in/{id}/gaeste` | same | step 1, unchanged form; a successful save assesses the Kurtaxe and goes to `avs` |
| POST | `/check-in/{id}/gaeste/hinzufuegen`, `…/gaeste/{rg_id}/entfernen` | same | unchanged |
| GET | `/check-in/{id}/avs` | same | step 2 |
| POST | `/check-in/{id}/avs/{rg_id}/gedruckt` | same | tick printed; htmx → guest card fragment, else 303 back |
| POST | `/check-in/{id}/avs/{rg_id}/offen` | same | undo a mistaken tick |
| POST | `/check-in/{id}/avs/alle` | same | tick every guest whose data is complete |
| GET | `/check-in/{id}/abschluss` | same | step 3 |
| POST | `/check-in/{id}/kurtaxe` | same | save exemptions from the disclosure, reassess, 303 to `…/abschluss#kurtaxe` |
| POST | `/check-in/{id}/kurtaxe/vorschau` | same | htmx preview, unchanged |
| POST | `/check-in/{id}/abschluss` | same | complete; form field `unterschrieben` lists the guest ids whose signed sheet is back |
| POST | `/meldeschein/{rg_id}/unterschrieben` | same | record a signature later; optional `zurueck`, else 303 to the reservation detail |
| GET | `/check-in/{id}/meldeschein`, `…/kurtaxe`, `…/kurkarte` | same | 303 to `…/avs`, `…/abschluss#kurtaxe`, `…/abschluss` |

Removed: `GET /meldeschein/{rg_id}.pdf`, `POST …/meldeschein/{rg_id}/erzeugen`,
`…/meldeschein/alle`, `…/meldeschein/{rg_id}/unterschreiben`,
`POST …/kurkarte`. They answer 404 or 405 like any unknown route.

**Übersicht.** Header: the date and one sentence ("2 Abreisen offen · 5
Anreisen offen"). Three compact metrics: Abreisen (offen/gesamt), Anreisen
(offen/gesamt), Belegung heute Nacht (% and free rooms). Then the "Heute" card
(`data-widget="today"`): chips Alle · Abreisen · Anreisen with counts, a table
with Zeit · Gast · Zimmer · Art · Hinweise · Aktion. Open rows only; finished
rows (angekommen, ausgecheckt, No-Show) sit in a closed `<details>` "Erledigt
heute (n)" below. Zeit is the ETA for arrivals and empty for departures. Each
row has one button: "Check-in" (primary on the next arrival), "Check-out", or
"Ansehen" for finished rows. A flag with `href` renders as a link. The
occupancy chart stays below (`data-widget="occupancy"`). At 390 px each row is
a card: Art badge and time, guest name, room and flags, full-width button of
at least 44 px.

**Anreisen, Abreisen, Im Haus.** Same pages and filters as today, flags from
the providers. Im Haus shows the Meldeschein badge and, for `gedruckt` guests,
an "Unterschrift erfassen" button. Cards at 390 px.

**Check-in layout.** Stepper with three steps. Below 960 px the aside becomes
a closed `<details>` "Reservierung" under the header.

**Step 2, AVS.** A card "So geht's" with the three numbered steps from the
manager ("Bad-Orb-Papier ins Druckfach legen", "In AVS anmelden", "Daten je
Gast eingeben und drucken") and, when `KURORT_AVS_URL` is set, an "AVS öffnen"
button (new tab). Then one card per guest:

- values in this order, each with a copy button (`data-copy` holding the
  value, `aria-label` "{Feld} kopieren"): Familienname, Vorname,
  Geburtsdatum (TT.MM.JJJJ), Staatsangehörigkeit (country name), Straße und
  Hausnummer, PLZ, Ort, Land, Ausweisnummer (only when present or required),
  Anreise, Abreise, Kurtaxe-Gruppe (the band label or the exemption);
- "Alle Angaben kopieren" copies `Feld: Wert` lines;
- "In AVS gedruckt" button; once ticked a badge "Gedruckt {Uhrzeit} ·
  {Benutzer}" and a small "Rückgängig" button;
- incomplete data: "Daten unvollständig" and a link to step 1 instead of
  values and button.

"Alle als gedruckt markieren" sits above the cards for parties of two or more.
Copying is plain JavaScript in a new `static/checkin.js`
(`navigator.clipboard.writeText`, falling back to selecting the text) with a
"Kopiert" confirmation for two seconds.

**Step 3, Abschluss.** Checklist: Gästedaten, AVS gedruckt (n von m), Zimmer,
Kurtaxe. The Kurtaxe line reads e.g. "Kurtaxe 31,20 € · normaler Satz" or "…
· 1 Person befreit (Geschäftsreise)", followed by `<details id="kurtaxe">`
"Kurtaxe bearbeiten" with the existing exemption form and preview table
(`checkin/_kurtaxe_table.html`); the disclosure is open when the Kurtaxe has a
blocker. Then the bill (Logis, Kurtaxe, total), then one checkbox per guest
"Unterschrift erhalten", ticked by default. Blockers from `readiness` and
`CHECKIN_BLOCKERS` are listed with their action buttons; "Check-in
abschließen · Zimmer {n}" is disabled while any exists.

**Reservation detail.** Per guest the Meldeschein badge and, for `gedruckt`,
an "Unterschrift erfassen" button. No PDF button, no Kurkarte row. The guest
section has `id="gaeste"`.

**Check-out.** `CHECKOUT_WARNINGS` render as warning notices above the bill.
No Kurkarte codes.

**Sidebar.** Already data on `main`: `NAV`, `NAV_GROUPS`, `NAV_PROVIDERS` and
`nav_groups(request)` in `web.py`, rendered by `templates/base.html` and tested
in `tests/app/test_extension_points.py`. F1 changes only its phone layout: at
≤ 860 px the rail shows the brand and a `<details class="rail-menu">` "Menü"
holding the links and the "Neue Reservierung" button; no JavaScript.

## Rules

- `engine.STEPS = (("gaeste", "Gäste & Daten"), ("avs", "AVS"), ("abschluss",
  "Abschluss"))`. `readiness`: `gaeste` = data errors (unchanged); `avs` = each
  guest still `offen` ("{Name}: in AVS noch nicht gedruckt."); `abschluss` =
  no room and the Kurtaxe preview's blockers. `readiness` stays free of
  database writes; a missing assessment is not a blocker, because opening
  Abschluss and completing both assess first.
- The Kurtaxe is assessed (`engine.assess_kurtaxe`) after a successful guest
  save, after saving exemptions, on opening Abschluss when none exists and the
  preview has no blockers, and at completion. A blocked assessment is not an
  error; it shows as a blocker. Existing invalidation stays: changing birth
  date, GdB or the party drops the assessment.
- Changing a Meldeschein-relevant field (`MELDESCHEIN_RELEVANT`) of a guest who
  is `gedruckt` or `unterschrieben` sets them back to `offen`, clears both
  timestamps, and the notice says "Daten geändert – in AVS neu drucken:
  {Namen}."
- Completion needs every guest at least `gedruckt`. Ticked guests become
  `unterschrieben` with `meldeschein_signed_at`; unticked ones stay
  `gedruckt` and show "Unterschrift fehlt" afterwards. On success: status
  `checked_in`, 303 to `/` with "{Name} ist eingecheckt · Zimmer {n}".
- `POST /meldeschein/{rg_id}/unterschrieben` works for `gedruckt` guests in any
  reservation state; for `offen` it answers with the notice "Erst in AVS
  drucken." (danger). `zurueck` is honoured only via `auth.safe_next`.
- Delete `services/checkin_pdf.py`, `services/checkin_qr.py`, the engine
  adapter's PDF, signing and Kurkarte functions and imports, and the templates
  `checkin/meldeschein.html`, `_meldeschein_panel.html`, `kurtaxe.html`,
  `kurkarte.html`, `_kurkarte_card.html`. Keep `engine.meldeschein_form()`:
  its validation still decides completeness. Reason: AVS is the hotel's only
  source for both papers, and a second, official-looking printout invites
  mistakes. The code stays in Git history (commit `74b7486`) for a Kurort that
  prints its own forms.
- Audit actions: `meldeschein.printed`, `meldeschein.print_undone`,
  `meldeschein.signed` (entity `reservation_guest`), `kurtaxe.assessed` with
  `payload.auto = true` when computed automatically, `reservation.checked_in`
  (unchanged). `meldeschein.generated` and `kurkarte.issued` are no longer
  written.
- Assistant: `schema.WIDGETS = ("metrics", "today", "occupancy")`; planner
  words for `today`: `heute|tabelle|anreisen?|abreisen?|ankuenfte`, label
  "Heute"; the `hints` widget is gone. `assistant.js` drops widget ids it
  does not find on the page from a stored configuration, and shows every
  widget if none is left.

## Acceptance criteria

1. **AC-1** The stepper shows exactly "Gäste & Daten", "AVS", "Abschluss".
   `GET /check-in/{id}` for a reservation with complete data redirects to
   `…/avs`.
2. **AC-2** The AVS page lists each guest's values in the order above, each
   with a `data-copy` button; a guest with missing data shows "Daten
   unvollständig" and no "In AVS gedruckt" button.
3. **AC-3** Ticking sets `gedruckt` and `meldeschein_printed_at` and records
   `meldeschein.printed`; with `HX-Request` the response is the guest card
   fragment only. "Rückgängig" returns the guest to `offen`.
4. **AC-4** Editing a printed guest's birth date in step 1 sets `offen` and
   the notice names the guest.
5. **AC-5** After saving complete guest data, `reservation.kurtaxe` exists
   with the normal amount, no Kurtaxe step exists, and Abschluss shows the
   amount and a "Kurtaxe bearbeiten" disclosure.
6. **AC-6** An exemption without proof shows a blocker with the disclosure
   open and completion is refused; posting the proof via `…/kurtaxe`
   reassesses (that guest pays 0) and completion succeeds.
7. **AC-7** Completion is refused while a guest is `offen`; with all
   `gedruckt` it succeeds, ticked guests are `unterschrieben`, unticked stay
   `gedruckt`, status is `checked_in`, the redirect goes to `/`.
8. **AC-8** An unsigned in-house guest shows "Unterschrift fehlt" on Im Haus
   and on today's departure row; `POST /meldeschein/{rg_id}/unterschrieben`
   records it (audit `meldeschein.signed`); for an `offen` guest it refuses
   with "Erst in AVS drucken."
9. **AC-9** `…/meldeschein`, `…/kurtaxe` and `…/kurkarte` answer 303 to the
   new steps; `/meldeschein/{rg_id}.pdf` answers 404; the rendered detail,
   check-in and check-out pages contain neither `.pdf` nor "Kurkarte".
10. **AC-10** The migration maps `erzeugt` to `gedruckt`; afterwards the
    database rejects `erzeugt`; downgrade to `0001` maps it back. (The generic
    round trip in `tests/app/test_migrations.py` must keep passing.)
11. **AC-11** `/` has no "Hinweise" heading, one "Heute" table with today's
    open departures and arrivals, one action per row, finished rows inside
    "Erledigt heute"; `?zeigen=anreisen` and `?zeigen=abreisen` filter; chip
    counts match the database.
12. **AC-12** With seed data, the planted missing birth date and missing
    exemption proof appear as flags in the "Heute" table, linking to
    `…/gaeste` and `…/abschluss#kurtaxe`.
13. **AC-13** A provider appended to `FLAG_PROVIDERS` in a test appears on
    `/`; a `DASHBOARD_NOTICES` entry renders as a line above the "Heute" table;
    a `CHECKIN_BLOCKERS` entry blocks completion and its `action_label`
    renders as a POST button to `action_url`; a `CHECKOUT_WARNINGS` entry
    renders on the check-out page and does not block check-out.
14. **AC-14** Pages contain the `rail-menu` disclosure with every sidebar
    link and "Neue Reservierung"; the sidebar tests in
    `tests/app/test_extension_points.py` still pass.
15. **AC-15** Assistant: "Blende die Kennzahlen aus" yields widgets
    `["today", "occupancy"]`; no plan mentions `hints`; all assistant tests
    pass.
16. **AC-16** `kurort-app seed --reset` leaves one in-house guest `gedruckt`
    and no `erzeugt` rows; every screen listed in scope item 10 shows no
    horizontal scrolling at 390 px (screenshots).

## Tests

- `tests/app/test_checkin.py`: rewrite `test_happy_path_checks_the_guest_in`
  for the three steps (AC-1, 3, 5, 7); replace
  `test_changing_data_after_generation_resets_the_meldeschein` (AC-4),
  `test_htmx_generation_returns_only_the_panel` (AC-3),
  `test_pdf_endpoint` (AC-9), `test_kurtaxe_exemption_needs_evidence` (AC-6),
  `test_kurkarte_waits_for_the_kurtaxe` (removed behaviour, replaced by the
  automatic-Kurtaxe test, AC-5), `test_completion_is_refused_while_items_are_open`
  (AC-7); add AVS page and signature-later tests (AC-2, 8). Keep the co-traveller
  and state tests.
- `tests/app/test_engine_adapter.py`: delete
  `test_meldeschein_renders_a_real_pdf`, `test_sign_requires_a_generated_form`,
  `test_pdf_is_rerendered_when_only_the_form_id_survived`,
  `test_kurkarte_carries_the_engine_qr_payload`, `test_qr_svg_is_a_full_symbol`
  (their code is deleted); rewrite `test_readiness_walks_through_the_steps`
  for three steps. Kurtaxe tests stay unchanged.
- `tests/app/test_front_desk.py`: replace
  `test_dashboard_hints_list_planted_exceptions` and
  `test_dashboard_queue_links_open_arrivals_to_check_in` with "Heute" table
  tests (AC-11, 12); adapt `test_dashboard_metrics_match_database` to three
  metrics; check-out warnings (AC-13).
- `tests/app/test_reservations.py`: `test_detail_for_in_house_offers_check_out_and_pdf`
  becomes `…_and_signature`; `test_detail_history_includes_check_in_trail`
  uses `…/avs/alle`.
- `tests/app/test_today.py` (new): the registries (AC-13) and the phone menu
  (AC-14).
- `tests/app/test_migrations.py` (exists; it already round-trips the whole
  chain): add one data test that upgrades a scratch database to `0001`,
  inserts an `erzeugt` row, upgrades to head, checks `gedruckt` and the
  constraint, downgrades to `0001` and checks `erzeugt` again (AC-10). Reuse
  its `scratch_url` fixture.
- `tests/app/test_assistant.py`: widget cases (AC-15).

List every deleted or rewritten test in the pull request.

## Files

New: `services/today.py`, `static/checkin.js`, `migrations/versions/0002_meldeschein_avs.py`,
`tests/app/test_today.py`. Changed: `tests/app/test_migrations.py`,
`services/engine.py`, `routers/checkin.py`, `routers/front_desk.py`,
`models.py`, `web.py`, `config.py`, `seed.py`, `templates/base.html`,
`templates/_macros.html`, `templates/checkin/*`, `templates/front_desk/*`,
`templates/reservations/detail.html`, `static/app.css`, `static/checkin.css`,
`static/front_desk.css`, `services/assistant/planner.py`,
`services/assistant/schema.py`, `static/assistant.js`. Deleted: see Rules.

`today.py` is what F2, F4 and F5 build on: give it a docstring that says how
to register a provider.

## Decided defaults

- **AVS field order** follows the Meldeschein (§ 30 BMG) order. Reorder when
  the hotel shows the AVS input mask; it is one list in the template.
- **"Unterschrift erhalten" is ticked by default** at Abschluss, because the
  guest normally signs at the counter; the audit records who confirmed it.
- **No AVS link** unless `KURORT_AVS_URL` is set.
- **Departures before arrivals** in the "Heute" table: the morning check-outs
  come first in the desk's day.
- **Our own PDF and Kurkarte are deleted, not hidden.**
- **No Kurtaxe confirmation step**: the normal rate is applied and audited as
  automatic; exemptions are the exception and live behind "Kurtaxe
  bearbeiten".
