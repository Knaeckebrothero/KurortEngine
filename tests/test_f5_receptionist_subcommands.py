"""AC-1..AC-5: F5 receptionist-subcommands Tier-1 (4 of 6) + F6 arrival-bundle closure.

Test_oracle paths recorded in `spec.yaml:88-152` and `spec_lock.md:53-119`.
Each test maps 1:1 to the 5 EARS ACs in iter-16 spec for F5 receptionist-subcommands
Tier-1 (4 of 6 subcommands + arrival-bundle orchestrator closing F6).

This is the RED phase. Each test MUST fail with `AssertionError` (NOT
`ImportError` / `SyntaxError` / `CollectionError` / `0 collected`) because the
implementation has not yet shipped. Per pinned memory rule #1:

  * `python -m kurort_engine meldeschein check-in` (AC-1) currently fails
    with `argparse: invalid choice: 'meldeschein'` — exit code 2, caught
    by the `returncode == 0` assertion and re-raised as AssertionError.
  * `python -m kurort_engine kurtaxe charge` (AC-2) — same as above.
  * `python -m kurort_engine remittance generate` (AC-3) — same as above.
  * `python -m kurort_engine arrival bundle` (AC-4) — same as above.
  * `python -m kurort_engine --help` (AC-1..AC-5) lists only `{demo, version}`
    per Phase 1 git evidence — caught by the substring-match assertions.

Forbidden patterns enforced (per pinned memory rule #1 + per `iter-8` + `iter-12`
+ `iter-15` precedent):
  * NO `pytest.skip` / `@pytest.mark.skip` for AC-1..AC-4 (these must FAIL honestly).
  * NO mocking of `kurort_engine` or its submodules — subprocess invokes
    the actual module; the test boundary IS the subprocess call.
  * NO `assert True` or tautological assertions — every assert compares
    two distinguishable expressions or one expression to a literal.
  * NO `f(x) == f(x)` mirror tests.

This file is in the RED phase of the TDD cycle. Phase 3 GREEN will implement
the 4 subparsers in `repo/src/kurort_engine/__main__.py` + the 4 helpers in
`repo/src/kurort_engine/cli/` + the `build_arrival_bundle` orchestrator in
`repo/src/kurort_engine/guest_arrival.py`. None of those src/ files are
modified in this RED phase.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Path + env constants — matches `repo/tests/test_repo_layout.py:_run_module`
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

    Per pinned memory rule #1 + iter-8 / iter-15 precedent: do NOT mock the
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
# AC-1 — `python -m kurort_engine meldeschein check-in` writes a non-empty PDF
# ---------------------------------------------------------------------------


def test_ac1_meldeschein_checkin_emits_pdf() -> None:
    """AC-1 spec test_oracle: `meldeschein check-in` exits 0 and writes a
    Meldeschein PDF (or non-empty stdout marker in RED phase).

    The AC-1 EARS contract (per `spec.yaml:88-98`):
      "When an operator runs `python -m kurort_engine meldeschein check-in`
       with a valid JSON-stdin payload matching
       `repo/schemas/meldeschein.schema.json`, the system shall construct a
       `kurort_engine.MeldescheinForm` from the payload, call
       `kurort_engine.meldeschein.render(form)`, and write the resulting
       PDF bytes to `--output-file <path>` (or stdout if not given); on
       success, exit 0 and print `Meldeschein emitted: <bytes_written>
       bytes to <path>`."

    Sub-conditions (in RED phase, this must FAIL with AssertionError
    because the `meldeschein` subcommand does NOT exist yet — only
    `version` and `demo` are wired in `__main__.py:62-69`):
      (a) The subprocess exit code is 0.
      (b) The subprocess stdout contains a non-empty Meldeschein marker.

    This test uses the SHIPPED `kurort_engine.meldeschein.MeldescheinForm`
    field schema (per `kurort_engine/meldeschein/__init__.py:86-94`): 7
    mandatory BMG §30 Pflichtangaben + optional `ausweis_seriennummer`.
    """
    valid_meldeschein_payload = {
        "familienname": "Mustermann",
        "vorname": "Erika",
        "geburtsdatum": "1985-03-12",
        "staatsangehoerigkeit": "DE",
        "anschrift": "Kurstrasse 1, 63619 Bad Orb",
        "anreisedatum": "2026-06-01",
        "abreisedatum": "2026-06-08",
        "ausweis_seriennummer": None,
    }
    completed = _run_kurort_engine(
        ("meldeschein", "check-in"),
        stdin_payload=json.dumps(valid_meldeschein_payload),
    )

    # (a) Exit code must be 0.
    assert completed.returncode == 0, (
        f"AC-1: `python -m kurort_engine meldeschein check-in` must exit 0 "
        f"to be operator-reachable. Got returncode={completed.returncode}. "
        f"Subprocess stderr:\n{completed.stderr}"
    )

    # (b) stdout must mention the Meldeschein marker.
    assert "Meldeschein" in completed.stdout, (
        f"AC-1: stdout must mention 'Meldeschein' so the operator sees a "
        f"one-line confirmation of the emitted PDF. Got stdout:\n{completed.stdout}"
    )


# ---------------------------------------------------------------------------
# AC-2 — `python -m kurort_engine kurtaxe charge` emits per-guest ledger
# ---------------------------------------------------------------------------


def test_ac2_kurtaxe_charge_emits_ledger() -> None:
    """AC-2 spec test_oracle: `kurtaxe charge` exits 0 and emits a per-guest
    ledger with Kurtaxe total + reservation_id.

    The AC-2 EARS contract (per `spec.yaml:100-112`):
      "When an operator runs `python -m kurort_engine kurtaxe charge` with
       a valid JSON-stdin payload matching `repo/schemas/kurtaxe.schema.json`
       (containing a Reservation dict, Satzung profile id, and optional
       exemptions dict), the system shall construct a
       `kurort_engine.Reservation` + `kurort_engine.Satzung` from the
       payload, call `kurort_engine.calculate_kurtaxe_for_reservation(...)`,
       and print the resulting `Decimal` total + per-guest ledger to
       stdout; on success, exit 0 and print
       `Kurtaxe charged: <total_eur> for reservation <reservation_id>`."

    Sub-conditions (must FAIL with AssertionError in RED phase because
    `kurtaxe` subcommand does NOT exist yet — argparse rejects with
    `invalid choice: 'kurtaxe'`):
      (a) The subprocess exit code is 0.
      (b) stdout contains `'Kurtaxe charged'` marker.
      (c) stdout contains the reservation_id from the payload.
    """
    valid_kurtaxe_payload = {
        "reservation_id": "R-W1-001",
        "guest_id": "G-001",
        "amount_eur": 42.0,
    }
    completed = _run_kurort_engine(
        ("kurtaxe", "charge"),
        stdin_payload=json.dumps(valid_kurtaxe_payload),
    )

    # (a) Exit code must be 0.
    assert completed.returncode == 0, (
        f"AC-2: `python -m kurort_engine kurtaxe charge` must exit 0 to be "
        f"operator-reachable. Got returncode={completed.returncode}. "
        f"Subprocess stderr:\n{completed.stderr}"
    )

    # (b) stdout must mention the Kurtaxe charged marker.
    assert "Kurtaxe charged" in completed.stdout, (
        f"AC-2: stdout must mention 'Kurtaxe charged' so the operator sees "
        f"the per-guest ledger summary. Got stdout:\n{completed.stdout}"
    )

    # (c) stdout must echo the reservation_id.
    assert "R-W1-001" in completed.stdout, (
        f"AC-2: stdout must mention the reservation_id 'R-W1-001' from the "
        f"payload so the operator can match the charge to a booking. "
        f"Got stdout:\n{completed.stdout}"
    )


# ---------------------------------------------------------------------------
# AC-3 — `python -m kurort_engine remittance generate` writes Hessen KAG CSV
# ---------------------------------------------------------------------------


def test_ac3_remittance_csv_matches_expected(tmp_path) -> None:
    """AC-3 spec test_oracle: `remittance generate` exits 0 and writes a
    Hessen KAG 12-column CSV.

    The AC-3 EARS contract (per `spec.yaml:114-125`):
      "When an operator runs `python -m kurort_engine remittance generate
       --year YYYY --month MM` with `--input-file <reservations.csv>`
       (or JSON-stdin equivalent matching
       `repo/schemas/remittance.schema.json`), the system shall load the
       reservations, call
       `kurort_engine.generate_monthly_remittance_csv(year, month,
       reservations)`, and write the resulting Hessen KAG 12-column CSV
       to `--output-file <path>` (or stdout if not given); on success,
       exit 0 and print `Remittance written: <bytes_written> bytes
       (n_rows=<R>) to <path>`."

    Sub-conditions (must FAIL with AssertionError in RED phase because
    `remittance` subcommand does NOT exist yet):
      (a) The subprocess exit code is 0.
      (b) The CSV file at `--output-file` exists and is non-empty.
      (c) The CSV file starts with the 12-column header row from
          `kurort_engine.reporting.AC4_HEADER_COLUMNS`.

    The expected header is the canonical Hessen KAG 12-column header
    pinned at `kurort_engine/reporting.py:42-55`. We hardcode the
    first column-pair `("Reservation-ID", "anonymised guest name")`
    to keep the assertion narrow + unambiguous.
    """
    output_csv = tmp_path / "remit.csv"
    completed = _run_kurort_engine(
        (
            "remittance",
            "generate",
            "--year",
            "2025",
            "--month",
            "6",
            "--output-file",
            str(output_csv),
        )
    )

    # (a) Exit code must be 0.
    assert completed.returncode == 0, (
        f"AC-3: `python -m kurort_engine remittance generate --year 2025 "
        f"--month 6` must exit 0 to be operator-reachable. Got "
        f"returncode={completed.returncode}. Subprocess stderr:\n{completed.stderr}"
    )

    # (b) The output CSV must exist and be non-empty.
    assert output_csv.exists(), (
        f"AC-3: --output-file {output_csv} must exist after the "
        f"`remittance generate` invocation (WROTE the Hessen KAG CSV). "
        f"Subprocess stdout:\n{completed.stdout}"
    )
    csv_text = output_csv.read_text(encoding="utf-8")
    assert len(csv_text) > 0, (
        f"AC-3: --output-file {output_csv} must be non-empty after the "
        f"`remittance generate` invocation. Got 0 bytes."
    )

    # (c) The CSV must start with the canonical Hessen KAG 12-column header.
    # The first 2 columns are `Reservation-ID` and `anonymised guest name`
    # per `kurort_engine/reporting.py:43-44`; the full 12-column header is
    # pinned at `kurort_engine/reporting.py:42-55`.
    expected_header_prefix = "Reservation-ID,anonymised guest name"
    assert csv_text.startswith(expected_header_prefix), (
        f"AC-3: remittance CSV must start with the canonical Hessen KAG "
        f"12-column header prefix '{expected_header_prefix}' "
        f"(per `kurort_engine/reporting.py:42-55`). Got first 80 chars: "
        f"{csv_text[:80]!r}"
    )


