# Roadmap: Hotel Rheinland feedback, October 2026

On 2026-10-15 the manager of Hotel Rheinland (Bad Orb, 33 rooms) tried the
staff app. This roadmap turns the part of that feedback that needs **no further
input from the hotel** into eight features. Each feature has its own document
in this folder, is built on its own branch and delivered as one pull request.

Read [`AGENTS.md`](../../AGENTS.md) first for setup, commands and conventions.
This page holds what all features share: order, dependencies and the contracts
that keep parallel branches from colliding.

## The manager's feedback in one paragraph

Simpler screens with details on demand, usable on a phone. One table for
today's arrivals and departures; drop the "Hinweise" card. Check-in is
over-built: the Meldeschein and the Kurkarte come out of the separate **AVS**
system on special Bad Orb paper, and the Kurtaxe is the normal rate unless
someone changes it. Missing: whether rooms are clean, who has paid and how,
e-mails from templates, a late-arrival routine (key and Meldeschein in the
safe, PIN by e-mail), booking the seminar room without a guest room. The owner
added an "Apps" area for small hotel apps (HACCP first, then inventory), which
the manager liked.

## Features

| ID | Feature | Wave | Depends on | Migration | Branch |
|---|---|---|---|---|---|
| F1 | [Check-in fit to reality and the "Heute" table](f1-checkin-and-today.md) | 1 | – | `0002` | `feature/f1-checkin-and-today` |
| F2 | [Room cleaning status](f2-housekeeping.md) | 2 | F1 | `0005` | `feature/f2-housekeeping` |
| F3 | [App platform](f3-app-platform.md) | 1 | – | `0003` | `feature/f3-app-platform` |
| F4 | [Payment tracking](f4-payments.md) | 2 | F1 | `0006` | `feature/f4-payments` |
| F5 | [Guest e-mail and late arrival](f5-guest-email-late-arrival.md) | 2 | F1 | `0007` | `feature/f5-guest-email` |
| F6 | [Seminar room booking](f6-seminar-room.md) | 1 | – | `0004` | `feature/f6-seminar-room` |
| F7 | [HACCP app](f7-haccp-app.md) | 3 | F2, F3 | none planned | `feature/f7-haccp-app` |
| F8 | [Inventory and ordering app](f8-inventory-app.md) | 3 | F2, F3 | none planned | `feature/f8-inventory-app` |

**Waves.** Wave 1 starts from today's `main`. A wave-2 feature starts from
`main` after F1 is merged; a wave-3 feature after F2 and F3 are merged. Within
a wave the features run in parallel. F2 sits in wave 2 because it adds to the
"Heute" table and the check-in that F1 rebuilds; F7 and F8 wait for F2 because
F2 introduces staff who may see only some screens (the `kueche` role builds on
that).

**Not in this roadmap**, because each needs accounts, legal care or data the
hotel has not given yet: Stripe or payment links, Booking.com and the channel
manager, an AVS interface, invoices and a group bill across rooms (needs a
GoBD-compliant invoice model first), the hotel website, AI purchasing
suggestions (needs months of F8 data). Do not start any of these, even partly.

## Rules for every feature

1. **Scope.** Build what your feature document says, all of it, and nothing
   else. If the document is wrong or unclear, pick the reading closest to the
   manager's words, build that, and say so in the pull request under
   "Abweichungen". Do not stop to ask; nobody is watching the run.
2. **Branch and pull request.** Branch from the current `main` as named in the
   table. One pull request against `main`, titled `F<n>: <feature title>`.
   Body: every acceptance criterion as a checked box with where it is tested,
   the test command output summary, screenshot paths, "Abweichungen", and
   "Offene Fragen".
3. **Tests are the gate.** Every acceptance criterion has at least one test.
   The gate commands in `AGENTS.md` pass before you open the pull request. Never
   delete, skip or loosen an existing test to make it pass. When your feature
   removes a behaviour on purpose (F1 removes check-in steps), replace the tests
   for that behaviour with tests for the new one, and list them in the pull
   request.
