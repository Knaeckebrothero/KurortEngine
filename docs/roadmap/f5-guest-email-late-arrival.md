# F5: Guest e-mail and late arrival

| | |
|---|---|
| Wave | 2 |
| Depends on | F1 (`services/today.py`, Meldeschein states `offen`/`gedruckt`/`unterschrieben`) |
| Branch | `feature/f5-guest-email` |
| Migration | `0007_guest_email` |
| Size | L |

## Why

The manager: *"E-Mails aus Vorlagen versenden (kann Resavio)."* And:
*"Späte Anreise (nach 18 Uhr): Meldeschein und Zimmerschlüssel kommen in den
Safe, der Gast bekommt eine E-Mail mit PIN. Nachhalten, wer den Meldeschein
abgegeben hat."* Today the desk writes such mails by hand, and nothing records
which late guest still owes the signed Meldeschein the next morning.

## What to build

1. **Templates and outbox.** Hotel-editable German e-mail templates with
   placeholders, sent from a reservation with a preview, logged in an outbox.
   Without a mail server the app still works: messages are stored and marked
   "protokolliert – nicht versendet".
2. **Late arrival.** The "Heute" table marks arrivals expected at or after
   18:00. Staff prepare them before leaving: choose a safe compartment, tick
   key and Meldeschein, send the PIN mail. Next morning a list shows who
   arrived, whose Meldeschein is still missing, and who never came.

## Scope

- Templates (`leitung` edits, live preview), safe compartments (`leitung`).
- Compose → preview → send from the reservation detail; message history on the
  detail page; outbox list with retry for failures.
- Transports `log` (default) and `smtp`, synchronous, plain text.
- Late-arrival preparation, PIN handling, morning list, completion, no-show.
- Demo data and tests.

## Not in scope

HTML mails, attachments, a background queue or scheduled/automatic mails
(every mail is sent by a person), inbound mail, bulk mail, newsletters,
per-language templates (German only), SMS, safe hardware integration. The
signed Meldeschein itself stays paper (AVS).

## Data model

Migration `0007_guest_email` creates four tables (schema only; default rows
come from `defaults.py`, see below).

**`email_templates`**: `id`; `key` `String(40)` unique (slug); `name`
`String(80)`; `subject` `String(200)`; `body` `Text`; `system` bool (default
false; system templates cannot be deactivated or renamed); `active` bool
(default true); `updated_at`, `updated_by`.

Defaults: `buchungsbestaetigung` Buchungsbestätigung · `anreiseinformationen`
Anreiseinformationen · `spaetanreise` Spätanreise (`system`) · `nach_abreise`
Nach der Abreise. Write real German texts (formal "Sie", warm, short; the
Spätanreise mail names the compartment, the PIN, the room, and asks to drop
the signed Meldeschein in the box at reception or leave it in the room).

**`email_messages`**: `id`; `reservation_id` FK null `ON DELETE SET NULL`,
indexed; `template_key` `String(40)` null; `to_address` `String(160)`;
`subject`; `body` `Text` (exactly as sent); `transport` `String(8)`
(`log`|`smtp`); `status` `String(10)` check in `queued`, `sent`, `failed`,
`logged`; `error` `Text` null; `attempts` int default 0; `created_at`,
`created_by`, `sent_at` null.

**`safe_compartments`**: `id`; `label` `String(40)` unique ("Fach 1");
`fixed_pin` `String(8)` null (digits only); `active` bool; `position` int.
Defaults: "Fach 1", "Fach 2", "Fach 3", all without a fixed PIN.

**`late_arrivals`**: `id`; `reservation_id` FK unique `ON DELETE CASCADE`;
`compartment_id` FK; `pin` `String(8)` null; `key_in_safe` bool;
`meldeschein_in_safe` bool; `status` `String(16)` check in `vorbereitet`,
`angereist`, `abgeschlossen`, `abgebrochen`, `nicht_angereist`;
`email_message_id` FK null; `phone_notified_at` null; `prepared_at`,
`prepared_by`, `arrived_confirmed_at` null, `meldeschein_returned_at` null,
`closed_at` null.

