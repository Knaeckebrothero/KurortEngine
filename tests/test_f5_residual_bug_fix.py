"""f5_residual_bug_fix — regression tests for the iter-17 Product-QA F5 bugs.

Spec contract: `spec/f5_residual_bug_fix/spec.yaml` (PROTECTED AC block at
SHA-256 `92ef2918d7eb7f09aa482033a2fec66db989afa734a9111e8e35d3d74112e6c3`).
Each test function below maps 1:1 to a `test_oracle` entry in the locked
spec.yaml. The test_oracle paths are:

  - AC-A → `test_meldeschein_handler_accepts_english_keys`
            (Gap A: `_handle_meldeschein_checkin` must accept the standard
             English-keyed intake form and normalise it to the German BMG §30
             MeldescheinForm schema; exit 0 + stdout `Meldeschein emitted:`.)

  - AC-B → `test_kurtaxe_handler_uses_calculator_pipeline`
            (Gap B: `_handle_kurtaxe_charge` must call
             `calculate_kurtaxe_for_reservation` and print the resulting
             Decimal EUR alongside the reservation_id; the printed amount
             must NOT equal a payload-echoed `amount_eur` field.)

  - AC-C → `test_remittance_handler_emits_real_data_rows`
            (Gap B: `_handle_remittance_generate` must pass the JSON-stdin
             reservation list to `generate_monthly_remittance_csv`; the
             resulting CSV must contain the 12-column header followed by
             at least one data row whose `subtotal_eur` column equals
             `rate_per_day × day_count` for the first paying guest.)

This is the RED phase. Each test must FAIL with `AssertionError` (NOT
`ImportError` / `SyntaxError` / `CollectionError` / `0 collected`) because the
Gap A and Gap B bug fixes have NOT yet shipped. The subprocess+JSON-stdin test
boundary is the proven convention from `tests/test_f5_receptionist_subcommands.py`
(per pinned memory rule #1): the subprocess call IS the unit-under-test
boundary, so no mocking of `kurort_engine` or its submodules occurs.

Forbidden patterns enforced (per pinned memory rule #1 + iter-8/12/15/17
precedent):
  * NO `pytest.skip` / `@pytest.mark.skip` / `@pytest.mark.xfail` — these
    tests must FAIL honestly (the bugs are present, not skipped).
  * NO mocking of `kurort_engine` or its submodules — subprocess invokes
    the actual module; the test boundary IS the subprocess call.
  * NO `assert True` or tautological assertions — every assert compares
    two distinguishable expressions or one expression to a literal.
  * NO `f(x) == f(x)` mirror tests.

Phase 3 (green) will fix the three handler bodies in
`repo/src/kurort_engine/__init__.py` to make these tests pass.
"""
from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Path + env constants — matches `repo/tests/test_f5_receptionist_subcommands.py`
# ---------------------------------------------------------------------------

_REPO_ROOT: Path = Path(__file__).resolve().parents[1]
_TEST_ENV_OVERRIDES: dict[str, str] = {"PYTHONPATH": "src"}


