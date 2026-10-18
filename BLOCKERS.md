# F6: Seminar room booking — Gate-Blocker

## Was ist blockiert?

Der vollständige Gate-Lauf aus `AGENTS.md` ist nicht grün. Der App-Gate ist grün
(**231 passed, 1 warning**), ebenso Ruff Lint und Format (**45 files already formatted**).
Der Full-Gate endet mit **1 failed, 282 passed, 2 deselected, 1 warning** (Exit 1):

`tests/test_demo.py::test_ac11_demo_synthetic_bad_orb_month_produces_reproducible_csv`

## Warum?

Das ist ein unveränderter Fehler auf dem ursprünglichen `main` (`6de94f4`), nicht F6:
Die Regulatory-Library erzeugt CSV mit CRLF, die Golden-Datei enthält LF.
Erster Unterschied an Byte 179 (`\r` statt `\n`).

- Fixture: 10.589 Bytes, SHA-256 `457968e2c250c349850e527408a61e7c9abe38cfab84b79816849e193b34c956`
- Ausgabe: 10.743 Bytes, SHA-256 `fd06ed84c0b1318ba6580600269f7884727511bd2f568d0722e2d51fd7ac16ee`

## Was wurde versucht?

1. Den exakten Full-Gate mit `KURORT_TEST_REQUIRE_DB=1` und nur den beiden in
   `AGENTS.md` vorgegebenen Deselektionen ausgeführt (Exit 1).
2. `git archive main` in ein frisches temporäres Verzeichnis entpackt und den
   betroffenen Test dort ausgeführt: identischer Fehler und Hashes (Exit 1).
3. Mit `git diff --quiet main -- src/kurort_engine tests/test_demo.py
   tests/fixtures/expected_synthetic_bad_orb.csv` bestätigt, dass diese Dateien
   durch F6 unverändert sind (Exit 0).
4. Zusätzlich den vollständigen Lauf mit `--maxfail=0` gestartet, damit weitere
   Fehler nicht durch das projektweite `-x` verdeckt werden. Ergebnis im PR.

## Was stattdessen erledigt wurde

F6 vollständig umgesetzt und durch 36 neue Tests (alle 12 ACs), den App-Gate,
Migrations-Roundtrip, Ruff und Browser-Prüfungen bei 1280/390 px verifiziert.
Demo mit eingebettetem PostgreSQL migriert und zweimal mit `seed --reset` erzeugt:
ein Seminarraum, fünf Buchungen, genau eine mit Reservierung verknüpft.
14 Screenshots liegen außerhalb des Repositories unter `output/screenshots/f6-*.png`.

Die Library, ihr Test und die Golden-Datei wurden nicht geändert; kein Test wurde
übersprungen oder abgeschwächt. Für vier grüne Gates ist ein separat autorisierter
Library-/Fixture-Fix nötig. Gemäß Roadmap-Regel 4 wird der PR dennoch geöffnet.
