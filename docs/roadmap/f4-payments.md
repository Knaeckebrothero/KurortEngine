# F4: Payment tracking

| | |
|---|---|
| Wave | 2 |
| Depends on | F1 (the "Heute" table and `services/today.py`) |
| Branch | `feature/f4-payments` |
| Migration | `0006_payments` |
| Size | M |

## Why

The manager: *"Erinnerungen: wer hat bezahlt, und wie (bei der Abreise
usw.)."* Today the app shows a bill preview at check-out (room + Kurtaxe) but
knows nothing about money received. Staff cannot see at a glance whether a
departing guest still has to pay, whether Booking.com already collected, or
which company still owes a transfer.

This feature records **payments received**, nothing more. It is **not an
invoice**: invoices stay in the hotel's current system until a GoBD-compliant
invoice model exists (not in this roadmap). Every screen that shows amounts
says so with the line *"Zahlungsübersicht – keine Rechnung."*

## What to build

A payment section on every reservation: what is due (room + Kurtaxe), what has
been paid and how, what is still open. A one-tap "Zahlung erfassen" form. The
"Heute" table tells the desk which departing guests still have to pay; the
check-out page warns and lets staff record the payment right there. A list of
open amounts, and a `leitung` screen for the payment methods.

## Scope

- Payment methods: a hotel-editable list (`leitung`), deactivate instead of
  delete.
- Payments per reservation: record, cancel with a reason (corrections), mark a
  deferred payment ("Auf Rechnung") as received.
- One balance service used everywhere (replaces `_balance` in
  `routers/front_desk.py`).
- Reservation detail: payment section. Check-out: warning plus inline payment
  form. "Heute": flag on departures. List "Offene Beträge".
- Demo data and tests.

## Not in scope

Invoices, invoice numbers, VAT, receipts, PDFs. Charges other than room and
Kurtaxe (minibar, breakfast extras, seminar room) and splitting one stay across
payers. Refunds as money movements (a cancelled payment is a correction, not a
refund). Stripe or payment links. Automatic e-mail reminders (F5 can send a
template by hand). Cancellation fees.

## Data model

Migration `0006_payments` creates two tables (schema only; default rows come
from `defaults.py`, see below).

**`payment_methods`**

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `code` | `String(32)` unique | slug, never changes (`bar`, `ec`, …) |
| `label` | `String(60)` | shown to staff, editable |
| `deferred` | bool, default false | money arrives later ("Auf Rechnung") |
| `active` | bool, default true | inactive methods are hidden in forms, kept on old payments |
| `position` | int | sort order |

Defaults (in this order): `bar` Bar · `ec` EC-Karte · `kreditkarte`
Kreditkarte · `ueberweisung` Überweisung · `booking` Booking.com
(vorausbezahlt) · `rechnung` Auf Rechnung (`deferred = true`).

**`payments`**

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `reservation_id` | FK `reservations.id` `ON DELETE CASCADE`, indexed | |
| `method_id` | FK `payment_methods.id` | |
| `amount` | `Numeric(10, 2)`, check `amount > 0` | euros |
| `paid_on` | `Date` | default the business date, never after it |
| `received_on` | `Date` null | = `paid_on` for normal methods; null for a deferred method until the transfer arrives |
| `payer` | `String(120)` null | e.g. "Firma Müller GmbH" when not the guest |
| `note` | `String(200)` null | |
| `recorded_by` / `recorded_at` | `String(60)` / timestamptz | actor from `audit`; `server_default now()` |
| `cancelled_at` / `cancelled_by` / `cancel_reason` | timestamptz / `String(60)` / `String(200)`, all null | a cancelled payment no longer counts |

Add `Reservation.payments` (ordered by `paid_on, id`) and `Payment.method`
relationships in `models.py`.

**Default rows.** Keep the list as `DEFAULT_METHODS` in
`services/payments.py` with an idempotent `ensure_payment_methods(session)`
(inserts missing codes, never touches existing rows) and register it in
`src/kurort_app/defaults.py` as
`"kurort_app.services.payments:ensure_payment_methods"`. `kurort-app migrate`
and the demo seed run the registered functions; the migration inserts nothing.
The test fixtures empty every table before each test, so a test that needs the
methods calls `defaults.ensure_defaults(db)` or uses `seeded`.

## Balance

`services/payments.py` owns the arithmetic:

```python
@dataclass(frozen=True)
class Balance:
    room: Decimal              # reservation.rate_total
    kurtaxe: Decimal | None    # None while not computed
    due: Decimal               # room + (kurtaxe or 0)
    paid: Decimal              # active payments, deferred ones included
    open: Decimal              # due - paid, may be negative (credit)
    awaiting: Decimal          # active deferred payments with received_on null
    state: str                 # "bezahlt" | "offen" | "guthaben"

def balance(reservation: Reservation) -> Balance: ...
```