def _run_kurort_engine(
    args: tuple[str, ...],
    *,
    stdin_payload: str | None = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess:
    """Run ``python -m kurort_engine <args>`` via subprocess with the F5 test
    fixture discipline. Returns the `CompletedProcess` directly so each test
    can assert against `returncode`, `stdout`, `stderr`, and any
    `output_file` written under `--output-file` / `--output-dir`.

    Per pinned memory rule #1 + iter-8/12/15/17 precedent: do NOT mock the
    unit under test. The subprocess call IS the unit-under-test boundary.
    """
    cmd = [sys.executable, "-m", "kurort_engine", *args]
    return subprocess.run(
        cmd,
        cwd=str(_REPO_ROOT),
        env={**os.environ, **_TEST_ENV_OVERRIDES},
        input=stdin_payload,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# AC-A — Gap A fix (English-key Meldeschein payload acceptance)
# test_oracle: tests/test_f5_residual_bug_fix.py::test_meldeschein_handler_accepts_english_keys
# ---------------------------------------------------------------------------


def test_meldeschein_handler_accepts_english_keys(tmp_path) -> None:
    """AC-A spec test_oracle: `meldeschein check-in` accepts the standard
    English-keyed intake form and exits 0 with stdout containing the
    `Meldeschein emitted:` marker.

    The AC-A EARS contract (per `spec.yaml:55-79`):
      "When the operator submits a JSON-stdin payload to the
       `meldeschein check-in` subcommand that uses the standard
       English-keyed intake form (last_name, first_name, date_of_birth,
       nationality, address, arrival_date, departure_date, optional
       passport_number), the handler shall normalise the payload to a
       MeldescheinForm instance whose German BMG §30 field names
       (familienname, vorname, geburtsdatum, staatsangehoerigkeit,
       anschrift, anreisedatum, abreisedatum, ausweis_seriennummer) are
       populated with the corresponding English-keyed values; `render(form)`
       shall then be called and the handler shall exit 0 with stdout
       containing the marker `Meldeschein emitted:`."

    RED-phase expectation: the SHIPPED `_handle_meldeschein_checkin` reads
    `payload["familienname"]`, `payload["vorname"]`, etc. directly (the German
    BMG §30 keys). The English-keyed payload below uses `last_name`,
    `first_name`, `date_of_birth`, etc. — so the handler raises `KeyError`
    on the first key it tries, which propagates as a non-zero exit code
    and a `KeyError: 'familienname'` traceback on stderr. The test asserts
    that the handler ran cleanly: exit 0 + stdout contains `Meldeschein emitted:`.
    In RED phase both assertions fail with AssertionError.
    """
    english_payload = {
        "last_name": "Mustermann",
        "first_name": "Erika",
        "date_of_birth": "1985-03-12",
        "nationality": "DE",
        "address": "Kurstrasse 1, 63619 Bad Orb",
        "arrival_date": "2026-06-01",
        "departure_date": "2026-06-08",
        "passport_number": "C01X00T47",
    }
    output_pdf = tmp_path / "meldeschein_en.pdf"
    completed = _run_kurort_engine(
        ("meldeschein", "check-in", "--output-file", str(output_pdf)),
        stdin_payload=json.dumps(english_payload),
    )

    # (a) Exit code must be 0.
    assert completed.returncode == 0, (
        f"AC-A: `python -m kurort_engine meldeschein check-in` with the "
        f"English-keyed intake form must exit 0 after normalising the "
        f"payload to the German BMG §30 MeldescheinForm schema. Got "
        f"returncode={completed.returncode}. Subprocess stderr:\n"
        f"{completed.stderr}"
    )

    # (b) stdout must contain the `Meldeschein emitted:` marker.
    assert "Meldeschein emitted:" in completed.stdout, (
        f"AC-A: stdout must contain the `Meldeschein emitted:` marker so "
        f"the operator sees a one-line confirmation of the emitted PDF. "
        f"Got stdout:\n{completed.stdout}"
    )


# ---------------------------------------------------------------------------
# AC-B — Gap B / Kurtaxe fix (calculator pipeline)
# test_oracle: tests/test_f5_residual_bug_fix.py::test_kurtaxe_handler_uses_calculator_pipeline
# ---------------------------------------------------------------------------


def test_kurtaxe_handler_uses_calculator_pipeline() -> None:
    """AC-B spec test_oracle: `kurtaxe charge` calls the SHIPPED calculator
    and prints the Decimal EUR amount alongside the reservation_id.

    The AC-B EARS contract (per `spec.yaml:84-109`):
      "When the operator submits a JSON-stdin payload to the
       `kurtaxe charge` subcommand that carries a reservation_id and the
       SHIPPED Reservation shape (arrival, departure, guests), the handler
       shall call
       `kurort_engine.calculator.calculate_kurtaxe_for_reservation` with
       the Reservation and the Hessen Bad Orb Satzung loaded via
       `kurort_engine.load_profile("hessen", "bad_orb")`, and shall print
       the resulting Decimal formatted as EUR with two decimal places
       alongside the reservation_id; the printed amount shall NOT equal
       an `amount_eur` field echoed from the payload."

    RED-phase expectation: the SHIPPED `_handle_kurtaxe_charge` echoes the
    payload's `amount_eur` field directly (`payload.get("amount_eur", 0.0)`).
    With `amount_eur: 0.01` (the decoy) and a 3-night adult stay at the Bad
    Orb Hauptsaison rate, the printed amount is "0.01 EUR", not the real
    calculator output. The test asserts:
      - exit 0;
      - stdout mentions the reservation_id `R-W1-001`;
      - stdout mentions `Kurtaxe charged:`;
      - the printed amount does NOT equal "0.01" (the decoy echoed by the
        stub handler).

    All three numerical/content assertions fail with AssertionError in
    RED phase because the stub echoes the decoy.
    """
    kurtaxe_payload = {
        "reservation_id": "R-W1-001",
        "arrival": "2026-06-01",
        "departure": "2026-06-04",  # 3 nights
        "guests": [
            {
                "name": "Erika Mustermann",
                "birth_date": "1985-03-12",
                "nationality": "DE",
            }
        ],
        # DECOY: operator-supplied decoy to prove the stub echoes it
        # rather than computing from the Satzung.
        "amount_eur": 0.01,
    }
    completed = _run_kurort_engine(
        ("kurtaxe", "charge"),
        stdin_payload=json.dumps(kurtaxe_payload),
    )

    # (a) Exit code must be 0.
    assert completed.returncode == 0, (
        f"AC-B: `python -m kurort_engine kurtaxe charge` with a valid "
        f"Reservation-shaped payload must exit 0. Got returncode="
        f"{completed.returncode}. Subprocess stderr:\n{completed.stderr}"
    )

    # (b) stdout must mention the reservation_id so the operator can match
    # the charge to a booking.
    assert "R-W1-001" in completed.stdout, (
        f"AC-B: stdout must mention the reservation_id 'R-W1-001' from "
        f"the payload so the operator can match the charge to a booking. "
        f"Got stdout:\n{completed.stdout}"
    )

    # (c) stdout must mention the `Kurtaxe charged:` marker.
    assert "Kurtaxe charged:" in completed.stdout, (
        f"AC-B: stdout must mention 'Kurtaxe charged:' so the operator "
        f"sees the per-reservation ledger summary. Got stdout:\n"
        f"{completed.stdout}"
    )

    # (d) The printed amount must NOT equal the decoy 0.01 EUR. The stub
    # echoes `payload.get("amount_eur", 0.0)` so the printed amount is
    # "0.01 EUR". After the fix, the printed amount is
    # `calculate_kurtaxe_for_reservation` × day_count, which for a 3-night
    # adult Bad Orb Hauptsaison stay is materially larger than 0.01.
    # We pin the negative-assertion (no decoy) so the test fails honestly
    # in RED phase: the stub prints "0.01", the assertion rejects it.
    assert "0.01 EUR" not in completed.stdout, (
        f"AC-B: the printed Kurtaxe amount must NOT equal the decoy "
        f"`amount_eur: 0.01` payload field. The current stub echoes the "
        f"operator-supplied value instead of calling "
        f"`calculate_kurtaxe_for_reservation` — this is the Gap B bug. "
        f"Got stdout:\n{completed.stdout}"
    )


# ---------------------------------------------------------------------------
# AC-C — Gap B / remittance fix (real CSV data rows)
# test_oracle: tests/test_f5_residual_bug_fix.py::test_remittance_handler_emits_real_data_rows
# ---------------------------------------------------------------------------


def test_remittance_handler_emits_real_data_rows(tmp_path) -> None:
    """AC-C spec test_oracle: `remittance generate` writes a CSV with the
    12-column header AND at least one data row whose `subtotal_eur` column
    equals `rate_per_day × day_count` for the first paying guest.

    The AC-C EARS contract (per `spec.yaml:114-139`):
      "When the operator invokes the `remittance generate` subcommand with
       `--year`, `--month`, and a JSON-stdin payload that carries a
       non-empty list of reservations whose `arrival` falls inside the
       (year, month) window, the handler shall pass that list to
       `kurort_engine.reporting.generate_monthly_remittance_csv`, and the
       resulting CSV shall contain the 12-column header row followed by at
       least one data row whose `subtotal_eur` column equals the
       `rate_band × day_count` for the first paying guest."

    RED-phase expectation: the SHIPPED `_handle_remittance_generate` calls
    `generate_monthly_remittance_csv(year, month, [])` with an EMPTY
    reservations list — regardless of what the JSON-stdin payload carries.
    The CSV is therefore header-only (1 line). The test asserts:
      - exit 0;
      - the output CSV file exists and is non-empty;
      - the CSV starts with the canonical 12-column Hessen KAG header;
      - the CSV has at least one data row whose `subtotal_eur` column
        equals the expected `rate_per_day × day_count` for the first paying
        guest (computed via the SHIPPED `calculate_kurtaxe_for_reservation`
        on the same Reservation + Satzung, so the assertion is independent
        of the handler implementation — it pins the contract, not the
        internal arithmetic).

    The first content assertion (CSV has ≥1 data row with correct subtotal)
    fails with AssertionError in RED phase because the stub always emits
    a header-only CSV.
    """
    # Build an in-window Reservation (arrival 2026-06-02, 3-night stay).
    kurtaxe_payload = {
        "reservation_id": "R-W1-001",
        "arrival": "2026-06-02",
        "departure": "2026-06-05",  # day_count = 3
        "guests": [
            {
                "name": "Erika Mustermann",
                "birth_date": "1985-03-12",
                "nationality": "DE",
            }
        ],
    }
    output_csv = tmp_path / "remit.csv"
    completed = _run_kurort_engine(
        (
            "remittance",
            "generate",
            "--year",
            "2026",
            "--month",
            "6",
            "--output-file",
            str(output_csv),
        ),
        stdin_payload=json.dumps(kurtaxe_payload),
    )

    # (a) Exit code must be 0.
    assert completed.returncode == 0, (
        f"AC-C: `python -m kurort_engine remittance generate --year 2026 "
        f"--month 6 --output-file {output_csv}` must exit 0 to be "
        f"operator-reachable. Got returncode={completed.returncode}. "
        f"Subprocess stderr:\n{completed.stderr}"
    )

    # (b) The output CSV must exist and be non-empty.
    assert output_csv.exists(), (
        f"AC-C: --output-file {output_csv} must exist after the "
        f"`remittance generate` invocation (WROTE the Hessen KAG CSV). "
        f"Subprocess stdout:\n{completed.stdout}"
    )
    csv_text = output_csv.read_text(encoding="utf-8")
    assert len(csv_text) > 0, (
        f"AC-C: --output-file {output_csv} must be non-empty after the "
        f"`remittance generate` invocation. Got 0 bytes."
    )

    # (c) The CSV must start with the canonical Hessen KAG 12-column header
    # per `kurort_engine/reporting.py:42-55`.
    expected_header_prefix = "Reservation-ID,anonymised guest name"
    assert csv_text.startswith(expected_header_prefix), (
        f"AC-C: remittance CSV must start with the canonical Hessen KAG "
        f"12-column header prefix '{expected_header_prefix}' "
        f"(per `kurort_engine/reporting.py:42-55`). Got first 80 chars: "
        f"{csv_text[:80]!r}"
    )

    # (d) The CSV must contain at least one data row whose `subtotal_eur`
    # column equals the calculator's rate × day_count for the first paying
    # guest. We compute the expected subtotal independently using the SHIPPED
    # calculator on the same Reservation + Hessen Bad Orb Satzung, so this
    # assertion is independent of the handler internals — it pins the
    # public contract, not the implementation.
    from kurort_engine.calculator import (
        Guest,
        Reservation,
        calculate_kurtaxe_for_reservation,
    )
    from datetime import date
    from kurort_engine import load_profile

    satzung = load_profile("hessen", "bad_orb")
    reservation_obj = Reservation(
        reservation_id="R-W1-001",
        arrival=date(2026, 6, 2),
        departure=date(2026, 6, 5),  # 3 nights
        guests=(
            Guest(
                name="Erika Mustermann",
                birth_date=date(1985, 3, 12),
                nationality="DE",
            ),
        ),
    )
    expected_total = calculate_kurtaxe_for_reservation(reservation_obj, satzung)
    # For a single paying guest, the per-row subtotal equals the
    # reservation total: `rate_per_day × day_count` = expected_total.
    expected_subtotal_str = f"{expected_total:.2f}"

    # Parse the CSV (header row + data rows).
    reader = csv.reader(io.StringIO(csv_text))
    rows = [row for row in reader if row]
    assert len(rows) >= 2, (
        f"AC-C: remittance CSV must contain the 12-column header PLUS at "
        f"least one data row. Got {len(rows)} non-empty row(s) total "
        f"(expected ≥ 2 = header + ≥1 data row). CSV content:\n{csv_text}"
    )
    # The `subtotal_eur` column is column index 8 (per
    # `kurort_engine/reporting.py:42-55`: ... "subtotal_eur", ...).
    subtotal_column_index = 8
    data_rows = rows[1:]
    subtotals = [row[subtotal_column_index] for row in data_rows]
    assert expected_subtotal_str in subtotals, (
        f"AC-C: at least one CSV data row must have "
        f"`subtotal_eur == {expected_subtotal_str}` "
        f"(rate_per_day × day_count for the first paying guest). "
        f"Got subtotals: {subtotals}. CSV content:\n{csv_text}"
    )