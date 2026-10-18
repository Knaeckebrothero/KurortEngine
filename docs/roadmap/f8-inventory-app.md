# F8: Inventory and ordering app

| | |
|---|---|
| Wave | 3 |
| Depends on | F2 (limited-staff plumbing, for `kueche`), F3 (app platform); F7 for the `kueche` role if merged first, otherwise add it as F7 describes |
| Branch | `feature/f8-inventory-app` |
| Migration | none planned (records live in F3's tables); `0009` if one is unavoidable |
| Size | M |

## Why

Food for breakfast is ordered twice a week. Today the employee on shift
drafts the order and calls the manager; together they spend about 15 minutes
reconstructing what was already bought and cut a draft of roughly 750 € down
to roughly 350 €. Nothing is written down, so the same conversation repeats
every time (owner's example, see the pitch note on the closed ordering loop).

The manager listed inventory as a wish ("Inventur, Frühstück, Bestellung")
and AI order suggestions as a later idea. F8 is the first step of that loop:
**make stock and orders visible** and **suggest an order from simple rules**,
using what only this system knows, the guests expected for breakfast. Every
order records what was suggested and what was actually ordered, with a
reason when they differ. That history is what later, smarter suggestions
need; F8 does not build those.

## What to build

`src/kurort_app/apps/definitions/inventur.yaml` (slug `inventur`, title
*Inventur & Bestellung*, icon `cart`) with suppliers, articles, stock counts,
orders and order lines; one plugin view *Bestellvorschlag*; demo data; tests.

## Scope

- Five collections (below), reports and CSV through F3.
- The plugin view `bestellvorschlag`: per supplier, count, see the
  suggestion, adjust, save the order in one go.
- The breakfast forecast from reservations.
- Demo data: four suppliers, 26 articles, four weeks of counts and orders.

## Not in scope

- Learned or AI suggestions, weather or season factors (later, needs months
  of F8 data).
- Stock that books itself from deliveries or consumption; stock is what was
  last counted.
- Sending orders to suppliers (e-mail, portal), supplier price lists or
  price history, invoices.
- Linking deliveries to F7's HACCP goods receipt.
- Barcode scanning, several storage locations with transfers, recording
  calls.

## Data model

No tables. The definition (keys are binding; labels may be polished):

| Collection | Item | Fields (type) | Notes |
|---|---|---|---|
| `lieferanten` *Lieferanten* | Lieferant | `name` (text, req.), `bestellweg` (select: `telefon` Telefon, `email` E-Mail, `online` Online-Shop, `vertreter` Vertreter), `kontakt` (text), `liefertage` (text, help "z. B. Mo und Do"), `notiz` (textarea) | `master: true`; edit `[kueche]` |
| `artikel` *Artikel* | Artikel | `name` (text, req.), `kategorie` (select: `fruehstueck` Frühstück, `kueche` Küche, `getraenke` Getränke; req.), `einheit` (select: `stueck` Stück, `kg` kg, `l` l, `packung` Packung, `kiste` Kiste, `portion` Portion; req.), `lieferant` (reference → lieferanten, req.), `lagerort` (text, help "z. B. Kühlraum, Trockenlager, Tiefkühler"), `mindestbestand` (decimal, 2 places, min 0), `zielbestand` (decimal, 2 places, min 0), `packungsgroesse` (decimal, 2 places, min 0.01, default 1, help "Bestellt wird in Vielfachen davon"), `pro_fruehstueck` (decimal, 3 places, min 0, label *Verbrauch pro Frühstücksgast*), `preis` (decimal, 2 places, min 0, label *Preis pro Einheit (netto)*, unit €), `aktiv` (boolean, default true) | `master: true`; edit `[kueche]`; `list_fields: [name, kategorie, lieferant, zielbestand]` |
| `bestaende` *Bestände* | Zählung | `artikel` (reference, req.), `gezaehlt_am` (datetime, req., default `now`), `menge` (decimal, 2 places, req., min 0), `mitarbeiter` (staff) | `date_field: gezaehlt_am`, `order_by: -gezaehlt_am` |
| `bestellungen` *Bestellungen* | Bestellung | `lieferant` (reference, req.), `bestellt_am` (date, req., default `today`), `lieferung_am` (date, req.), `naechste_lieferung` (date), `fruehstuecke` (integer, label *Erwartete Frühstücke*), `status` (select: `bestellt` Bestellt, `geliefert` Geliefert, `storniert` Storniert; req., default `bestellt`), `notiz` (textarea), `mitarbeiter` (staff) | `date_field: bestellt_am`, `order_by: -bestellt_am` |
| `positionen` *Bestellpositionen* | Position | `bestellung` (reference, req.), `artikel` (reference, req.), `bestand` (decimal, 2 places), `vorschlag` (decimal, 2 places), `bestellt` (decimal, 2 places, req., min 0), `grund` (select, label *Grund für Abweichung*: `genug_da` Noch genug da, `angebot` Angebot/Aktion, `gruppe` Gruppe/Veranstaltung, `haltbarkeit` Qualität/Haltbarkeit, `sonstiges` Sonstiges), `notiz` (text) | edit `[]` (only `leitung` corrects lines by hand; the plugin writes them) |

App roles: view `[kueche, rezeption]`, edit `[kueche]` (`leitung` always).

Views: `bestellvorschlag` *Bestellvorschlag*, handler
`inventur:bestellvorschlag`. Demo hook `inventur:seed_demo`. Both in
`src/kurort_app/apps/plugins/inventur.py`; the template in
`src/kurort_app/templates/apps/plugins/inventur/bestellvorschlag.html`.

Reports: `bestellungen` *Bestellungen* (sections `bestellungen`: bestellt_am,
lieferant, lieferung_am, status, fruehstuecke; `positionen`: bestellung,
artikel, bestand, vorschlag, bestellt, grund) and `bestaende` *Bestände*
(`bestaende`: gezaehlt_am, artikel, menge, mitarbeiter).

## The suggestion rule

Pure functions in `plugins/inventur.py`, unit-tested without HTTP:

- **Expected breakfasts** for the period `[lieferung_am, naechste_lieferung)`:
  for each day *d* in it, the number of guests (rows in
  `reservation_guests`) of every reservation with `arrival < d <= departure`
  (they slept there the night before) and a status other than `cancelled`
  and `no_show`; summed over the days.
- **Stock** of an article: the count entered on the page, else the latest
  `bestaende` record by `gezaehlt_am`, else 0 with the flag *Bestand
  unbekannt*.
- **Need:** with `pro_fruehstueck` set: `pro_fruehstueck × breakfasts +
  mindestbestand` (empty minimum = 0). Without it: `zielbestand`, else
  `mindestbestand`; with neither, no suggestion and the flag *Kein
  Zielbestand*.
- **Suggestion:** `need − stock`; 0 if that is ≤ 0; otherwise rounded **up**
  to a multiple of `packungsgroesse` (`Decimal`, `ROUND_CEILING`).
- **Flags:** *unter Mindestbestand* when stock < `mindestbestand`.
- **Value:** `bestellt × preis` summed over lines with a price; lines without
  a price are counted and named ("3 Artikel ohne Preis").

## Screens and routes

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/apps/inventur/ansicht/bestellvorschlag?lieferant=&lieferung_am=&naechste_lieferung=` | view | The suggestion for one supplier |
| POST | same path, `aktion=berechnen` | view | Recompute with the entered counts (nothing saved) |
| POST | same path, `aktion=speichern` | edit on `bestellungen` | Save counts, order and lines |

Everything else (lists, forms, detail, reports, CSV) is F3's.

**The page, top to bottom:**

1. Supplier select (default: the first supplier by name that has active
   articles), *Lieferung am* (default business date + 1), *Nächste
   Lieferung* (default *Lieferung am* + 3), and one line: "Erwartete
   Frühstücke 15.10.–17.10.: 128 (aus den Reservierungen)".
2. One row per active article of that supplier, sorted by category, then
   name: name and unit; *zuletzt gezählt* (value and date, or *Bestand
   unbekannt*); input *Bestand jetzt* (empty, the last count as
   placeholder); *Vorschlag* with its flags; input *Bestellen* (prefilled
   with the suggestion); select *Grund* (optional). Storage place and the
   rule used ("1,0 pro Frühstück + 60 Mindestbestand" / "Zielbestand 300")
   sit behind a small disclosure per row.
3. Under the table: "Summe ca. 412,50 €", the button *Vorschlag
   aktualisieren* (`aktion=berechnen`: recompute with the entered counts and
   set *Bestellen* to the new suggestions) and, for users with edit rights,
   *Bestellung speichern*.
4. *Letzte Bestellungen* of this supplier (5): date, suggested value,
   ordered value, number of lines where ordered ≠ suggested; each links to
   the order's detail page.

At 390 px each row is a card: name, last count, the two inputs side by side
(44 px high, `inputmode="decimal"`), suggestion, reason; the sum and buttons
stick to the bottom of the card list.

## Rules

- **Saving** (`aktion=speichern`) in one transaction through F3's
  `AppContext.create`: a `bestaende` record for every row with an entered
  count; one `bestellungen` record (supplier, `bestellt_am` = business date,
  both delivery dates, `fruehstuecke` = the forecast shown, status
  `bestellt`, current user); a `positionen` line for every row where the
  suggestion or the ordered amount is > 0 (with the stock used, the
  suggestion, the ordered amount, the reason). Then redirect to the order's
  detail page with "Bestellung bei Großmarkt Main-Kinzig gespeichert – 14
  Positionen, ca. 412,50 €." The lines appear there under *Verknüpfte
  Einträge*.
- **Validation:** counts and ordered amounts are numbers ≥ 0 (German comma
  accepted); *Nächste Lieferung* must be after *Lieferung am*; errors
  re-render the page with 422, German messages next to the inputs and all
  entered values kept. Nothing is saved on an error.
- *Grund* is optional, even when ordered ≠ suggested (capture must stay
  quick).
- A user without edit rights on `bestellungen` sees no save button and gets
  403 on `aktion=speichern`; `aktion=berechnen` is allowed (it saves
  nothing).
- No inventory-specific Python outside `plugins/inventur.py` and its
  template. Audit comes from F3's store.

## Demo data

`inventur:seed_demo(session, anchor)`, deterministic, relative to anchor A.

Suppliers: *Großmarkt Main-Kinzig* (Telefon, Mo und Do), *Bäckerei am
Kurpark* (Telefon, täglich), *Hofmolkerei Spessart* (E-Mail, Di und Fr),
*Obst & Gemüse Gelnhausen* (Telefon, Mo und Do). All names are fictional.

Articles (unit, supplier, min, target, pack, per breakfast, price €):

| Article | Unit | Supplier | Min | Target | Pack | Per bf. | Price |
|---|---|---|---|---|---|---|---|
| Eier | Stück | Großmarkt | 60 | – | 30 | 1,0 | 0,28 |
| Gouda in Scheiben | kg | Großmarkt | 1 | – | 0,5 | 0,03 | 9,90 |
| Kochschinken in Scheiben | kg | Großmarkt | 0,5 | – | 0,5 | 0,02 | 14,50 |
| Salami in Scheiben | kg | Großmarkt | 0,5 | – | 0,5 | 0,015 | 16,90 |
| Konfitüre Portionen | Portion | Großmarkt | 100 | 300 | 100 | – | 0,12 |
| Honig Portionen | Portion | Großmarkt | 50 | 200 | 100 | – | 0,14 |
| Nuss-Nougat-Creme Portionen | Portion | Großmarkt | 50 | 200 | 120 | – | 0,18 |
| Müsli | kg | Großmarkt | 2 | – | 1 | 0,03 | 5,40 |
| Cornflakes | kg | Großmarkt | 1 | 3 | 0,75 | – | 4,20 |
| Orangensaft | l | Großmarkt | 6 | – | 6 | 0,15 | 1,60 |
| Apfelsaft | l | Großmarkt | 6 | – | 6 | 0,08 | 1,20 |
| Kaffeebohnen | kg | Großmarkt | 2 | 8 | 1 | – | 14,80 |
| Tee sortiert (100 Beutel) | Packung | Großmarkt | 1 | 4 | 1 | – | 6,50 |
| Mineralwasser (12 × 0,75 l) | Kiste | Großmarkt | 3 | 10 | 1 | – | 5,90 |
| Vollmilch | l | Molkerei | 6 | – | 6 | 0,12 | 1,15 |
| Butter Portionen | Portion | Molkerei | 100 | – | 100 | 1,5 | 0,09 |
| Naturjoghurt 500 g | Stück | Molkerei | 4 | – | 6 | 0,05 | 0,89 |
| Fruchtjoghurt | Stück | Molkerei | 12 | – | 12 | 0,25 | 0,45 |
| Sahne 200 ml | Stück | Molkerei | 5 | 10 | 10 | – | 0,99 |
| Brötchen | Stück | Bäckerei | 0 | – | 10 | 1,8 | 0,38 |
| Croissants | Stück | Bäckerei | 0 | – | 10 | 0,4 | 0,65 |
| Vollkornbrot | Stück | Bäckerei | 0 | – | 1 | 0,06 | 3,90 |
| Äpfel | kg | Obst & Gemüse | 1 | – | 1 | 0,06 | 2,40 |
| Bananen | kg | Obst & Gemüse | 1 | – | 1 | 0,05 | 1,80 |
| Tomaten | kg | Obst & Gemüse | 0,5 | – | 1 | 0,04 | 3,20 |
| Gurken | Stück | Obst & Gemüse | 2 | – | 1 | 0,05 | 0,79 |

Categories: drinks (juices, coffee, tea, water) `getraenke`, Sahne `kueche`,
the rest `fruehstueck`.

History from A−28 to A−1: for Großmarkt and Obst & Gemüse an order every
Monday and Thursday, for the Molkerei every Tuesday and Friday, for the
Bäckerei every day; each with counts for all its articles just before, the
forecast computed from the seeded reservations, and lines where about one in
five ordered amounts differs from the suggestion (mostly lower, with
*Noch genug da*; a few higher with *Gruppe/Veranstaltung*). Past orders have
status `geliefert`. Counts for every article exist within the last three days
before A, so the page shows real numbers on the business date.

## Acceptance criteria

1. **AC-1** `kurort-app apps validate` passes for `inventur.yaml`; after
   `seed_demo_data(reset=True)` the app is installed with 4 suppliers, 26
   articles, at least 16 orders with lines, and a count for every article
   dated within three days before the business date.
2. **AC-2** The suggestion function covers: rate-based need, target-based
   need, no target (no suggestion, flag), rounding up to a pack of 0,5 kg,
   stock ≥ need → 0, unknown stock (0 + flag), *unter Mindestbestand*.
3. **AC-3** The breakfast forecast counts guests on day *d* for
   `arrival < d <= departure`, excludes `cancelled` and `no_show`, and sums
   over `[lieferung_am, naechste_lieferung)` (fixture reservations with known
   answers).
4. **AC-4** GET for a supplier on the business date lists exactly its active
   articles with last count, suggestion and the breakfast line; an inactive
   article and other suppliers' articles are absent.
5. **AC-5** `aktion=berechnen` with entered counts returns the page with new
   suggestions and *Bestellen* set to them, and saves nothing; a negative or
   non-numeric input, or *Nächste Lieferung* not after *Lieferung am*, gives
   422 with German messages and the entered values kept.
6. **AC-6** `aktion=speichern` creates the counts, one order with the
   forecast and status `bestellt`, and lines with stock, suggestion, ordered
   amount and reason; it redirects to the order's detail page with the
   notice; the lines show under *Verknüpfte Einträge*; each record has its
   `app_record.created` audit event.
7. **AC-7** The sum is `Σ bestellt × preis` over priced lines and the page
   names the number of articles without a price.
8. **AC-8** *Letzte Bestellungen* shows the supplier's last five orders with
   suggested and ordered value.
9. **AC-9** With login on: `rezeption` sees the page without the save button
   and gets 403 on `aktion=speichern`; `kueche` and `leitung` can save; a
   `kueche` user's sidebar shows *Inventur & Bestellung*.
10. **AC-10** The CSV export of `positionen` contains the columns
    *Bestand*, *Vorschlag*, *Bestellt* and *Grund für Abweichung*; the
    *Bestellungen* PDF for the current month answers 200 with
    `application/pdf`.
11. **AC-11** At 390 px the suggestion page shows cards, inputs at least
    44 px high and no horizontal scrolling (screenshot).

## Tests

`tests/app/test_app_inventur.py`: AC-2 and AC-3 as unit tests of the pure
functions; AC-1, AC-4 to AC-8 and AC-10 over HTTP on the seeded database;
AC-9 with the `idp` and `oidc_client` fixtures and `login()` from
`tests/app/auth_helpers.py`.

## Files

New: `src/kurort_app/apps/definitions/inventur.yaml`,
`src/kurort_app/apps/plugins/inventur.py`,
`src/kurort_app/templates/apps/plugins/inventur/bestellvorschlag.html`,
`tests/app/test_app_inventur.py`. If F7 is not merged yet when you start:
the `kueche` role changes F7 describes (`auth.py`, start page, demo realm),
and the integrator drops the duplicate when merging.

## Decided defaults

- Delivery period default: tomorrow to three days later (two orders a week).
- Safety stock = the article's minimum; no extra percentage.
- Counting is optional on the page: without an entered count the last one
  is used and shown with its date.
- Reception may look at stock and suggestions but not order.
- The kitchen user's start page stays `/apps/haccp` (F7); Inventur is one
  click away in the sidebar.
