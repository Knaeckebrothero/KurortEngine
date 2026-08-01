"""AC-1..AC-3: F5 receptionist-subcommands Tier-2 (rechnung / dsgvo / predicate).

Test_oracle paths recorded in
``repo/spec/f5_receptionist_tier2_rechnung_dsgvo_predicate/spec.yaml:43-52``
and ``repo/spec/f5_receptionist_tier2_rechnung_dsgvo_predicate/spec_lock.md``
PROTECTED AC block. Each test maps 1:1 to the 3 EARS ACs in iter-24 spec for
F5 receptionist-subcommands Tier-2 chain-extension (3 of 3 SHIPPED library
modules wired onto Tier-1 subparser surface).

This is the RED phase. Each test MUST fail with ``AssertionError`` (NOT
``ImportError`` / ``SyntaxError`` / ``CollectionError`` / ``0 collected``)
because the Tier-2 subcommands do not yet exist in
``__main__.py:_build_parser`` (only Tier-1 4-of-6 + avv_kaskade 3-of-3 are
shipped per iter-16 / iter-28). Per pinned memory rule #1 + iter-16 precedent:

  * ``python -m kurort_engine rechnung issue`` (AC-1) currently fails with
    ``argparse: invalid choice: 'rechnung'`` — exit code 2, caught by
    ``returncode == 0`` and re-raised as AssertionError.
  * ``python -m kurort_engine dsgvo cascade`` (AC-2) — same as above.
  * ``python -m kurort_engine predicate file`` (AC-3) — same as above.

Forbidden patterns enforced (per pinned memory rule #1 + iter-16 / iter-12
/ iter-15 precedent):

  * NO ``pytest.skip`` / ``@pytest.mark.skip`` for AC-1..AC-3 (these must
    FAIL honestly).
  * NO mocking of ``kurort_engine`` or its submodules — subprocess invokes
    the actual module; the test boundary IS the subprocess call.
  * NO ``assert True`` or tautological assertions — every assert compares
    two distinguishable expressions or one expression to a literal.
  * NO ``f(x) == f(x)`` mirror tests.

This file is in the RED phase of the TDD cycle. Phase 3 GREEN will implement
the 3 subparsers in ``repo/src/kurort_engine/__main__.py`` + the 3 handlers
in ``repo/src/kurort_engine/__init__.py:parse_subcommand`` dispatcher. No
src/ edits occur in this RED phase.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Path + env constants — matches Tier-1
# ``repo/tests/test_f5_receptionist_subcommands.py:_run_kurort_engine``
# ---------------------------------------------------------------------------

_REPO_ROOT: Path = Path(__file__).resolve().parents[1]
_TEST_ENV_OVERRIDES: dict[str, str] = {"PYTHONPATH": "src"}


def _run_kurort_engine(
    args: tuple[str, ...],
    *,
    stdin_payload: str | None = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess:
    """Run ``python -m kurort_engine <args>`` via subprocess with the F5
    Tier-2 test fixture discipline. Returns the ``CompletedProcess``
    directly so each test can assert against ``returncode``, ``stdout``,
    ``stderr``, and any artifact written under ``--input-file`` /
    ``--output-dir``.

    Per pinned memory rule #1 + iter-16 / iter-15 precedent: do NOT mock the
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
# AC-1 — `python -m kurort_engine rechnung issue` emits GoBD §10 text output
# ---------------------------------------------------------------------------