# ---------------------------------------------------------------------------
# AC-4 — `python -m kurort_engine arrival bundle` writes 3 files
# ---------------------------------------------------------------------------


def test_ac4_arrival_bundle_writes_three_files(tmp_path) -> None:
    """AC-4 spec test_oracle: `arrival bundle` exits 0 and writes 3 files.

    The AC-4 EARS contract (per `spec.yaml:127-140`):
      "When an operator runs `python -m kurort_engine arrival bundle
       --reservation R-XXX --output-dir <dir>` with a valid reservation
       id (resolved via a fixture lookup against the SHIPPED
       `kurort_engine.kurpaket_guest_card` registry), the system shall
       invoke the orchestrator
       `kurort_engine.guest_arrival.build_arrival_bundle` which
       produces 3 files in `<dir>`: a Meldeschein PDF
       (`meldeschein_<R>.pdf`), an Apple PKPass
       (`kurkarte_apple_<R>.pkpass`), and a Google Wallet JSON
       (`kurkarte_google_<R>.json`); on success, exit 0 and print
       `Arrival bundle: 3 files written to <dir> for reservation <R>`."

    Sub-conditions (must FAIL with AssertionError in RED phase because
    `arrival` subcommand does NOT exist yet):
      (a) The subprocess exit code is 0.
      (b) The 3 expected files exist in `--output-dir`:
          `meldeschein_R-W1-001.pdf` + `kurkarte_apple_R-W1-001.pkpass`
          + `kurkarte_google_R-W1-001.json`.
    """
    output_dir = tmp_path / "bundle"
    completed = _run_kurrot_engine_args = _run_kurort_engine(
        (
            "arrival",
            "bundle",
            "--reservation",
            "R-W1-001",
            "--output-dir",
            str(output_dir),
        )
    )

    # (a) Exit code must be 0.
    assert completed.returncode == 0, (
        f"AC-4: `python -m kurort_engine arrival bundle --reservation "
        f"R-W1-001 --output-dir {output_dir}` must exit 0 to be "
        f"operator-reachable. Got returncode={completed.returncode}. "
        f"Subprocess stderr:\n{completed.stderr}"
    )

    # (b) The 3 expected files must exist in the output directory.
    expected_files = (
        output_dir / "meldeschein_R-W1-001.pdf",
        output_dir / "kurkarte_apple_R-W1-001.pkpass",
        output_dir / "kurkarte_google_R-W1-001.json",
    )
    missing_files = [str(p) for p in expected_files if not p.exists()]
    assert not missing_files, (
        f"AC-4: `arrival bundle` must write 3 files to {output_dir}: "
        f"meldeschein_R-W1-001.pdf + kurkarte_apple_R-W1-001.pkpass + "
        f"kurkarte_google_R-W1-001.json. Missing: {missing_files}. "
        f"Got directory contents: {sorted(p.name for p in output_dir.iterdir()) if output_dir.exists() else 'DIRECTORY DOES NOT EXIST'}. "
        f"Subprocess stdout:\n{completed.stdout}"
    )


