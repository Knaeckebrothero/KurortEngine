# F2: Room cleaning status

| | |
|---|---|
| Wave | 2 (start from `main` after F1 is merged) |
| Depends on | F1 (`services/today.py`, `engine.Blocker` actions) |
| Branch | `feature/f2-housekeeping` |
| Migration | `0005_room_status` |
| Size | M |

## Why

The manager on 2026-10-15, under "missing in the app": whether rooms are
cleaned. Today the desk cannot see whether the room of an arriving guest is
ready, and housekeeping has no list to work from or report back to. The
owner's HACCP prototype kept a housekeeping log; this feature's audit trail
replaces it.

## What to build

Every room has a cleaning status: **schmutzig, sauber, geprüft, außer
Betrieb**. Check-out makes a room dirty. Housekeeping staff work from a
phone-first list, `/zimmerstatus`, that shows each room's situation today
(departure, arrival, stayover, free) and changes its status with one tap. The
desk sees "Zimmer noch nicht sauber" on today's arrivals and can mark a room
clean right from the check-in. Rooms out of order are not offered for new
bookings. A new role `housekeeping` opens only this list.

## Scope

1. Status per room with migration, constants, labels and audit trail.
2. Check-out sets the room to `dirty`.
3. `/zimmerstatus`: list, filters, one-tap change, bulk "Bleibezimmer".
4. A "Heute" flag and a check-in blocker through F1's registries.
5. Status in the Zimmerplan; out-of-order rooms leave availability.
6. Role `housekeeping` and the plumbing for limited staff (README, Roles).
7. Demo realm role and user; seed data.

## Not in scope

- Scheduled tasks, cleaning plans per room, linen or minibar tracking.
- Housekeeping time tracking or assignment of rooms to people.
- Changing the dashboard's capacity numbers for out-of-order rooms.
- Out-of-order periods with an end date (the status lasts until changed).

## Data model