def test_ac1_rechnung_issue_subcommand_emits_gobd_text() -> None:
    """AC-1 spec test_oracle: ``rechnung issue`` exits 0 and emits a GoBD
    §10 retention-compliant text-only output on stdout.

    The AC-1 EARS contract (per ``spec.yaml:44-46``):
      "When the user invokes `python -m kurort_engine rechnung issue` with
       a valid JSON payload supplied either via stdin or via
       `--input-file <path.json>`, the system shall parse monetary fields
       as `Decimal(string_value)` (no raw float), validate the payload
       schema, and emit a GoBD §10 retention-compliant text-only output on
       stdout; and the system shall exit 0 on success or exit non-zero with
       a structured error message on schema violation."

    Sub-conditions (must FAIL with AssertionError in RED phase because
    ``rechnung`` subcommand does NOT exist yet — argparse rejects with
    ``invalid choice: 'rechnung'``):
      (a) The subprocess exit code is 0.
      (b) The subprocess stdout contains the verbatim §23 SGB V footer
          ``Badekur/Ambulante Vorsorge §23 SGB V`` (GoBD §10 retention
          citation per ``kurort_engine/rechnung.py:43``
          ``AC5_FOOTER_TEXT``).
      (c) The subprocess stdout contains the Kurtaxe Zuschussfähige
          Posten label ``Kurtaxe:`` (per ``rechnung.py:116`` render line).

    The valid payload schema is the minimum-viable Reservation + folios
    shape needed by ``build_badekur_rechnung(reservation, satzung,
    folios)`` (``repo/src/kurort_engine/rechnung.py:78-82``):
      - ``reservation_id: str`` (required by Reservation)
      - ``guest_name: str``, ``guest_birth_date: ISO date``,
        ``guest_nationality: str`` (required by Guest)
      - ``arrival_date: ISO date``, ``departure_date: ISO date`` (required
        by Reservation.arrival/departure)
      - ``uebernachtung: list[str]`` (per-night Decimal-stringified
        amounts; no raw float per AC-1 EARS Decimal discipline)
      - ``verpflegung: list[str]`` (per-night Decimal-stringified amounts)
    """
    valid_rechnung_payload = {
        "reservation_id": "R-W1-100",
        "guest_name": "Mustermann, Erika",
        "guest_birth_date": "1985-03-12",
        "guest_nationality": "DE",
        "arrival_date": "2026-06-01",
        "departure_date": "2026-06-08",
        "uebernachtung": ["65.00", "65.00", "65.00", "65.00", "65.00", "65.00", "65.00"],
        "verpflegung": ["30.00", "30.00", "30.00", "30.00", "30.00", "30.00", "30.00"],
    }
    completed = _run_kurort_engine(
        ("rechnung", "issue"),
        stdin_payload=json.dumps(valid_rechnung_payload),
    )

    # (a) Exit code must be 0.
    assert completed.returncode == 0, (
        f"AC-1: `python -m kurort_engine rechnung issue` must exit 0 to be "
        f"operator-reachable. Got returncode={completed.returncode}. "
        f"Subprocess stderr:\n{completed.stderr}"
    )

    # (b) stdout must contain the verbatim §23 SGB V footer (GoBD §10
    # retention citation). This is the canonical Krankenkasse-grepped
    # substring from `kurort_engine/rechnung.py:43 AC5_FOOTER_TEXT`.
    gobd_footer = "Badekur/Ambulante Vorsorge §23 SGB V"
    assert gobd_footer in completed.stdout, (
        f"AC-1: stdout must contain the GoBD §10 footer "
        f"{gobd_footer!r} (the Krankenkasse reviewer greps for this exact "
        f"substring per `kurort_engine/rechnung.py:43 AC5_FOOTER_TEXT`). "
        f"Got stdout:\n{completed.stdout}"
    )

    # (c) stdout must contain the Kurtaxe Zuschussfähige Posten label.
    # The render line in `rechnung.py:116` is `f"  Kurtaxe:      {_format_eur(...)}"`.
    assert "Kurtaxe:" in completed.stdout, (
        f"AC-1: stdout must contain the `Kurtaxe:` Zuschussfähige Posten "
        f"label (per `rechnung.py:116`). Got stdout:\n{completed.stdout}"
    )


# ---------------------------------------------------------------------------
# AC-2 — `python -m kurort_engine dsgvo cascade` reports in-house actions
# ---------------------------------------------------------------------------