4. **Blocked?** Write the blocker into `BLOCKERS.md` at the repository root on
   your branch (what, why, what you tried, what you did instead), finish
   everything else in the feature, and open the pull request anyway.
5. **Hands off** `src/kurort_engine/` (the regulatory library), `spec/` (old
   engine contracts), `deploy/` and `src/kurort_app/auth.py`, unless your
   feature document names the change. Never add a runtime dependency your
   document does not allow.
6. **Screenshots.** Run the app with demo data and save screenshots of every
   new or changed screen at 1280 px and 390 px width as
   `f<n>-<screen>-<width>.png`: into `output/screenshots/` if your workspace
   has an `output/` folder, otherwise into `.screenshots/` in the repository
   (gitignored, never committed). A screen that needs horizontal scrolling at
   390 px is a bug.

## Shared contracts

**Migrations.** One hand-written Alembic migration per feature, file
`src/kurort_app/migrations/versions/<NNNN>_<slug>.py`, revision id equal to
the file stem (`"0003_app_platform"`), `NNNN` taken from the table above.
`down_revision` is the newest revision on the `main` you branched from; the
first migration's id is just `"0001"`, so wave-1 features write
`down_revision = "0001"`. The migration has a working `downgrade()`.
Migrations create schema only, never rows (see "Default rows").
`tests/app/test_migrations.py` already checks that the whole chain upgrades,
downgrades and upgrades again and has a single head, so you add no migration
test of your own unless you migrate data (F1 does). Never edit
`0001_initial_schema` or another feature's migration. When pull requests merge
in a different order, the integrator re-points `down_revision`; you do not
need to plan for that. F7 and F8 are expected to need no migration (apps store
records in F3's tables); if one does need one, use `0008` (F7) or `0009` (F8).

**Default rows.** Business-setting rows a fresh installation needs (payment
methods, e-mail templates, seminar room prices, safe compartments) come from an
idempotent `ensure_*(session)` function in the feature's service module,
listed as `"module:function"` in `DEFAULTS` in `src/kurort_app/defaults.py`.
It inserts only what is missing and never overwrites rows staff changed.
`kurort-app migrate` and the demo seed run them. The `db` test fixture empties
every table, so a test that needs those rows calls
`defaults.ensure_defaults(db)` or uses the `seeded` fixture.

**Status vocabularies** stay plain strings with a database check constraint,
defined once in `models.py` (see the existing `RESERVATION_STATUSES`). German
display labels live in `web.py` next to the existing label maps.

**Meldeschein states after F1:** `offen` (nothing printed), `gedruckt`
(printed in AVS), `unterschrieben` (signed and handed in). F5's late-arrival
list uses `unterschrieben` as "handed in". Existing `erzeugt` rows become
`gedruckt` in F1's migration.

**"Heute" rows and extension points (F1 builds, F2/F4/F5 extend).** F1
creates `src/kurort_app/services/today.py` with these names, moving the
existing `Flag` there from `routers/front_desk.py`:

```python
@dataclass(frozen=True)
class Flag:                      # unchanged fields
    text: str
    kind: str                    # success | warning | danger | info
    href: str | None = None      # new: where the flag's fix lives

@dataclass
class TodayRow:
    kind: str                    # "anreise" | "abreise"
    reservation: Reservation     # guests, room and kurtaxe loaded
    flags: list[Flag]            # filled by FLAG_PROVIDERS

FlagProvider = Callable[[Session, TodayRow], list[Flag]]
CheckinBlocker = Callable[[Session, Reservation], list[engine.Blocker]]
CheckoutWarning = Callable[[Session, Reservation], list[Flag]]
DashboardNotice = Callable[[Session, date], list[Flag]]

FLAG_PROVIDERS: list[FlagProvider]
CHECKIN_BLOCKERS: list[CheckinBlocker]       # any blocker stops "Check-in abschließen"
CHECKOUT_WARNINGS: list[CheckoutWarning]     # shown on the check-out page; staff may proceed
DASHBOARD_NOTICES: list[DashboardNotice]     # one-line notices above the "Heute" table
```

`engine.Blocker` is the existing dataclass in `services/engine.py`; F1 adds
two optional fields, `action_label` and `action_url`, so a blocker can offer
its fix as a button (F2's "Als sauber markieren"). A wave-2 feature writes its
provider in its own module and registers it with one appended line, e.g.
`FLAG_PROVIDERS.append(room_not_clean_flags)`, in a module that `today.py`
imports at its end. It does not edit F1's providers.

**Roles.** Today: `rezeption` and `leitung`; a logged-in user without one sees
"Kein Zugriff". F2 adds `housekeeping` (sees only the room status screen) and
the plumbing for such limited staff: front-desk routers require `rezeption` or
`leitung`, and the start page `/` sends a limited user to their own area. The
sidebar already shows only the links whose `roles` match the user. F7 adds
`kueche` on top of F2's plumbing; F8, which runs in parallel, adds it the same
way only if F7 is not merged yet, and the integrator keeps one copy. Settings
screens (payment methods, e-mail templates, prices, app catalogue) require
`leitung`. A new role is also added to the demo realm in
`deploy/k3d/keycloak/` with one demo user (password as the others), which is
the one `deploy/` change F2 and F7 may make; each then updates
`test_demo_keycloak_realm_matches_the_app_contract`, which asserts the exact
role set. Role tests use the `idp` and `oidc_client` fixtures and `login()`
from `tests/app/auth_helpers.py`.

**Sidebar.** Keep it short; the manager asked for less. Final order:

- *Heute*: Übersicht, Anreisen, Abreisen, Im Haus, Zimmerstatus (F2)
- *Planung*: Reservierungen, Zimmerplan, Seminarraum (F6)
- *Apps* (F3): one link per installed app the user may open
- *Verwaltung* (only `leitung`): Zahlungsarten (F4), E-Mail & Safe (F5:
  templates and safe compartments), Apps verwalten (F3), Seminarraum-Preise
  (F6)

Lists that are not in the sidebar (open payments, the e-mail outbox) are
reached from the screens that need them. The sidebar is data: `NAV` in
`web.py`, a list of `NavItem(href, label, icon, group, roles, match)`. A
feature adds its link with one `NAV.append(NavItem(...))` in its own module;
links that depend on the database (F3's installed apps) come from a function
appended to `NAV_PROVIDERS`. `templates/base.html` renders the groups in
`NAV_GROUPS` order, hides empty groups and filters by role. Do not write links
into `base.html`.

**Business settings** that the hotel changes (payment methods, e-mail
templates, prices, safe compartments) live in database tables with a
`leitung` screen and default rows from `DEFAULTS`. Infrastructure settings
(SMTP host, time limits) are `KURORT_*` environment variables in `config.py`.

**Demo data.** Extend `seed.py` so the demo shows your feature on the business
date: a few dirty rooms, an open balance, a late arrival, a seminar booking.
Apps (F7, F8) bring their demo records through F3's demo hook instead of
editing `seed.py`. Use your own `random.Random(SEED + n)` so the existing demo
stays unchanged, keep the seed deterministic and keep
`kurort-app seed --reset` working (it empties every table, then runs
`DEFAULTS` and the seed).

**The assistant** (`services/assistant/`) drives routes by name in its demo
rules. If you change or remove a route it uses, update the planner and
`tests/app/test_assistant.py` in the same pull request.

## After the run

The integrator reviews each pull request, re-chains migrations where needed,
merges in wave order, and checks every screen in the browser on the k3d demo. Agents cannot judge the look of a screen; the
screenshots make that review fast.