# ---------------------------------------------------------------------------
# AC-5 — `kurort-engine` CLI binary lists 4 new subcommands
# ---------------------------------------------------------------------------


def test_ac5_cli_binary_lists_four_subcommands() -> None:
    """AC-5 spec test_oracle: `kurort-engine --help` lists 4 new subcommands.

    The AC-5 EARS contract (per `spec.yaml:142-152`):
      "The system shall expose a `kurort-engine` CLI binary via the
       `[project.scripts]` entry point already declared in
       `repo/pyproject.toml:30` (`kurort-engine =
       \"kurort_engine.__main__:main\"`) such that `kurort-engine --help`
       prints the same usage text as `python -m kurort_engine --help`
       and lists the 4 new subcommands (`meldeschein`, `kurtaxe`,
       `remittance`, `arrival`) alongside `version` and `demo`; on
       success, exit 0."

    Sub-conditions (must FAIL with AssertionError in RED phase because
    the 4 subcommands are NOT yet wired):
      (a) The `kurort-engine` binary is on PATH (or `python -m kurort_engine --help`
          fallback to verify the entry-point contract).
      (b) The 4 new subcommands each appear in the `--help` output.
    """
    # (a) Resolve the binary. If the `[project.scripts]` install has not
    # been run, fall back to `python -m kurort_engine --help` which is
    # the same code path (the binary just wraps `python -m kurort_engine`).
    binary = shutil.which("kurort-engine")
    if binary is None:
        # Fall back to `python -m kurort_engine --help` — this still
        # exercises the same parser in `__main__.py:_build_parser` and
        # is the documented VC-5 best-effort path per pinned rules
        # §"Known blockers" item 3.
        binary_invocation = [sys.executable, "-m", "kurort_engine", "--help"]
        binary_label = "python -m kurort_engine (binary fallback)"
    else:
        binary_invocation = [binary, "--help"]
        binary_label = f"kurort-engine binary at {binary}"

    completed = subprocess.run(
        binary_invocation,
        cwd=str(_REPO_ROOT),
        env={**os.environ, **_TEST_ENV_OVERRIDES},
        capture_output=True,
        text=True,
        timeout=30,
    )

    # (b) The 4 new subcommands must each appear in the --help output.
    expected_subcommands = ("meldeschein", "kurtaxe", "remittance", "arrival")
    help_text = completed.stdout
    matched_subcommands = [
        sub
        for sub in expected_subcommands
        if sub in help_text
    ]
    assert len(matched_subcommands) == len(expected_subcommands), (
        f"AC-5: `{binary_label} --help` stdout must list all 4 new "
        f"subcommands {list(expected_subcommands)}. Got only "
        f"{matched_subcommands} ({len(matched_subcommands)} of "
        f"{len(expected_subcommands)}). Raw stdout:\n{help_text}"
    )
