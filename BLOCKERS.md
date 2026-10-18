# F1: Gate-Blocker auf unverändertem main

Das App-Gate besteht (201 Tests), ebenso Ruff und Ruff-Format. Das vollständige
AGENTS-Gate mit den zwei vorgegebenen Deselektionen scheitert zusätzlich an:

`tests/test_demo.py::test_ac11_demo_synthetic_bad_orb_month_produces_reproducible_csv`

Die erzeugte CSV hat CRLF-Zeilenenden (10.743 Bytes), die eingecheckte Fixture
`tests/fixtures/expected_synthetic_bad_orb.csv` LF (10.589 Bytes). Erste Abweichung:
Byte 179 (`\r` statt `\n`).

- Fixture SHA-256: `457968e2c250c349850e527408a61e7c9abe38cfab84b79816849e193b34c956`
- Ausgabe SHA-256: `fd06ed84c0b1318ba6580600269f7884727511bd2f568d0722e2d51fd7ac16ee`

## Reproduktion und Abgrenzung

Das unveränderte `main` beim Start (`6de94f4`) wurde in einem separaten,
detached Worktree ausgecheckt. Dort scheitert derselbe Test mit denselben Bytes
und Hashes:

```sh
# Aus dem F1-Checkout; /tmp/kurort-f1-main ist main@6de94f4.
KURORT_TEST_REQUIRE_DB=1 PYTHONPATH=/tmp/kurort-f1-main/src \
  .venv/bin/python -m pytest /tmp/kurort-f1-main/tests/test_demo.py -q
# 1 failed in 0.37s; Exit 1
```

Das exakte Gesamt-Gate auf F1: `1 failed, 252 passed, 2 deselected` (Exit 1;
pytest beendet durch das konfigurierte `-x`). Die Logs außerhalb des Repositorys:
`output/logs/f1-full.log`, `output/logs/f1-main-csv.log`.

Ein ergänzender Lauf mit unveränderten Deselektionen und
`PYTEST_ADDOPTS=--maxfail=0` erfasst die restlichen Tests:
`2 failed, 380 passed, 8 skipped, 2 deselected, 1 warning in 334.42s` (Exit 1;
`output/logs/f1-full-all.log`). Zweiter Fehler:
`tests/test_repo_layout.py::test_ac6_full_pytest_suite_exits_zero`. Dieser
unveränderte Metatest startet intern die komplette Suite **ohne** die beiden
AGENTS-Deselektionen und erbt dadurch die bekannten a11y-/Audit-Fehler sowie
den CSV-Fehler. Die acht bestehenden Skips betreffen optionale Browsertests;
es wurden keine Skips ergänzt. Das App-Gate enthält keine Skips.

Eine Korrektur der Bibliothek oder ihrer Golden-Master-Fixture ist nicht Teil
von F1. `src/kurort_engine/` und der Test bleiben unverändert; es wurde keine
weitere Deselektion, kein Skip und kein Xfail hinzugefügt. Gemäß Aufgabenbrief
wird der PR trotz dieses dokumentierten Blockers zur Prüfung geöffnet. Benötigt
wird eine separat autorisierte Vereinheitlichung der CSV-Zeilenenden.