- Cancelled and no-show stays: `due` is 0 (no fees in v1); payments on them
  show as credit ("Guthaben – Erstattung klären").
- Deferred payments count as paid at the desk (the guest may leave), and appear
  as `awaiting` until received.
- Labels: `bezahlt` → "Bezahlt", `offen` → "Offen 120,00 €", `guthaben` →
  "Guthaben 20,00 €"; with `awaiting > 0` add "· Rechnung offen 300,00 €".

## Screens and routes

| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | `/reservierungen/{id}/zahlungen` | rezeption, leitung | record a payment; `next` (local path only) chooses the redirect |
| POST | `/reservierungen/{id}/zahlungen/{pid}/stornieren` | rezeption, leitung | cancel a payment, reason required |
| POST | `/zahlungen/{pid}/eingang` | rezeption, leitung | deferred payment received (date) |
| GET | `/zahlungen/offen` | rezeption, leitung | list "Offene Beträge"; `?ansicht=rechnung` for open transfers |
| GET | `/verwaltung/zahlungsarten` | leitung | list, add, rename, (de)activate, reorder |
| POST | `/verwaltung/zahlungsarten` and `/verwaltung/zahlungsarten/{id}` | leitung | create, update |

**Reservation detail** gets a card "Zahlung" between "Kurtaxe" and "Notizen"
(anchor `#zahlung`). Essentials: the state label and the open amount, and a
"Zahlung erfassen" button. On demand (`<details>`): the breakdown (Logis,
Kurtaxe, Bezahlt, Offen) and the payment history (date, method, amount, payer,
who recorded it; cancelled ones struck through with the reason; "Stornieren"
behind its own `<details>` with a required reason). The form: amount
(prefilled with the open amount), method (active methods), date (business
date), payer and note behind "Weitere Angaben". German amounts: `120,50`,
`1.234,50` and `120.50` are accepted.

**Check-out page.** The "Abrechnung (Vorschau)" card shows Logis, Kurtaxe,
each payment, and an "Offen" row. Register a `CHECKOUT_WARNING`: open > 0 →
`Flag("Offener Betrag 120,00 € – bitte vor dem Check-out kassieren",
"warning")`, rendered above the confirm button together with the payment form
(`next=/check-out/{id}`). Staff may still check out; the audit payload of
`check_out` gets `open` (string amount).

**"Heute" table.** Register a `FLAG_PROVIDER` for `abreise` rows only:
`open > 0` → `Flag("Offen 120,00 €", "warning", href="/reservierungen/{id}#zahlung")`;
fully paid → `Flag("Bezahlt", "success")`. Arrival rows get no payment flag:
the desk collects at departure, and the manager asked for a quieter table.

**"Offene Beträge"** (`/zahlungen/offen`): stays with `open > 0` that are in
house or departed (departure, guest, room, open amount, "Zahlung erfassen"),
oldest departure first; second view "Rechnung offen": deferred payments not
received (payer, amount, since, "Eingang erfassen"). Reached from the
departures page header and a dashboard notice "3 offene Beträge" (shown only
when there are any; see Rules). Not in the sidebar.

**Zahlungsarten** (`leitung`): a short list with label, "Später bezahlt (auf
Rechnung)" switch, active switch, up/down buttons; one add form. The sidebar
entry is one line in `routers/payments.py`:
`NAV.append(NavItem("/verwaltung/zahlungsarten", "Zahlungsarten", <icon>,
"Verwaltung", roles=("leitung",)))` (`NAV`, `NavItem` from `web.py`).

At 390 px: the payment card stacks; the form fields are full width with 44 px
targets; both lists become stacked cards like `.fd-queue`.

## Rules

- Amount: > 0, at most two decimals, at most 100.000,00 €. Method must exist
  and be active. `paid_on` not after the business date. Errors re-render the
  form with the German message next to the field ("Betrag fehlt",
  "Zahlungsart wählen", "Datum liegt in der Zukunft").