Migration `0005_room_status.py`, revision `0005_room_status`, `down_revision` =
the head on your base `main` (F1's `0002_meldeschein_avs` or later). On
`rooms`:

| Column | Type | Notes |
|---|---|---|
| `housekeeping_status` | `String(16)`, not null, server default `'clean'` | check `room_housekeeping_status IN ('dirty', 'clean', 'inspected', 'out_of_order')` |
| `housekeeping_note` | `String(200)`, null | free text, shown for `out_of_order` ("Heizung defekt") |
| `housekeeping_changed_at` | `DateTime(timezone=True)`, null | |
| `housekeeping_changed_by` | `String(60)`, null | username, as `audit_events.actor` |

Existing rows become `clean`. `downgrade()` drops the four columns and the
constraint. The generic round trip in `tests/app/test_migrations.py` covers
it; add nothing there.

`models.py`: `ROOM_DIRTY = "dirty"`, `ROOM_CLEAN = "clean"`,
`ROOM_INSPECTED = "inspected"`, `ROOM_OUT_OF_ORDER = "out_of_order"`,
`HOUSEKEEPING_STATUSES`, and `ROOM_READY = (ROOM_CLEAN, ROOM_INSPECTED)`.
`web.py`: `HOUSEKEEPING_LABELS = {"dirty": "schmutzig", "clean": "sauber",
"inspected": "geprüft", "out_of_order": "außer Betrieb"}` and a
`room_status_label` filter. Badge kinds: dirty `warning`, clean `success`,
inspected `info`, out_of_order `danger`.

## Screens and routes

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/zimmerstatus` | housekeeping, rezeption, leitung | the list; `?etage=1..3`, `?status=<id>`, `?sort=dringend\|zimmer` |
| POST | `/zimmerstatus/{room_id}/{status}` | same | set a status; form fields `notiz` (optional), `zurueck` (optional); htmx → room card fragment, else 303 back with notice |
| POST | `/zimmerstatus/bleibe` | same | every stayover room that is `clean` or `inspected` becomes `dirty` |

**`/zimmerstatus`.** Sidebar entry "Zimmerstatus" in the "Heute" group: one
`NAV.append(NavItem("/zimmerstatus", "Zimmerstatus", <icon>, "Heute",
roles=("housekeeping", "rezeption", "leitung")))` in `routers/housekeeping.py`. Top: chips
for Etage (Alle, 1, 2, 3, derived from the rooms) and Status (Alle and each
status with its count), a "Bleibezimmer auf schmutzig setzen" button with the
number of affected rooms. Then one card per room:

- room number (large), floor and category;
- the situation today: "Abreise heute", "Abgereist", "Anreise heute · ca.
  14:00", "Abreise · Anreise heute", "Bleibe", "frei";
- the status badge and "Zuletzt {Uhrzeit} · {Benutzer}";
- one primary button for the usual next status: schmutzig → "Sauber",
  sauber → "Geprüft", außer Betrieb → "Wieder in Betrieb" (sets `dirty`);
  geprüft has none;
- `<details>` "Anderer Status" with buttons for the other statuses and, for
  "Außer Betrieb", a note field.

**No guest names** appear on this screen. Default sort `dringend`: arrival
today and not ready, then checked out today and dirty, then other dirty
rooms, then out of order, then the rest; each group by room number. At
390 px the cards are one column, buttons at least 48 px high; at 1280 px a
grid of cards. With htmx the tapped card is replaced in place
(`hx-post`, `hx-target` the card, `hx-swap="outerHTML"`); the list is not
re-filtered until reload. Without JavaScript the form posts and redirects.

**Zimmerplan.** The room label cell shows the status badge for today. For an
out-of-order room, free cells carry no booking link and the label reads
"außer Betrieb" with the note as `title`.

**Check-in, Abschluss.** The blocker below renders with its button through
F1's `action_label`/`action_url`. The check-in aside shows the room's status
badge.

## Rules

- Write all status changes through one function in a new
  `services/housekeeping.py`:
  `set_status(session, room, status, *, reason, note=None)`. It sets the
  columns (actor from `auth.current_actor`, else `audit.DEFAULT_ACTOR`) and
  records `audit.record(action="room.status_changed", entity="room",
  entity_id=room.id, summary="Zimmer 112: schmutzig → sauber", payload={"from",
  "to", "reason", "note"})`. `reason` is `manual`, `checkout`, `stayover` or
  `checkin_blocker`. Setting the current status again is a no-op without an
  audit event. The note is kept only for `out_of_order` and cleared otherwise.
- **Check-out:** the existing check-out handler calls
  `housekeeping.mark_dirty_after_checkout(session, reservation)` (reason
  `checkout`). No other F1 code changes behaviour.
- **Situation** for a room on day `d`: departs = a stay with `departure == d`
  and status `checked_in` ("Abreise heute") or `checked_out` ("Abgereist");
  arrives = a stay with `arrival == d` and status `reserved` ("Anreise
  heute", with ETA); stays = `checked_in` with `arrival < d < departure`
  ("Bleibe"); none → "frei". Departure and arrival together → "Abreise ·
  Anreise heute".
- **Flag provider** (`room_not_ready_flags`, appended to `FLAG_PROVIDERS`):
  for an arrival row with status `reserved` and a room: `dirty` → Flag
  "Zimmer noch nicht sauber" (warning, href `/zimmerstatus?etage={floor}`);
  `out_of_order` → "Zimmer außer Betrieb" (danger, href
  `/reservierungen/{id}/bearbeiten`). Nothing for departure rows.
- **Check-in blocker** (`room_not_ready_blocker`, appended to
  `CHECKIN_BLOCKERS`): `dirty` → `Blocker("abschluss", "Zimmer {n} ist noch
  nicht sauber.", action_label="Als sauber markieren",
  action_url="/zimmerstatus/{room_id}/clean")`; the route records reason
  `checkin_blocker` when `zurueck` points into `/check-in/`. `out_of_order` →
  `Blocker("abschluss", "Zimmer {n} ist außer Betrieb – bitte ein anderes
  Zimmer zuweisen.")` without action. `clean` and `inspected` both count as
  ready.
- Register both providers in `services/housekeeping.py` and import that
  module at the end of `services/today.py` (one line, as the README says).
- **Bulk stayover:** only rooms whose situation is "Bleibe" and status
  `clean` or `inspected`; reason `stayover`; notice "{n} Bleibezimmer auf
  schmutzig gesetzt." (or "Keine Bleibezimmer zu setzen.").
- **Availability:** `availability.free_rooms()` leaves out `out_of_order`
  rooms for every date range, so the room picker, walk-in and the assistant's
  availability answer never offer them. Creating a reservation, or editing one
  to a different room, with an out-of-order room fails with "Zimmer {n} ist
  außer Betrieb." Existing reservations keep their room and show the flag.
- Unknown status in the path → 400 "Unbekannter Zimmerstatus."; unknown room
  → 404.

### Roles and limited staff

- `auth.py`: `ROLE_LABELS` gains `"housekeeping": "Housekeeping"` (after
  `rezeption`); `FRONT_DESK_ROLES = ("rezeption", "leitung")`;
  `ROLE_HOME = {"housekeeping": "/zimmerstatus"}`; `home_path(user)` returns
  `/` with login off or for a user with a front-desk role, else the first
  `ROLE_HOME` path for the user's roles, else `/`. F7 adds `kueche` to both
  maps.
- `main.py`: the `front_desk`, `reservations`, `checkin` and `assistant`
  routers are included with `dependencies=[Depends(require_role(*FRONT_DESK_ROLES))]`.
  `/` must still redirect limited users, so move the `GET /` route into a new
  `routers/home.py`, included without that dependency: a user without a
  front-desk role gets 303 to `home_path(user)`, everyone else the F1
  dashboard.
- A 403 from `require_role` on a page request renders
  `auth/forbidden.html` (status 403) with a link "Zu Ihrem Bereich" to
  `home_path(user)` when that is not `/`; JSON requests keep a JSON 403. Adjust
  the forbidden page text so it fits both "no role at all" and "not your
  area" (e.g. "Diese Seite gehört nicht zu Ihrem Bereich.").
- `base.html`: the assistant bar and the "Neue Reservierung" button show only
  with login off or for front-desk users. The sidebar already filters by
  `NavItem.roles` (`web.nav_groups`).
- Demo realm (`deploy/k3d/keycloak/`): add the realm role `housekeeping`
  (description "Housekeeping") and the user `s.klein` (Sandra Klein, roles
  `[housekeeping]`). Update `tests/test_deployment_artifacts.py::test_demo_keycloak_realm_matches_the_app_contract`
  to the new role set. Keycloak imports the realm only on first start; say in
  the pull request that the demo Keycloak must be recreated.

## Acceptance criteria

1. **AC-1** After migration every room is `clean`; the database rejects
   another value; `tests/app/test_migrations.py` still passes.
2. **AC-2** `GET /zimmerstatus` with seed data shows all 33 rooms with
   number, situation and status label, and contains no guest name of today's
   arrivals or departures.
3. **AC-3** `?etage=2` shows only floor-2 rooms; `?status=dirty` only dirty
   ones; the chip counts match the database.
4. **AC-4** `POST /zimmerstatus/{id}/clean` sets status, `changed_at` and
   `changed_by`, and records `room.status_changed` with `from`, `to` and
   `reason: manual`; with `HX-Request` the response is the card fragment;
   without it a 303 with a notice. Posting the current status again writes no
   audit event.
5. **AC-5** An unknown status answers 400, an unknown room 404.
6. **AC-6** Check-out sets the room to `dirty` with reason `checkout`.
7. **AC-7** A `reserved` arrival whose room is dirty shows "Zimmer noch nicht
   sauber" in the "Heute" table, linking to `/zimmerstatus`; clean or
   inspected rooms show no flag.
8. **AC-8** Abschluss for a dirty room lists the blocker with an "Als sauber
   markieren" button and refuses completion; after posting that button the
   room is clean and completion succeeds.
9. **AC-9** An out-of-order room is missing from
   `/reservierungen/verfuegbare-zimmer`, the walk-in form and
   `free_rooms()`; creating a reservation with it fails with "Zimmer {n} ist
   außer Betrieb."; an existing reservation in it shows the danger flag and
   the blocker.
10. **AC-10** The Zimmerplan shows every room's status label; an out-of-order
    room's free cells have no booking link.
11. **AC-11** The bulk action sets only stayover rooms that were clean or
    inspected to dirty and reports the count.
12. **AC-12** With login on (OIDC test app), a `housekeeping`-only user: `GET
    /` → 303 to `/zimmerstatus`; `GET /zimmerstatus` → 200 with "Zimmerstatus"
    as the only sidebar link, no assistant bar, no "Neue Reservierung";
    `GET /anreisen` and `GET /reservierungen` → 403 page with "Zu Ihrem
    Bereich"; `POST /assistent/plan` (JSON) → JSON 403. A `rezeption` user
    still reaches every front-desk page and sees "Zimmerstatus"; a user
    without any role still gets "Kein Zugriff".
13. **AC-13** The demo realm renders the role `housekeeping` and the user
    `s.klein` with that role.
14. **AC-14** `kurort-app seed --reset` gives at least three dirty rooms (one
    of them the room of a `reserved` arrival today), one out-of-order room
    with a note, and at least one inspected room; the dashboard demo still
    shows F1's planted flags.

## Tests

- `tests/app/test_housekeeping.py` (new): AC-1 to AC-12, AC-14.
- `tests/app/test_housekeeping.py` also holds the limited-staff cases, with
  the `idp` and `oidc_client` fixtures and `login()` from
  `tests/app/auth_helpers.py` (set `idp.claims["roles"]` first) (AC-12), and
  the status defaults and constraint (AC-1).
- `tests/test_deployment_artifacts.py`: the realm assertion (AC-13).
- `tests/app/test_reservations.py`: one out-of-order availability case next
  to `test_room_availability_rules` (AC-9).

## Files

New: `services/housekeeping.py`, `routers/housekeeping.py`, `routers/home.py`,
`templates/housekeeping/list.html`, `templates/housekeeping/_room_card.html`,
`static/housekeeping.css` (linked in `base.html`),
`migrations/versions/0005_room_status.py`, `tests/app/test_housekeeping.py`.
Changed: `models.py`, `web.py` (labels), `services/today.py`
(one import line at the end), `services/availability.py`,
`routers/front_desk.py` (check-out call, `/` route moved out),
`routers/reservations.py` (out-of-order validation, plan context),
`templates/reservations/plan.html`, `templates/base.html`,
`templates/auth/forbidden.html`, `templates/checkin/_layout.html`, `auth.py`,
`main.py`, `seed.py`, `deploy/k3d/keycloak/values.yaml`,
`deploy/k3d/keycloak/templates/realm-configmap.yaml`, the tests above.

## Decided defaults

- **No automatic daily reset for stayover rooms.** The app has no scheduler,
  and the hotel has not said how often stayover rooms are cleaned (daily,
  every second day, on request). The bulk button covers the morning routine
  in one tap; a schedule can follow once the rhythm is known.
- **Out of order lasts until someone changes it**, and leaves availability
  for all dates, because nobody knows when the repair is done. "Wieder in
  Betrieb" sets `dirty`: a repaired room is cleaned before it is let.
- **Reception may set any status**, including "sauber" from the check-in. In
  a 33-room hotel the desk often checks the room itself.
- **"geprüft" is optional**: it counts as ready like "sauber" and records that
  someone inspected the room.
- **No guest names for housekeeping** (data minimisation); they need the
  situation and the time, not the person.
- **Check-in does not change the status**; the next morning's bulk action
  turns occupied rooms into stayover work.