def test_ac2_dsgvo_cascade_subcommand_reports_in_house_actions() -> None:
    """AC-2 spec test_oracle: ``dsgvo cascade --guest-id X`` exits 0 and
    emits a JSON object with the canonical keys ``guest_id``,
    ``actions_planned``, and ``actions_count``.

    The AC-2 EARS contract (per ``spec.yaml:47-49``):
      "If the user invokes `python -m kurort_engine dsgvo cascade` with a
       `guest_id` argument, then the system shall execute the in-house
       retention cascade via
       `kurort_engine.kurgaste_retention.auto_cascade.run_cascade(guest_id)`,
       restrict the cascade to the in-house data inventory (no cross-border
       subprocessor work), and report the planned retention actions to
       stdout as a JSON object with at minimum the keys `guest_id`,
       `actions_planned`, and `actions_count`."

    Sub-conditions (must FAIL with AssertionError in RED phase because
    ``dsgvo`` subcommand does NOT exist yet — argparse rejects with
    ``invalid choice: 'dsgvo'``):
      (a) The subprocess exit code is 0.
      (b) The subprocess stdout is parseable as a JSON object (i.e.
          ``json.loads(stdout)`` does not raise).
      (c) The parsed JSON contains the keys ``guest_id``,
          ``actions_planned``, and ``actions_count``.
      (d) The value of ``guest_id`` matches the CLI argument.
      (e) The value of ``actions_count`` equals
          ``len(actions_planned)`` (consistency invariant).
      (f) The value of ``actions_count`` is >= 1 (the library returns the
          5-step atomic cascade per ``auto_cascade.py:265-320``,
          ``forget_guest`` orchestration).
    """
    guest_id = "G-W1-001"
    completed = _run_kurort_engine(("dsgvo", "cascade", guest_id))

    # (a) Exit code must be 0.
    assert completed.returncode == 0, (
        f"AC-2: `python -m kurort_engine dsgvo cascade {guest_id}` must "
        f"exit 0 to be operator-reachable. Got "
        f"returncode={completed.returncode}. Subprocess stderr:\n{completed.stderr}"
    )

    # (b) stdout must be parseable as a JSON object.
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"AC-2: stdout must be valid JSON (the dsgvo cascade reports "
            f"the planned retention actions as a JSON object per "
            f"spec.yaml:48). Got unparseable stdout "
            f"({exc.msg} at line {exc.lineno} col {exc.colno}):\n"
            f"{completed.stdout}"
        )
    assert isinstance(parsed, dict), (
        f"AC-2: parsed stdout must be a JSON object (dict). Got type "
        f"{type(parsed).__name__}. Stdout:\n{completed.stdout}"
    )

    # (c) The canonical keys must all be present.
    canonical_keys = ("guest_id", "actions_planned", "actions_count")
    missing_keys = [k for k in canonical_keys if k not in parsed]
    assert not missing_keys, (
        f"AC-2: parsed JSON must contain all canonical keys "
        f"{list(canonical_keys)}. Missing: {missing_keys}. "
        f"Got keys: {sorted(parsed.keys())}. Stdout:\n{completed.stdout}"
    )

    # (d) The echoed guest_id must match the CLI argument.
    assert parsed["guest_id"] == guest_id, (
        f"AC-2: parsed JSON guest_id must match the CLI argument "
        f"{guest_id!r}. Got {parsed['guest_id']!r}. Stdout:\n{completed.stdout}"
    )

    # (e) Consistency invariant: actions_count == len(actions_planned).
    actions_planned = parsed["actions_planned"]
    actions_count = parsed["actions_count"]
    assert isinstance(actions_planned, list), (
        f"AC-2: `actions_planned` must be a list (the 5-step atomic "
        f"cascade per `auto_cascade.py:265-320`). Got type "
        f"{type(actions_planned).__name__}. Stdout:\n{completed.stdout}"
    )
    assert isinstance(actions_count, int), (
        f"AC-2: `actions_count` must be an int. Got type "
        f"{type(actions_count).__name__}. Stdout:\n{completed.stdout}"
    )
    assert len(actions_planned) == actions_count, (
        f"AC-2: `actions_count` ({actions_count}) must equal "
        f"len(actions_planned) ({len(actions_planned)}). Stdout:\n"
        f"{completed.stdout}"
    )

    # (f) The 5-step atomic cascade must produce at least 1 planned action.
    assert actions_count >= 1, (
        f"AC-2: `actions_count` must be >= 1 (the library returns the "
        f"5-step atomic cascade per `auto_cascade.py:265-320`). Got "
        f"{actions_count}. Stdout:\n{completed.stdout}"
    )