- Overpayment is allowed and shows as "Guthaben"; the form shows a warning
  first when the amount exceeds the open amount ("Mehr als offen – Guthaben
  20,00 €").
- Payments can be recorded on reserved (prepayment), in-house, departed and
  no-show stays, not on cancelled ones (their existing payments can still be
  cancelled). Cancelling a payment needs a reason; a cancelled payment cannot
  be restored (record a new one).
- Deferred methods set `received_on = null`; others set it to `paid_on`.
- A method in use can be deactivated, renamed and reordered, never deleted;
  `code` is fixed after creation.
- Dashboard notice: register a function in F1's `DASHBOARD_NOTICES`
  (`services/today.py`) that returns the "{n} offene Beträge" notice with
  `href="/zahlungen/offen"`. Do not edit the dashboard template; nothing else
  on the dashboard changes.
- Audit (entity `reservation`, id = reservation id, so it shows in the stay's
  "Verlauf"; payload includes `payment_id`, `amount` as string, `method` code):
  `payment_recorded`, `payment_cancelled` (+ `reason`), `payment_received`.
  Methods: entity `payment_method`, actions `payment_method_created`,
  `payment_method_updated`.

## Acceptance criteria

- **AC-1** After `defaults.ensure_defaults()`, `payment_methods` holds the six
  defaults in order and "Auf Rechnung" is the only deferred one; running it
  again after a manager renamed one changes nothing.
- **AC-2** POST a payment of `120,50` "Bar" on a stay with due 400,00 € →
  303 to the detail page; the page shows "Offen 279,50 €"; the row has
  `received_on` = business date; an audit event `payment_recorded` exists.
- **AC-3** Invalid input (empty amount, `0`, `12,345`, inactive method, a date
  after the business date) → 200 with the German error, no row written.
- **AC-4** Cancelling a payment with a reason restores the open amount and
  records `payment_cancelled`; without a reason → error, nothing changes.
- **AC-5** A deferred payment covering the full amount makes the state
  "Bezahlt · Rechnung offen …"; it appears in `/zahlungen/offen?ansicht=rechnung`;
  after `/eingang` it is gone from there and `received_on` is set.
- **AC-6** `balance()` unit tests: no payments; partial; exact; overpaid
  (guthaben); Kurtaxe not computed (`kurtaxe is None`, `due` = room); cancelled
  stay with a payment → `due` 0, state `guthaben`; cancelled payments ignored.
- **AC-7** The "Heute" table on the business date shows "Offen …" for a
  departing stay with an open amount and "Bezahlt" for a paid one; arrival rows
  carry no payment flag.
- **AC-8** The check-out page of a stay with an open amount shows the warning
  and the payment form; recording a payment from there redirects back to the
  check-out page; checking out without paying still works and the `check_out`
  audit payload contains `open`.
- **AC-9** `/zahlungen/offen` lists in-house and departed stays with open
  amounts and no paid or cancelled ones.
- **AC-10** `/verwaltung/zahlungsarten`: `leitung` can add, rename, deactivate
  and reorder; a deactivated method disappears from the payment form but old
  payments keep their label; a `rezeption`-only user gets 403 (OIDC test app).
- **AC-11** The detail page and the check-out page say "Zahlungsübersicht –
  keine Rechnung."
- **AC-12** `seed --reset` on the business date yields: at least one departure
  with an open amount, one partly paid in-house stay, one Booking.com stay
  prepaid in full, one "Auf Rechnung" payment not yet received; most
  checked-out stays fully paid. The seed stays deterministic.

## Tests

- `tests/app/test_payments.py`: AC-1 to AC-11 through HTTP and the database;
  `balance()` unit tests for AC-6 with plain model objects.
- Role check (AC-10) with the `idp` and `oidc_client` fixtures and `login()`
  from `tests/app/auth_helpers.py`.
- AC-12 in `tests/app/test_payments.py` against the `seeded` fixture.
- Existing check-out tests in `tests/app/test_front_desk.py` must still pass;
  adapt only assertions on the bill card's exact text, and list them in the PR.

## Files

New: `services/payments.py`, `routers/payments.py`,
`templates/payments/{_card.html,_form.html,open.html,methods.html}`,
`static/payments.css`, `migrations/versions/0006_payments.py`,
`tests/app/test_payments.py`. Changed: `models.py` (two models, two
relationships, `Reservation.payments`), `main.py` (router), `routers/front_desk.py`
(use `balance()`, `open` in the audit payload, payment form on check-out),
`templates/front_desk/checkout.html`, `templates/reservations/detail.html`
(include `payments/_card.html`), `routers/reservations.py` (load
`Reservation.payments` with the reservation), `seed.py` (demo payments),
`defaults.py` (one entry), `base.html` (stylesheet), one registration line
each for the sidebar link, the flag provider and the check-out warning.

Seed note: draw payment data from its own `random.Random(SEED + 4)` so the
existing stays, guests and planted exceptions stay exactly as they are.

## Decided defaults

- **Which methods the hotel uses** (open question): the six above; the manager
  changes the list on "Zahlungsarten".
- **Booking.com prepaid**: recorded by hand as a payment with method
  "Booking.com (vorausbezahlt)"; the seed does it for some Booking.com stays.
  Automatic import comes with the channel manager (not in this roadmap).
- **Stripe / payment links**: not built. A later feature adds a method and a
  link; nothing here blocks it.
- **Extras and invoices**: the open amount covers room and Kurtaxe only, and
  the screens say it is not an invoice.
