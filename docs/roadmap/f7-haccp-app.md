# F7: HACCP app

| | |
|---|---|
| Wave | 3 |
| Depends on | F2 (limited-staff plumbing), F3 (app platform), both merged |
| Branch | `feature/f7-haccp-app` |
| Migration | none planned (records live in F3's tables); `0008` if one is unavoidable |
| Size | M |

## Why

The owner built a HACCP prototype (Streamlit + Postgres) for the hotel's
kitchen: fridge and freezer temperatures with limits, goods receipt, open
food with use-by warnings, a cleaning schedule per station, PDF reports for
the food inspector. The manager agreed it should live inside the hotel's own
software instead of a separate tool with its own logins. F7 is the first real
app on F3's platform and its proof: if HACCP fits into one definition file
plus seed data, most hotel apps will.

Inspectors (Lebensmittelüberwachung) want the actual values with time and
name, the corrective action whenever a value is out of range, proof that the
cleaning plan is followed, and a printable record for a period. Those are
exactly F3's fields, ranges, schedules and reports.

## What to build

`src/kurort_app/apps/definitions/haccp.yaml` (slug `haccp`, title *HACCP*,
icon `thermometer`), a demo-data hook, the `kueche` role, and tests. No new
router, table or template unless F3 lacks something (see "Format limits").

## Scope

- Six collections: devices, temperature readings, goods receipt, open food,
  cleaning stations, cleanings.
- Two schedules: daily temperature per active device; cleaning per active
  station at its own frequency.
- One alert: open food past or near its use-by date.
- Four reports: temperature log, cleaning record, goods receipt, monthly
  report with all sections.
- Role `kueche` with its start page, plus a demo user.
- Deterministic demo data for the four weeks before the business date.

## Not in scope

- What the core app already covers: the prototype's guest list and arrival
  control (rooms checked before arrival are F2's status *geprüft*).
- The prototype's housekeeping logs: F2's audited room status changes are
  the room log.
- The prototype's own users, passwords and sessions (Keycloak replaces them).
- From the prototype's research notes, for later definitions: staff hygiene
  training records (Belehrung nach § 43 IfSG), pest control, allergen lists,
  the written HACCP plan, hot-holding checks every 1–2 hours during service,
  core cooking temperatures, wireless sensors, photos.
- A planned-versus-done comparison per station inside the cleaning report
  (the start page shows what is overdue).

## Data model

No tables. The definition (keys are binding; labels may be polished):

| Collection | Item | Fields (type) | Notes |
|---|---|---|---|
| `geraete` *Kühl- und Warmhaltegeräte* | Gerät | `name` (text, req.), `typ` (select: `kuehlschrank` Kühlschrank, `tiefkuehler` Tiefkühler, `kuehlzelle` Kühlzelle, `warmhaltung` Warmhaltung), `standort` (text), `soll_min`, `soll_max` (decimal, 1 place, °C), `aktiv` (boolean, default true) | `master: true`; edit `[kueche]`; help on the limits: "Kühlschrank 0 bis 7 °C, Tiefkühler −25 bis −18 °C, Warmhaltung ab 63 °C (Max leer lassen)" |
| `messungen` *Temperaturen* | Messung | `geraet` (reference → geraete, req.), `gemessen_am` (datetime, req., default `now`), `temperatur` (decimal, 1 place, °C, req., min −40, max 100, `range` from `geraet.soll_min`/`geraet.soll_max`, severity `warn`, `require_when_out_of_range: [massnahme]`), `massnahme` (textarea, label *Korrekturmaßnahme*), `mitarbeiter` (staff) | `date_field: gemessen_am`, `order_by: -gemessen_am`; help on Maßnahme: "Pflicht bei Abweichung, z. B. Tür geschlossen und nach 30 Minuten nachgemessen, Ware verworfen" |
| `wareneingang` *Wareneingang* | Lieferung | `geliefert_am` (date, req., default `today`), `lieferant` (text, req.), `produkt` (text, req.), `menge` (text, req., help "z. B. 10 kg, 3 Kartons"), `temperatur` (decimal, 1 place, °C, help "Kühlware höchstens 7 °C, Tiefkühlware höchstens −18 °C"), `mhd` (date, label *MHD / Verbrauchsdatum*), `charge` (text, label *Charge / Los*), `zustand_ok` (boolean, label *Verpackung und Ware einwandfrei*, default true), `ergebnis` (select: `angenommen` Angenommen, `abgelehnt` Abgelehnt; req., default `angenommen`), `bemerkung` (textarea, help "Bei Ablehnung: Grund"), `mitarbeiter` (staff) | `date_field: geliefert_am` |
| `offene_produkte` *Offene Lebensmittel* | Produkt | `produkt` (text, req.), `menge` (text), `geoeffnet_am` (date, req., default `today`), `verbrauchen_bis` (date, req., default `today+3`, help "In der Regel 3 Tage nach dem Öffnen; früher, wenn das Etikett es verlangt"), `erledigt` (boolean, label *Verbraucht oder entsorgt*), `mitarbeiter` (staff) | `date_field: geoeffnet_am`, `order_by: verbrauchen_bis` |
| `stationen` *Reinigungsplan* | Station | `name` (text, req.), `haeufigkeit_tage` (integer, req., min 1, max 90, default 1, label *Alle … Tage*), `hinweis` (textarea, label *Was gehört dazu*), `aktiv` (boolean, default true) | `master: true`; edit `[kueche]` |
| `reinigungen` *Reinigungen* | Reinigung | `station` (reference → stationen, req.), `erledigt_am` (datetime, req., default `now`), `aufgaben` (multiselect, req.: `oberflaechen` Oberflächen abgewischt, `geraet` Gerät gereinigt, `entkalkt` Entkalkt, `filter` Filter geprüft/gewechselt, `desinfiziert` Desinfiziert, `tiefenreinigung` Tiefenreinigung), `mittel` (text, label *Reinigungsmittel*), `mitarbeiter` (staff), `bemerkung` (textarea) | `date_field: erledigt_am`, `order_by: -erledigt_am` |

App roles: view `[kueche, rezeption]`, edit `[kueche, rezeption]` (`leitung`
always). Master data (`geraete`, `stationen`) is edited by `kueche` and
`leitung` only.

Schedules:

| Key | Title | Target → record via field | Interval |
|---|---|---|---|
| `temperatur` | Temperatur messen | `geraete` → `messungen` via `geraet`, at `gemessen_am` | `every_days: 1`, `when: aktiv` |
| `reinigung` | Reinigen | `stationen` → `reinigungen` via `station`, at `erledigt_am` | `every_days_field: haeufigkeit_tage`, `when: aktiv` |

Alert `verbrauch` (*Offene Lebensmittel*): field `verbrauchen_bis`,
`offset_days: 0`, `warn_days: 1`, `unless: erledigt`.

Reports (columns in this order):

| Key | Title | Sections |
|---|---|---|
| `temperatur` | Temperaturprotokoll | `messungen`: gemessen_am, geraet, temperatur, mitarbeiter, massnahme |
| `reinigung` | Reinigungsnachweis | `reinigungen`: erledigt_am, station, aufgaben, mittel, mitarbeiter |
| `wareneingang` | Wareneingang | `wareneingang`: geliefert_am, lieferant, produkt, menge, temperatur, mhd, charge, ergebnis |
| `gesamt` | HACCP-Monatsbericht | the three above plus `offene_produkte`: produkt, geoeffnet_am, verbrauchen_bis, erledigt |

## Demo data

Hook `demo: haccp_demo:seed_demo` in `src/kurort_app/apps/plugins/haccp_demo.py`,
written with F3's store API (actors `j.becker` and `m.schmidt`; set each
record's `created_at` to its own date where the API allows), deterministic
(`random.Random` with a fixed seed), relative to the anchor date *A*:

- **Devices:** Kühlschrank Küche (0–7), Kühlschrank Frühstücksbuffet (0–7),
  Getränkekühlschrank Bar (0–7), Tiefkühler Küche (−25 to −18), Warmhaltung
  Rührei (min 63, no max), all active.
- **Readings** once per device per day from A−28 to A−1, 07:00–08:30, inside
  the limits, except two deviations with a Maßnahme (Getränkekühlschrank
  8,4 °C at A−9 "Tür stand offen, nach 30 Min. 5,9 °C"; Tiefkühler −16,5 °C
  at A−3 "Abtauvorgang, nach 1 Std. −19,0 °C"). On A: a reading for
  Kühlschrank Küche only. Tiefkühler Küche has no reading on A−1 (its last
  is A−2), so it is *überfällig*; the other three are *fällig*.
- **Stations** (from the prototype plus one weekly): Kaffeemaschine,
  Teestation, Buffet, Eierstation (every day), Kühlschränke innen (every 7
  days). Cleanings daily until A−1, except Eierstation (last at A−2 →
  *überfällig*); Kühlschränke innen at A−5 (*erledigt*).
- **Goods receipt:** two deliveries a week for four weeks (dairy, meat,
  bakery, vegetables), one rejected: "Hackfleisch, 9,2 °C, Kühlkette
  unterbrochen, zurückgegeben" at A−6.
- **Open food:** six items: one past its date and not done (Milch, opened
  A−4, use by A−1 → *abgelaufen*), one due today (Sahne, use by A → *läuft
  ab*), two fine (use by A+2 or later), two marked done.

## Screens and routes

All screens come from F3; F7 adds none. The start page `/apps/haccp` is the
kitchen's main screen on a phone: *Fällig* first with "Jetzt erfassen" per
device or station, then *Warnungen* and *Abweichungen*, then the cards for
readings, deliveries, open food and cleanings. Master data sits under
*Stammdaten*.

## Role `kueche`

- Add `"kueche": "Küche"` to `ROLE_LABELS` in `auth.py`, after the roles F2
  added (the dict is ordered highest first).
- A `kueche`-only user is a limited user in F2's sense: use the mechanism F2
  introduced (read F2's document and code on `main`) to send them from `/` to
  `/apps/haccp`; front-desk screens answer 403; the sidebar shows only the
  *Apps* section (HACCP and, after F8, Inventur).
- Demo realm: add the role to the roles list in
  `deploy/k3d/keycloak/templates/realm-configmap.yaml` and a user to
  `deploy/k3d/keycloak/values.yaml`: `j.becker`, Jana Becker, roles
  `[kueche]`, the shared demo password. This is the only `deploy/` change
  allowed. Update
  `tests/test_deployment_artifacts.py::test_demo_keycloak_realm_matches_the_app_contract`,
  which asserts the exact role set.

## Format limits and how F7 handles them

| Prototype behaviour | F3 cannot express | F7 does instead |
|---|---|---|
| Per-station task lists | dynamic options | one shared task list (multiselect) + the station's *Was gehört dazu* hint |
| Reason required when a delivery is rejected | conditional required on a select | help text "Bei Ablehnung: Grund" |
| Delivery temperature limits by product kind | range depending on another select | help text only; no deviation flag |
| Deleting an open product | – (would lose the record) | *Verbraucht oder entsorgt* tick; records stay for the inspector |
| Report filtered to fridge or freezer | report filters | device column in the report |

If you find a prototype need that truly requires an F3 change, keep the
change tiny and generic, document it in `docs/apps/definition-format.md`,
test it, and list it in the pull request; otherwise drop the need and list
it under "Abweichungen".

## Rules

- No HACCP-specific Python outside `plugins/haccp_demo.py`. Everything else
  is the definition.
- Seed: `kurort-app seed --reset` leaves HACCP installed with the demo data
  above (through F3's demo hook; do not edit `seed.py`).
- Audit events are F3's (`app_record.created` etc.); nothing extra.

## Acceptance criteria

1. **AC-1** `kurort-app apps validate` passes for `haccp.yaml`; `/apps`
   lists *HACCP*; after `seed_demo_data(reset=True)` it is installed and
   enabled.
2. **AC-2** On the business date 2026-10-14 with the seed, `/apps/haccp`
   shows under *Fällig*: Tiefkühler Küche as *überfällig*; Kühlschrank
   Frühstücksbuffet, Getränkekühlschrank Bar and Warmhaltung Rührei as
   *fällig*; Eierstation as *überfällig*; Kaffeemaschine, Teestation and
   Buffet as *fällig*; not Kühlschrank Küche, not Kühlschränke innen.
3. **AC-3** *Warnungen* shows Milch as *abgelaufen* and Sahne as *läuft ab*,
   and no item marked done; *Abweichungen* shows the Tiefkühler reading of
   A−3 (inside the 7-day window), not the one of A−9.
4. **AC-4** Saving 8,5 °C for a fridge without Maßnahme → 422 with the
   Maßnahme message; with one → saved as *Abweichung*. −0,5 °C in a fridge,
   −15,0 °C in the freezer and 60,0 °C on the hot-holding unit are
   deviations; 4,0 °C, −20,0 °C and 75,0 °C are not.
5. **AC-5** "Jetzt erfassen" for Tiefkühler Küche opens the reading form
   with the device preselected and the time prefilled; after saving, the
   device leaves *Fällig*.
6. **AC-6** A cleaning needs at least one task (422 otherwise); saving one
   for Eierstation removes it from *Fällig*; a weekly station is not due
   before its seventh day.
7. **AC-7** A new open product defaults to use-by = business date + 3;
   ticking *Verbraucht oder entsorgt* silences its alert.
8. **AC-8** The report page lists the four reports; each PDF for the
   current month answers 200 with `application/pdf`; the row builder for
   *Temperaturprotokoll* over the last 28 days contains both seeded
   deviations with their Maßnahme; the goods-receipt CSV contains the
   rejected delivery with *Abgelehnt*.
9. **AC-9** With login on (OIDC test app): a `kueche` user is sent from `/`
   to `/apps/haccp`, may save readings and edit devices, gets 403 on
   `/anreisen`, and sees only the *Apps* section; a `rezeption` user may save
   readings but gets no edit button and 403 on POSTs for devices and
   stations; `ROLE_LABELS["kueche"] == "Küche"`.
10. **AC-10** The demo realm declares the role `kueche` and the user
    `j.becker` with it (a test reads both files and checks that every role a
    demo user has is declared).
11. **AC-11** Screenshots at 390 px of the start page, the reading form and
    the readings list show no horizontal scrolling.

## Tests

`tests/app/test_app_haccp.py`: AC-1 to AC-9 against the seeded database
(`seeded` fixture plus the demo hook; the business date is pinned to
2026-10-14 by the test setup). AC-10 in the same file or next to the existing
`tests/test_deployment_artifacts.py`.

## Files

New: `src/kurort_app/apps/definitions/haccp.yaml`,
`src/kurort_app/apps/plugins/haccp_demo.py`, `tests/app/test_app_haccp.py`.
Changed: `src/kurort_app/auth.py` (`ROLE_LABELS`), F2's role-to-start-page
mapping, `deploy/k3d/keycloak/values.yaml`,
`deploy/k3d/keycloak/templates/realm-configmap.yaml`.

## Decided defaults

- Hot-holding units are checked once a day like the fridges (the start page
  stays simple); several checks per service are a later definition.
- Use-by warning: 1 day before (the default use-by is already 3 days after
  opening, so the prototype's 3-day window would warn immediately).
- Reception may record readings and cleanings (small hotel, shared early
  shift) but not change devices or stations.
- Demo user `j.becker` (Jana Becker, Küche).