# ---------------------------------------------------------------------------
# AC-3 — `python -m kurort_engine predicate file` persists an artifact
# ---------------------------------------------------------------------------


def test_ac3_predicate_file_subcommand_persists_artifact(tmp_path) -> None:
    """AC-3 spec test_oracle: ``predicate file YEAR HEILBAD_CODE`` exits 0
    and persists a predicate artifact to the configured output directory.

    The AC-3 EARS contract (per ``spec.yaml:50-52``):
      "When the user invokes `python -m kurort_engine predicate file` with
       a `year` argument (integer) and a `heilbad_code` argument (string),
       then the system shall dispatch to
       `kurort_engine.predicate_filing.run(year, heilbad_code)`, persist
       the predicate artifact to the configured output directory, and emit
       a success line on stdout containing the year, the heilbad_code, and
       the persisted artifact path."

    Sub-conditions (must FAIL with AssertionError in RED phase because
    ``predicate`` subcommand does NOT exist yet — argparse rejects with
    ``invalid choice: 'predicate'``):
      (a) The subprocess exit code is 0.
      (b) The subprocess stdout contains the year argument as a decimal
          substring.
      (c) The subprocess stdout contains the heilbad_code argument as a
          substring.
      (d) The subprocess stdout mentions a persisted artifact path
          (contains ``artifact=`` or ``artifact:`` marker).
    """
    year = 2026
    heilbad_code = "BAD_ORB"
    output_dir = tmp_path / "predicate_artifacts"

    completed = _run_kurort_engine(
        (
            "predicate",
            "file",
            str(year),
            heilbad_code,
            "--output-dir",
            str(output_dir),
        ),
    )

    # (a) Exit code must be 0.
    assert completed.returncode == 0, (
        f"AC-3: `python -m kurort_engine predicate file {year} "
        f"{heilbad_code} --output-dir {output_dir}` must exit 0 to be "
        f"operator-reachable. Got returncode={completed.returncode}. "
        f"Subprocess stderr:\n{completed.stderr}"
    )

    # (b) stdout must mention the year.
    assert str(year) in completed.stdout, (
        f"AC-3: stdout must contain the year argument {year!r} so the "
        f"operator sees which filing cycle the artifact corresponds to. "
        f"Got stdout:\n{completed.stdout}"
    )

    # (c) stdout must mention the heilbad_code.
    assert heilbad_code in completed.stdout, (
        f"AC-3: stdout must contain the heilbad_code argument "
        f"{heilbad_code!r} so the operator sees which Heilbad the filing "
        f"is for. Got stdout:\n{completed.stdout}"
    )

    # (d) stdout must mention a persisted artifact path. The exact
    # marker text is the handler's choice (the EARS contract names the
    # contents: year + heilbad_code + artifact path); we accept any
    # substring containing the literal word `artifact=` followed by the
    # path component, OR the literal `artifact` keyword + a path-like
    # component. Using a substring marker keeps the test resilient to
    # GREEN-phase wording choices that still satisfy the EARS contract.
    has_artifact_marker = (
        "artifact=" in completed.stdout
        or "artifact: " in completed.stdout
        or "artifact path" in completed.stdout
    )
    assert has_artifact_marker, (
        f"AC-3: stdout must mention the persisted artifact path "
        f"(the handler must print a success line containing the artifact "
        f"path per spec.yaml:51 EARS contract). Got stdout:\n"
        f"{completed.stdout}"
    )