**Default rows.** Keep the defaults as constants in
`services/mail_templates.py` and `services/late_arrival.py` with idempotent
`ensure_email_templates(session)` / `ensure_safe_compartments(session)`
(insert what is missing by `key`/`label`, never overwrite rows the manager
edited) and register both in `src/kurort_app/defaults.py`. `kurort-app
migrate` and the demo seed run them; the migration inserts nothing. The test
fixtures empty every table before each test, so tests that need the defaults
call `defaults.ensure_defaults(db)` or use `seeded`.

**Settings** (`config.py`): `mail_transport: Literal["log", "smtp"] = "log"`,
`smtp_host`, `smtp_port = 587`, `smtp_user`, `smtp_password`, `smtp_from`
(e.g. `"Hotel Rheinland <info@…>"`), `smtp_security: Literal["starttls",
"ssl", "none"] = "starttls"`, `late_arrival_from: time = 18:00`. With
`KURORT_MAIL_TRANSPORT=smtp` but no host or sender, `create_app` refuses to
start with a clear message (like the login settings do).

## Templates

Rendered with `jinja2.sandbox.SandboxedEnvironment(undefined=StrictUndefined,
autoescape=False)`. The context holds only preformatted German strings:

| Placeholder | Example |
|---|---|
| `gast.vorname`, `gast.nachname`, `gast.name` | Anna, Weber, Anna Weber |
| `reservierung.code`, `.anreise`, `.abreise`, `.naechte`, `.zimmer`, `.kategorie`, `.ankunftszeit` | R-2610-0042, Mittwoch, 14. Oktober 2026, …, 3, 204, Doppelzimmer, 21:30 |
| `hotel.name`, `hotel.ort` | Hotel Rheinland, Bad Orb |
| `safe.fach`, `safe.pin` | Fach 2, 4817 (only in the late-arrival flow) |

An unknown placeholder or a syntax error is shown as "Unbekannter Platzhalter:
gast.vornamee" (or the Jinja message in German framing) in the preview and
blocks saving a template and sending a mail. The editor lists the
placeholders. The subject is one line (newlines rejected).

## Sending

`services/mail.py`: `send(session, message) -> EmailMessageRow`. Builds an
`email.message.EmailMessage` (UTF-8, `From` = `smtp_from`, `To`, `Subject`,
`Date`, `Message-ID`), then:

- `log`: no network; `status = logged`, `sent_at` set. Shown as
  "protokolliert – nicht versendet (kein Mailserver eingerichtet)".
- `smtp`: `smtplib.SMTP(host, port, timeout=10)` (+ `starttls()`), or
  `SMTP_SSL` for `ssl`; login when a user is set. Success → `sent`. Any
  `smtplib`/`OSError` → `failed` with the error text; the page shows it and
  offers "Erneut senden". Retry reuses the row (`attempts + 1`).

The message row is committed before the network call (`queued`), so a crash
mid-send leaves a visible row. No new dependencies.

