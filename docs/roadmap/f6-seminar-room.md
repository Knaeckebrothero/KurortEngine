# F6: Seminar room booking

| | |
|---|---|
| Wave | 1 (parallel with F1 and F3, from today's `main`) |
| Depends on | – |
| Branch | `feature/f6-seminar-room` |
| Migration | `0004_seminar_room` (`down_revision = "0001"`, the id of `0001_initial_schema.py`) |
| Size | M |

## Why

The manager: Resavio cannot book the seminar room without also booking a
guest room. Firms, the adult education centre or a physio course rent the room
for a morning or a day, and nobody sleeps in the hotel. Today the desk fakes a
room reservation or keeps the seminar room on paper.

## What to build

A small booking book for the hotel's function rooms, separate from guest
reservations. Staff see the coming bookings and a week strip of free and taken
half-days, book a morning, an afternoon or whole days for an organiser, note
attendees and catering, confirm or cancel. A booking can point to a guest
reservation when the organiser also stays, but never needs one. Leitung keeps
the list of rooms and their prices. The Zimmerplan shows the bookings
read-only below the guest rooms.

## Scope

- Tables `function_spaces` and `space_bookings`, migration `0004`, seed data.
- `/seminarraum`: list of coming bookings plus a week strip.
- New, detail, edit, confirm and cancel for a booking.
- `/verwaltung/seminarraum` (leitung): rooms, capacity, prices, active flag.
- A read-only "Seminarräume" section at the bottom of `/zimmerplan`.
- Sidebar entries "Seminarraum" (Planung) and "Seminarraum-Preise" (Verwaltung).

## Not in scope

- Invoices, payments, deposits. The price is informational until invoicing
  exists (F4 tracks payments for guest stays only).
- Meldeschein or Kurtaxe for seminar attendees (day guests pay neither).
- Showing the booking on the reservation detail page, e-mails to organisers
  (F5 may add a template later), the assistant, recurring bookings, times of day
  beyond the two halves, equipment lists.

## Data model

New models in `models.py`, constants next to the existing vocabularies:

```python
SPACE_SLOTS = ("vormittag", "nachmittag", "ganztags")
SPACE_BOOKING_STATUSES = ("angefragt", "bestaetigt", "storniert")
```

`function_spaces`

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `name` | `String(80)`, unique | "Seminarraum" |
| `capacity` | int, check `> 0` | persons |
| `price_half_day` | `Numeric(10, 2)` | per half-day |
| `price_full_day` | `Numeric(10, 2)` | per day |
| `active` | bool, default true | inactive rooms take no new bookings |
| `position` | int, default 0 | display order |

`space_bookings`

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `space_id` | FK `function_spaces.id`, not null, indexed | |
| `start_date`, `end_date` | `Date`, not null | inclusive; check `end_date >= start_date`; index `(space_id, start_date)` |
| `slot` | `String(12)`, check in `SPACE_SLOTS` | applies to every day of the booking |
| `status` | `String(12)`, check in statuses, default `angefragt` | |
| `organizer_name` | `String(160)`, not null | contact person |
| `company` | `String(160)`, null | |
| `email` | `String(160)`, null | |
| `phone` | `String(40)`, null | at least one of email/phone (form rule) |
| `attendees` | int, check `> 0` | |
| `catering_coffee`, `catering_lunch`, `catering_drinks` | bool, default false | Kaffeepause, Mittagessen, Getränke |
| `catering_note` | `Text`, null | "vegetarisch für 3" |
| `notes` | `Text`, null | |
| `price` | `Numeric(10, 2)`, not null | |
| `price_manual` | bool, default false | true when staff typed the price |
| `reservation_id` | FK `reservations.id`, `ondelete="SET NULL"`, null | organiser also stays |
| `created_at` | timestamptz, server default now | |
| `cancelled_at` | timestamptz, null | |
| `cancel_reason` | `Text`, null | |

Labels in `web.py`: slots "Vormittag", "Nachmittag", "Ganztags"; statuses
"Angefragt", "Bestätigt", "Storniert", plus `slot_label`/`space_status_label`
filters.

**Default room.** The room "Seminarraum" (capacity 20, 190,00 € half-day,
340,00 € day) is a default row: an idempotent `ensure_function_spaces(session)`
in `services/seminar.py`, listed in `DEFAULTS` in `src/kurort_app/defaults.py`
(it creates the room only when no function space exists). Migrations create
no rows.

`seed.py` (whose reset already empties every table and re-runs `DEFAULTS`)
adds these fixed bookings relative to the business date `d` (no random
numbers):

1. `d+1` ganztags, bestätigt, "Spessart Physio GmbH", 14 persons, Kaffeepause + Mittagessen.
2. `d+3` nachmittag, bestätigt, organiser linked to the first non-cancelled
   reservation (by id) that is in the house on `d+3`.
3. `d+2` vormittag, storniert, reason "Kurs abgesagt".
4. `d+6` to `d+7` vormittag, angefragt, "Volkshochschule Bad Orb", 12 persons, Getränke.
5. `d-5` ganztags, bestätigt (history).

## Screens and routes

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/seminarraum` | rezeption, leitung | Week strip + coming bookings; `?von=YYYY-MM-DD` picks the week, `?vergangene=1` adds past ones |
| GET | `/seminarraum/neu` | rezeption, leitung | Form; prefill from `?raum=<id>&von=<date>&zeit=<slot>` |
| POST | `/seminarraum/neu` | rezeption, leitung | Create, 303 to detail; 422 with the form on errors |
| GET | `/seminarraum/{id}` | rezeption, leitung | Detail |
| GET, POST | `/seminarraum/{id}/bearbeiten` | rezeption, leitung | Edit (not for `storniert`) |
| POST | `/seminarraum/{id}/bestaetigen` | rezeption, leitung | `angefragt` → `bestaetigt` |
| POST | `/seminarraum/{id}/stornieren` | rezeption, leitung | → `storniert`, optional `grund` |
| GET | `/verwaltung/seminarraum` | leitung | Rooms with capacity, prices, active |
| POST | `/verwaltung/seminarraum/{space_id}` | leitung | Save one room |
| POST | `/verwaltung/seminarraum/neu` | leitung | Add a room |

Rezeption and leitung are today's only roles, so the booking routes need no
extra check; the Verwaltung routes use `Depends(require_role("leitung"))`.

**`/seminarraum`.** Header "Seminarraum" with the button "Neue Buchung".
First the **week strip**: Monday to Sunday of the chosen week, buttons "Woche
zurück", "Diese Woche", "Woche vor". Per active room one row, per day two cells
"Vormittag" and "Nachmittag", each either "frei" (a link to `/seminarraum/neu`
prefilled with room, date and slot; no link for past days) or the organiser's
company or name with the status as text. Then the **list**: coming bookings
(`end_date >= today`, not cancelled) by start date, under week headings like
"KW 43 · 19.–25. Oktober". Each entry shows only dates and slot, company or
organiser, persons, catering as text ("Kaffeepause · Mittagessen"), status and
price; the room name only when more than one room is active. Contact data and
notes stay on the detail page. Cancelled coming bookings sit in a closed
`<details>` "Storniert (n)" below. At 390 px the strip turns into a list of
days, each with its two half-days, and list entries are cards.

**Form** (new and edit, same template): Raum (select, hidden when only one
room is active), Von, Bis (defaults to Von), Zeit (radio Vormittag /
Nachmittag / Ganztags), Veranstalter, Firma, E-Mail, Telefon, Personen,
Verpflegung (three checkboxes and a note), Notizen, Preis (empty means
calculated; the hint shows the calculation, e.g. "2 × Ganztag à 340,00 €"),
Reservierung (optional code like `R-2610-0042`), and on the new form only
Status (Angefragt, default, or Bestätigt). Errors follow the reservation
form: a summary at the top and the message under each field.

**Detail**: everything in the booking, the price with "berechnet" or
"manuell", a link to the linked reservation, the booking's audit events, and
the buttons "Bearbeiten", "Bestätigen" (only `angefragt`) and "Stornieren"
(with an optional reason, like reservation cancel).

**`/verwaltung/seminarraum`**: one card per room with name, capacity, both
prices, "aktiv" checkbox and "Speichern"; below a form "Raum hinzufügen".
Rooms are never deleted.

**Zimmerplan.** Below the last floor, a section "Seminarräume" with one row
per active room. Each non-cancelled booking in the window is drawn on the
plan's half-day grid: vormittag fills the day's first half, nachmittag the
second, ganztags both; consecutive whole days form one bar. Bars show the
company or organiser and link to the booking. No free-cell links in this
section. Room counts, occupancy percentages and arrival/departure numbers
ignore it.

## Rules

- **Clash.** Two bookings of the same room clash when their date ranges share
  a day, both are not `storniert`, and their slots overlap: `ganztags`
  overlaps everything, `vormittag` overlaps `vormittag`, `nachmittag` overlaps
  `nachmittag`. `angefragt` holds the slot like `bestaetigt`. A booking never
  clashes with itself on edit, guest room reservations never clash with
  seminar bookings. Message: "Seminarraum ist am 21.10.2026 vormittags bereits
  gebucht (Spessart Physio GmbH, angefragt)." naming the first clash.
- **Price.** Calculated as days × `price_full_day` for `ganztags`, days ×
  `price_half_day` otherwise, from the room's prices at save time. A typed
  price is kept and sets `price_manual`; an empty price field clears it. On
  edit, a booking with `price_manual = false` is recalculated. Changing a
  room's prices never changes saved bookings.
- **Validation** (422, nothing saved): Veranstalter fehlt; "Bitte E-Mail oder
  Telefon angeben."; Bis vor Von; longer than 14 days; start in the past
  (unless unchanged on edit); Personen missing or below 1; more persons than
  the room's capacity ("Der Seminarraum ist für höchstens 20 Personen
  ausgelegt."); inactive room; unknown or cancelled reservation code; negative
  price.
- **Status.** Cancelled bookings cannot be edited, confirmed or cancelled
  again: redirect to the detail with a warning notice. Cancelling frees the
  slot at once.
- **Audit** with `audit.record`, entity `space_booking` or `function_space`:
  `space_booking.created`, `space_booking.updated`,
  `space_booking.confirmed`, `space_booking.cancelled`,
  `function_space.created`, `function_space.updated`. Summaries in German,
  e.g. "Seminarraum 21.10.2026 ganztags für Spessart Physio GmbH angelegt".

## Acceptance criteria

1. **AC-1** `GET /seminarraum` on seed data returns 200, lists the coming
   bookings under week headings, and shows the cancelled one only inside
   "Storniert (1)".
2. **AC-2** A valid `POST /seminarraum/neu` without a reservation code
   redirects (303) to the detail page and creates one `space_bookings` row with
   status `angefragt`; the number of `reservations` and `guests` rows is
   unchanged; one `space_booking.created` audit event exists.
3. **AC-3** Price: 2 days ganztags gives 2 × `price_full_day`; 1 day
   vormittag gives `price_half_day`; a typed price is stored with
   `price_manual = true`; editing the dates of a calculated booking
   recalculates, of a manual one keeps the price.
4. **AC-4** Clashes: ganztags vs vormittag on a shared day → 422 with the clash
   message; vormittag vs nachmittag on the same day → saved; a `storniert`
   booking never blocks; back-to-back days → saved; another room → saved;
   editing a booking without changing its slot → saved.
5. **AC-5** Each validation rule in "Rules" returns 422 with its German message
   and saves nothing.
6. **AC-6** `bestaetigen` turns `angefragt` into `bestaetigt`; `stornieren`
   sets `storniert`, `cancelled_at` and the reason; the freed slot can be
   booked again; editing a cancelled booking redirects with a warning.
7. **AC-7** A valid reservation code links the booking; the detail page links to
   `/reservierungen/{id}`; a cancelled reservation's code is refused.
8. **AC-8** The week strip for `?von=` a seeded week shows "frei" and taken
   half-days correctly; a free cell links to `/seminarraum/neu?raum=…&von=…&zeit=…`
   and that form opens prefilled.
9. **AC-9** Leitung changes a room's prices on `/verwaltung/seminarraum` and
   adds a room (audit events written); existing booking prices stay; the hint
   "Platzhalterpreise – bitte prüfen" shows on seed data and is gone after the
   first save; with login on, a `rezeption`-only user gets 403 on these routes.
10. **AC-10** `/zimmerplan` shows "Seminarräume" with a bar per non-cancelled
    booking in the window, linking to it; the header's room count and
    occupancy percentage are the same as without seminar bookings.
11. **AC-11** `seed --reset` run twice gives exactly one room and the five
    bookings above, one of them linked to a reservation.
12. **AC-12** The sidebar shows "Seminarraum" under Planung for everyone and
    "Seminarraum-Preise" under Verwaltung only for leitung (and when login is
    off).

## Tests

New file `tests/app/test_seminar.py`; one or more tests per AC. Use `client`
and `seeded` for screens, `db` for clash and price rules (test the rule
function directly as well as through the form). For AC-9 and AC-12 with login
on, use the `idp` and `oidc_client` fixtures and `login()` from
`tests/app/auth_helpers.py` with `idp.claims["roles"]` set per test. The
migration's downgrade and upgrade are covered by the generic round trip in
`tests/app/test_migrations.py`.

## Files

New: `routers/seminar.py`, `services/seminar.py` (clash check, price
calculation, week strip and plan rows), `templates/seminar/*.html`,
`static/seminar.css`, `migrations/versions/0004_seminar_room.py`,
`tests/app/test_seminar.py`.

Shared files, keep the edits small:

- `models.py`: two models and two constants appended.
- `web.py`: label maps and two filters appended.
- `main.py`: one `include_router` line.
- Sidebar: two `NAV.append(NavItem(...))` lines in `routers/seminar.py`:
  "Seminarraum" (`/seminarraum`, group "Planung") and "Seminarraum-Preise"
  (`/verwaltung/seminarraum`, group "Verwaltung", `roles=("leitung",)`).
  `templates/base.html` gets only the stylesheet link.
- `routers/reservations.py` (`room_plan`) and `templates/reservations/plan.html`:
  only the call to `services/seminar.py` for the plan rows and the extra
  section. Leave the rest of the plan alone.
- `seed.py`: one `_seed_seminar(session, anchor, reservations)` call at the
  end of `seed_demo_data`.
- `defaults.py`: one entry.

## Decided defaults

The hotel has not said how many function rooms it has, what they cost, or how
catering works.

- **Rooms:** one, "Seminarraum", capacity 20. The data model is a list, so a
  second room is "Raum hinzufügen" in Verwaltung, no code change.
- **Prices:** 190,00 € half-day, 340,00 € day, net, placeholders; the
  Verwaltung screen shows "Platzhalterpreise – bitte prüfen" until a price is
  saved once (`function_space.updated` event exists).
- **Half-days:** Vormittag and Nachmittag without clock times; exact times go
  into Notizen.
- **Catering:** three ticks and a note, no prices or quantities.
- **Holds:** an inquiry (`angefragt`) blocks the slot until it is cancelled;
  there is no automatic expiry.
