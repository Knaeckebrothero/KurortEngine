# Working on KurortEngine

The staff web application for Hotel Rheinland, a 33-room hotel in the spa town
Bad Orb (Hessen): reception, reservations, check-in, Kurtaxe. German UI,
Python backend, server-rendered HTML.

**Current work:** [`docs/roadmap/`](docs/roadmap/README.md). Read its README
and your feature document before you change anything.

## Layout

| Path | What |
|---|---|
| `src/kurort_app/` | The web app: FastAPI, Jinja2 templates, htmx, SQLAlchemy 2, Alembic, Postgres |
| `src/kurort_app/routers/` | One router per area (`front_desk`, `reservations`, `checkin`, `assistant`) |
| `src/kurort_app/services/` | Logic the routers share; `engine.py` adapts the regulatory library |
| `src/kurort_app/templates/<area>/`, `static/<area>.css` | Screens and styles per area |
| `src/kurort_app/models.py`, `migrations/versions/` | Database model and hand-written migrations |
| `src/kurort_app/seed.py` | Deterministic demo data around the business date |
| `src/kurort_engine/` | Regulatory library (Kurtaxe, Meldeschein, Satzung profiles). Used, not changed |
| `tests/app/` | Web app tests (real Postgres). Other `tests/` files belong to the library |
| `docs/design/theme.md` | The UI theme ("Rheinland Reception Standard") and its tokens |

## Setup

Python 3.12 (3.11 works, but the embedded test Postgres has wheels for
3.10–3.12 only).

```bash
python3 -m venv .venv                      # or: uv venv --python 3.12 .venv
.venv/bin/pip install -e ".[web,dev,test-pg]"
```

The app tests need Postgres. With podman, start the container from
[`docs/ops/local-development.md`](docs/ops/local-development.md). Without it,
the `test-pg` extra is enough: the tests start an embedded Postgres themselves.

## Gate: run before every commit you push

```bash
KURORT_TEST_REQUIRE_DB=1 .venv/bin/python -m pytest tests/app -q
.venv/bin/python -m pytest -q \
  --deselect tests/test_a11y_guest_pwa.py::test_ac2_wcag_aa_audit_infra_with_manual_fallback \
  --deselect tests/test_audit_isolation.py::test_ac2_full_suite_exits_zero
.venv/bin/ruff check src/kurort_app tests/app scripts
.venv/bin/ruff format --check src/kurort_app tests/app scripts
```

`KURORT_TEST_REQUIRE_DB=1` makes a missing database fail the run; without it
the app tests are silently skipped. The two deselected library tests fail on
`main` already (shared audit-log state in the library); leave them alone.

## Run the app with demo data

```bash
.venv/bin/python scripts/dev_postgres.py &      # prints KURORT_DATABASE_URL=...
export KURORT_DATABASE_URL=...                  # the printed value
export KURORT_AUTH=off KURORT_TODAY=2026-10-14
.venv/bin/kurort-app migrate
.venv/bin/kurort-app seed --reset
.venv/bin/kurort-app serve --port 8000
```

Open http://127.0.0.1:8000/. With podman Postgres instead, see
`docs/ops/local-development.md`. `KURORT_TODAY` pins the business date the
demo data is laid out around.

## Conventions

- **UI copy is German**, short and human ("Zimmer noch nicht sauber", not
  "Fehler: Status ungültig"). Code, identifiers and comments are English.
  Route paths are German (`/anreisen`, `/check-in/{id}/gaeste`).
- **Server-rendered.** Jinja2 pages, htmx for partial updates, a little plain
  JavaScript where needed. No build step, no JavaScript framework, no CSS
  framework.
- **Theme tokens only.** Colours, spacing, radii and type come from the custom
  properties in `static/app.css` (documented in `docs/design/theme.md`). No new
  colour values. Status is shown with text as well as colour.
- **Mobile.** Every new screen works at 390 px width without horizontal
  scrolling. Tables turn into stacked cards on narrow screens, as the arrivals
  queue does (`.fd-queue` in `static/front_desk.css`).
- **Details on demand.** Show the few facts staff act on; put the rest behind
  a disclosure (`<details>`), a row expansion or the detail page.
- **Writes** go through a POST handler that redirects (post/redirect/get) with
  `redirect_with_notice` from `web.py`, or return an htmx partial. Every staff
  write records an audit event with `audit.record(...)`.
- **Roles** are checked with `Depends(require_role(...))` from `auth.py`; it is
  a no-op when `KURORT_AUTH=off`, so test role checks with the `oidc_client`
  fixture (see Tests below).
- **Dates and money.** The business date is `config.today()`, never
  `date.today()`. Timestamps are stored in UTC and shown in Europe/Berlin with
  the `date`/`time` filters. Money is `Decimal` and `Numeric(10, 2)`, shown
  with the `money` filter.
- **Migrations** are hand-written Alembic files, one per feature, with a
  working `downgrade()`. Status values are strings with a check constraint.
- **Tests** use the fixtures in `tests/app/conftest.py`: `db` (empty tables),
  `seeded` (demo data), `client` (a `TestClient`, login off), and `idp` plus
  `oidc_client` with `login()` from `tests/app/auth_helpers.py` for role
  tests. Test behaviour through HTTP where you can: status codes, redirects,
  the German text on the page, and the database state afterwards.
- **Shared hooks** instead of shared edits: sidebar links via `web.NAV`,
  default rows via `defaults.DEFAULTS`; the roadmap README lists the rest.
- **Dependencies.** No new runtime dependency unless your feature document
  allows it. The standard library and what `pyproject.toml` already has go a
  long way (`reportlab` for PDFs, `smtplib` for mail).
- **Lint and format** with ruff (line length 100), as in the gate.
- **Commits** are small and say why. Author them with the repository's
  configured identity; do not add co-author trailers.

## Don'ts

- Don't change `src/kurort_engine/`, `spec/`, `deploy/` or `auth.py` unless
  your feature document says so.
- Don't delete, skip or weaken a test to get green.
- Don't commit secrets, `.env` files, `.pgdata/` or screenshots.
- Don't start work on anything the roadmap lists as "not in this roadmap".