## Screens and routes

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/reservierungen/{id}/e-mail` | rezeption, leitung | compose: template, to, subject, body (`?vorlage=key`) |
| POST | `/reservierungen/{id}/e-mail/vorschau` | rezeption, leitung | htmx: rendered preview |
| POST | `/reservierungen/{id}/e-mail` | rezeption, leitung | send |
| GET | `/e-mails` | rezeption, leitung | outbox, newest first, `?status=failed` |
| GET | `/e-mails/{mid}` | rezeption, leitung | one message as sent |
| POST | `/e-mails/{mid}/erneut` | rezeption, leitung | retry a failed message |
| GET | `/verwaltung/e-mail` | leitung | templates and safe compartments |
| GET/POST | `/verwaltung/e-mail/vorlagen/{key}` | leitung | edit a template (htmx live preview against a demo stay) |
| POST | `/verwaltung/e-mail/vorlagen` | leitung | new template |
| POST | `/verwaltung/safe-faecher`, `/verwaltung/safe-faecher/{id}` | leitung | add, edit, (de)activate a compartment |
| GET/POST | `/spaetanreise/{reservation_id}` | rezeption, leitung | prepare a late arrival |
| POST | `/spaetanreise/{reservation_id}/pin` | rezeption, leitung | htmx: reveal the PIN |
| POST | `/spaetanreise/{reservation_id}/telefonisch` | rezeption, leitung | "Gast telefonisch informiert" |
| POST | `/spaetanreise/{reservation_id}/abbrechen` | rezeption, leitung | undo the preparation |
| GET | `/spaetanreisen` | rezeption, leitung | morning list |
| POST | `/spaetanreise/{reservation_id}/angekommen` | rezeption, leitung | guest arrived: check in |
| POST | `/spaetanreise/{reservation_id}/meldeschein` | rezeption, leitung | Meldeschein handed in |
| POST | `/spaetanreise/{reservation_id}/nicht-angereist` | rezeption, leitung | no-show |

**Reservation detail** gets a card "E-Mails": the last three messages (date,
template, status as text: "gesendet", "protokolliert – nicht versendet",
"fehlgeschlagen"), "Alle E-Mails" (outbox filtered to the stay) on demand, and
the button "E-Mail senden". The `spaetanreise` template is not offered there;
it belongs to the late-arrival flow. Without a guest e-mail address the button
is replaced by "Keine E-Mail-Adresse hinterlegt".

**Compose** (`/reservierungen/{id}/e-mail`): template select (changing it
reloads subject and body via htmx), "An" prefilled with the primary guest's
address, subject and body as editable fields (staff may adjust before
sending), the preview below. "Senden" → back to the detail with the result as
notice.

**Verwaltung → E-Mail & Safe** (`/verwaltung/e-mail`): template list (name,
last change, active), "Neue Vorlage"; below, section "Safe-Fächer für
Spätanreisen": label, "fester Code" (shown masked, `leitung` only), active.

**Late arrival preparation** (`/spaetanreise/{id}`): guest, room, ETA; each
guest's Meldeschein state; CHECKIN_BLOCKERS shown as hints ("Zimmer noch nicht
sauber"), not blocking. Form: compartment (active ones without an open late
arrival), "Schlüssel liegt im Safe", "Meldeschein liegt im Safe", then
"Vorbereiten und E-Mail senden" (or "Vorbereiten" without an address). After
saving, the page shows the PIN in clear once ("PIN 4817 – jetzt am Safe Fach 2
einstellen" for a generated PIN, "Fester Code von Fach 1" for a fixed one),
the mail status, and for missing addresses "Keine E-Mail-Adresse – PIN
telefonisch mitteilen" with the "Gast telefonisch informiert" button. Later
visits show the PIN masked with "PIN anzeigen".

**Morning list** (`/spaetanreisen`): two sections. "Von gestern und früher":
records in `vorbereitet` (actions "Angekommen", "Nicht angereist") or
`angereist` with a Meldeschein not back (action "Meldeschein abgegeben"). "Heute
Abend": today's prepared arrivals. Linked from the arrivals page header and a
dashboard notice ("1 Spätanreise: Meldeschein ausstehend"), shown only when
the first section is not empty.

At 390 px every screen stacks; the preparation form and the morning list are
usable one-handed (44 px targets, actions full width).

## Rules

- **Late** = arrival on the business date, status `reserved`, `eta >=
  late_arrival_from`. Register a `FLAG_PROVIDER` for `anreise` rows: not
  prepared → `Flag("Spätanreise 21:30 · vorbereiten", "warning",
  href="/spaetanreise/{id}")`; prepared → `Flag("Spätanreise vorbereitet ·
  Fach 2", "info")`. The detail page of any reserved stay arriving today
  offers "Spätanreise vorbereiten" too (guest called, no ETA).
- **Prerequisite:** every guest's Meldeschein is `gedruckt` or `unterschrieben`
  (printed in AVS via F1's check-in step); otherwise preparation is refused
  with "Meldeschein erst in AVS drucken" and a link to that step.
  "Meldeschein liegt im Safe" requires it too.
- **PIN:** a compartment with `fixed_pin` uses it and stores nothing on the
  late arrival (`pin` null). Otherwise generate 4 digits with `secrets`,
  rejecting all-equal digits and straight runs (`1234`, `9876`), store it in
  `late_arrivals.pin`. A compartment holds at most one open (`vorbereitet`)
  late arrival.
- **Who sees the PIN:** `rezeption` and `leitung` only, on the preparation
  page; each reveal records `late_arrival_pin_viewed`. Never in audit
  payloads, logs, the outbox list or the reservation detail.
- **Clearing:** on `angereist`, `abgebrochen` or `nicht_angereist` set `pin`
  to null, free the compartment, and replace the PIN in the stored body of the
  Spätanreise message with "••••".
- **Status of the stay:** the reservation stays `reserved` overnight and is
  checked in when staff confirm "Angekommen" the next morning
  (`checked_in_at` = that moment). Reason: nobody sees the guest arrive, a
  guest who never comes must not count as in house, and the key in the safe
  is the evidence staff check. During the night "Im Haus" therefore does not
  list the guest; the room is still booked in the Zimmerplan, and the morning
  list is the first task of the shift.
- **Angekommen** sets the stay `checked_in` and the record `angereist`
  (Kurtaxe as F1 computes it at check-in). It does not run `CHECKIN_BLOCKERS`
  (the guest has already slept in the room) and does not wait for the signed
  Meldeschein; the record stays on the morning list
  until "Meldeschein abgegeben", which sets every guest's state to
  `unterschrieben` and the record to `abgeschlossen`. (Ticking the Meldeschein
  first and arriving second also ends in `abgeschlossen`.)
- **Nicht angereist** sets the stay `no_show` and the record
  `nicht_angereist`; the key and Meldeschein are back at the desk.
- **Abbrechen** (guest arrives before staff leave, or cancels): record
  `abgebrochen`; normal check-in applies again.
- **Audit** (entity `reservation`, id = reservation id): `email_sent`,
  `email_logged`, `email_failed`, `email_retried` (payload: message id,
  template key, recipient; no body), `late_arrival_prepared` (compartment
  label, fixed or generated, no PIN), `late_arrival_pin_viewed`,
  `late_arrival_phone_notified`, `late_arrival_arrived`,
  `late_arrival_meldeschein_returned`, `late_arrival_no_show`,
  `late_arrival_cancelled`. Templates: entity `email_template`, actions
  `email_template_created`, `email_template_updated`; compartments: entity
  `safe_compartment`, `safe_compartment_created`, `safe_compartment_updated`.
- **Dashboard notice:** register a function in F1's `DASHBOARD_NOTICES`
  (`services/today.py`) for the morning notice, linking to `/spaetanreisen`.
  Do not edit the dashboard template.

## Acceptance criteria

- **AC-1** After `defaults.ensure_defaults()`, the four default templates and
  three compartments exist and `spaetanreise` is a system template; running it
  again after the manager edited a template leaves the edit in place.
- **AC-2** Rendering `buchungsbestaetigung` for a seeded stay yields the
  guest's first name, the German arrival date and the room number; an unknown
  placeholder yields the error "Unbekannter Platzhalter" and blocks saving
  (template editor) and sending (compose).
- **AC-3** With `KURORT_MAIL_TRANSPORT=log`, sending from the compose page
  creates a message `logged` with the exact subject and body, records
  `email_logged`, and the detail page shows "protokolliert – nicht versendet".
- **AC-4** With `smtp` and a fake `smtplib.SMTP` (monkeypatched), the fake
  receives one message with the right `From`, `To`, `Subject` and UTF-8 body;
  the row is `sent`. When the fake raises `SMTPException`, the row is `failed`
  with the error, the page shows "fehlgeschlagen" and "Erneut senden"; a retry
  that succeeds sets `sent` and `attempts = 2`.
- **AC-5** `smtp` without host or sender → `create_app` raises with a message
  naming the missing variables.
- **AC-6** `leitung` edits a template and the change is used by the next mail;
  `rezeption`-only users get 403 on `/verwaltung/e-mail` (OIDC test app);
  system templates cannot be deactivated.
- **AC-7** On the business date the "Heute" table shows "Spätanreise … ·
  vorbereiten" for a reserved arrival with ETA 18:00 or later and none for
  ETA 17:59.
- **AC-8** Preparing with a compartment without fixed PIN stores a 4-digit PIN
  that is not all-equal or a straight run, sends (logs) the `spaetanreise`
  mail containing the compartment and PIN, and shows the PIN once; a second
  GET shows it masked. With a fixed-PIN compartment the mail contains the
  fixed PIN and `late_arrivals.pin` is null.
- **AC-9** Preparation is refused while a guest's Meldeschein is `offen`; an
  occupied compartment is not offered; no e-mail address → no message, the
  page shows "PIN telefonisch mitteilen", and the phone button records
  `late_arrival_phone_notified`.
- **AC-10** No audit payload, outbox list or reservation detail contains the
  PIN; revealing it records `late_arrival_pin_viewed`.
- **AC-11** Next business day: `/spaetanreisen` lists the record; "Angekommen"
  checks the stay in (`checked_in`, `checked_in_at` set), clears the PIN and
  masks it in the stored mail body; the record stays listed until
  "Meldeschein abgegeben", which sets all guests to `unterschrieben` and the
  record to `abgeschlossen`.
- **AC-12** "Nicht angereist" sets the stay `no_show`, clears the PIN, frees
  the compartment; "Abbrechen" frees it and returns the stay to the normal
  check-in.
- **AC-13** `seed --reset` on the business date shows: one late arrival today
  (ETA 21:30, e-mail address, Meldeschein `gedruckt`) not yet prepared, and one
  from yesterday prepared and still `reserved` (compartment "Fach 2", logged
  mail), so the morning list is not empty. The seed stays deterministic.

## Tests

- `tests/app/test_guest_email.py`: AC-1 to AC-6 (templates, rendering,
  transports with a monkeypatched `smtplib`, config validation, roles via the
  `idp` and `oidc_client` fixtures and `login()` from
  `tests/app/auth_helpers.py`).
- `tests/app/test_late_arrival.py`: AC-7 to AC-13, moving the business date
  with `KURORT_TODAY` and the settings cache reset the conftest already uses.
- No real network in any test.

## Files

New: `services/mail.py`, `services/mail_templates.py`,
`services/late_arrival.py`, `routers/mail.py`, `routers/late_arrival.py`,
`templates/mail/…`, `templates/late_arrival/…`, `static/mail.css`,
`migrations/versions/0007_guest_email.py`, the two test files. Changed:
`models.py`, `config.py` (mail settings), `main.py` (routers; startup check
next to `auth.validate_settings`), `templates/reservations/detail.html`
(E-Mails card, "Spätanreise vorbereiten"), `routers/reservations.py` (load
messages), the arrivals page header link, `seed.py` (demo late arrivals),
`defaults.py` (two entries), `base.html` (stylesheet), one registration line
each for the flag provider and the sidebar link, in `routers/mail.py`:
`NAV.append(NavItem("/verwaltung/e-mail", "E-Mail & Safe", <icon>,
"Verwaltung", roles=("leitung",)))`.

Seed note: draw from its own `random.Random(SEED + 5)` so existing stays stay
unchanged; set the two late arrivals explicitly rather than by chance.

## Decided defaults

- **Mail account / sender** (open question): none until the hotel provides
  one; `log` transport by default, so everything works and is visible. Going
  live = set `KURORT_MAIL_TRANSPORT=smtp` and the `KURORT_SMTP_*` variables.
- **Safe PIN fixed or per guest** (open question): both, per compartment. A
  compartment with a fixed code uses it; one without gets a new PIN per guest.
  The manager sets this on the compartment list; no global mode.
- **Late from** 18:00 (`KURORT_LATE_ARRIVAL_FROM`), from the manager's words.
- **Template texts:** German defaults written by the implementer; the manager
  edits them on "E-Mail & Safe".
