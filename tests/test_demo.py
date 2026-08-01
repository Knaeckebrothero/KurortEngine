"""AC-11: synthetic Bad Orb month demo (100 reservations, byte-for-byte reproducible).

Test_oracle path recorded in `spec.yaml:171` and `spec_lock.md:183`.
The placeholder demo at `repo/src/kurort_engine/demos/synthetic_bad_orb_month.py`
currently prints a placeholder line and returns 0; it does NOT write a CSV. This
red-phase test therefore fails with `AssertionError` on the "CSV exists" check,
NOT with `ImportError` / `SyntaxError` / `CollectionError`.

Contract under test (spec.yaml:161-171 / spec_lock.md:167-183):

* Running ``python -m kurort_engine.demos.synthetic_bad_orb_month`` exits 0.
* The demo writes a CSV at
  ``repo/src/kurort_engine/demos/out/synthetic_bad_orb_<yyyy_mm>.csv``.
* The CSV contains >=100 data rows (after the 12-column header).
* The 5 rate-band names (``adult``, ``adult_disabled_70``, ``youth``,
  ``youth_disabled_70``, ``child``) are all present across the dataset.
* Both recognised exemption categories (``geschaeftsreisender``,
  ``schwerbehindert_100``) are present across the dataset.
* The CSV is byte-for-byte identical to
  ``repo/tests/fixtures/expected_synthetic_bad_orb.csv`` (deterministic seeded
  RNG; two runs of the demo produce the same bytes).

The EARS line says "all four exemption categories" but the current
``kurort_engine.exemptions`` module recognises exactly two categories
(``geschaeftsreisender`` and ``schwerbehindert_100``). The test asserts
that BOTH recognised categories are present, which is the closest faithful
mapping of "all exemption categories" without asserting on a category that
does not exist. Any future spec-revision that adds more categories must
also extend this assertion surface.

The fixture file ``tests/fixtures/expected_synthetic_bad_orb.csv`` is
checked-in alongside the green implementation (it is the demo's first
deterministic output, committed as the golden-master). The test asserts
byte-for-byte equality with this fixture.
"""
from __future__ import annotations

import csv
import glob
import io
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Constants — derived from the AC-11 EARS contract and the shipped exemptions
# ---------------------------------------------------------------------------

# All 5 rate bands defined in `repo/src/kurort_engine/profiles/hessen_bad_orb.yaml`
# — keyed by `name` so the assertion reads naturally.
AC11_RATE_BANDS: tuple[str, ...] = (
    "adult",
    "adult_disabled_70",
    "youth",
    "youth_disabled_70",
    "child",
)

# Both currently-recognised exemption categories from `kurort_engine.exemptions`
# (`_RECOGNISED_CATEGORIES = frozenset({"geschaeftsreisender", "schwerbehindert_100"})`).
# The AC-11 EARS references "all four exemption categories"; this test pins the
# two that the engine currently recognises. Future expansions must update this
# tuple and the spec.
AC11_EXEMPTION_CATEGORIES: tuple[str, ...] = (
    "geschaeftsreisender",
    "schwerbehindert_100",
)

# Header schema (verbatim from `kurort_engine/reporting.py::AC4_HEADER_COLUMNS`).
AC11_HEADER_COLUMNS: tuple[str, ...] = (
    "Reservation-ID",
    "anonymised guest name",
    "arrival",
    "departure",
    "day_count",
    "rate_band",
    "per_guest_per_day_eur",
    "exemption_flag",
    "subtotal_eur",
    "period_yyyy_mm",
    "hotel_steuernummer",
    "hotel_signature_line",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT: Path = Path(__file__).resolve().parents[1]
_DEMOS_OUT_DIR: Path = _REPO_ROOT / "src" / "kurort_engine" / "demos" / "out"
_FIXTURE_PATH: Path = _REPO_ROOT / "tests" / "fixtures" / "expected_synthetic_bad_orb.csv"


def _run_demo() -> tuple[int, str, str]:
    """Run ``python -m kurort_engine.demos.synthetic_bad_orb_month`` via subprocess.

    Returns ``(returncode, stdout, stderr)``. Uses the on-disk Python interpreter
    + ``PYTHONPATH=src`` so the demo module resolves the same way an operator's
    shell would after ``cd repo``.

    The subprocess call is the unit-under-test boundary for AC-11 — NOT a mock
    of the demo's internal logic. The red-phase test invokes the actual demo;
    if the demo is a stub, this helper still exits cleanly with stdout containing
    the placeholder line, and the subsequent file-existence assertion will fail.
    """
    env_overrides = {"PYTHONPATH": "src"}
    completed = subprocess.run(
        [sys.executable, "-m", "kurort_engine.demos.synthetic_bad_orb_month"],
        cwd=str(_REPO_ROOT),
        env={**__import__("os").environ, **env_overrides},
        capture_output=True,
        text=True,
        timeout=60,
    )
    return completed.returncode, completed.stdout, completed.stderr


def _find_produced_csv() -> Path | None:
    """Return the most recent CSV file the demo produced, or None.

    Glob ``demos/out/synthetic_bad_orb_*.csv`` (the demo's documented output
    naming pattern). Returns the lexicographically last match — the demo
    always uses a single period in its filename so the natural sort order
    is sufficient.
    """
    if not _DEMOS_OUT_DIR.is_dir():
        return None
    matches = sorted(_DEMOS_OUT_DIR.glob("synthetic_bad_orb_*.csv"))
    return matches[-1] if matches else None


def _parse_csv_rows(csv_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Return ``(header, data_rows)`` parsed from ``csv_path`` using csv.DictReader.

    The header is parsed with csv.reader to preserve column order; data rows
    are parsed once with csv.DictReader for keyed access in assertions.
    """
    text = csv_path.read_text(encoding="utf-8")
    with __import__("io").StringIO(text) as handle:
        reader = csv.reader(handle)
        rows = list(reader)
    assert rows, f"CSV {csv_path} must contain at least the header row, got empty"
    header = rows[0]
    data_rows = list(csv.DictReader(io.StringIO(text)))
    return header, data_rows


# ---------------------------------------------------------------------------
# Spec test_oracle — the single canonical AC-11 verdict function
# ---------------------------------------------------------------------------


def test_ac11_demo_synthetic_bad_orb_month_produces_reproducible_csv(
    tmp_path: Path,
) -> None:
    """AC-11 spec test_oracle: synthetic Bad Orb demo produces a reproducible CSV.

    Bundles all six AC-11 conditions into one assertion surface so
    ``pytest -k test_ac11_demo_synthetic_bad_orb_month_produces_reproducible_csv``
    is the canonical verdict command.

    Sub-conditions (each broken out via inline ``assert`` so a failure reports
    a focused error message rather than a bare generic-comparison trace):

      (a) The demo exits with code 0 when invoked as a subprocess.
      (b) The demo writes a CSV file under ``src/kurort_engine/demos/out/``
          following the ``synthetic_bad_orb_<yyyy_mm>.csv`` naming convention.
      (c) The CSV contains >=100 data rows after the 12-column header.
      (d) The dataset spans all 5 Hessen Bad Orb rate bands.
      (e) The dataset includes both recognised exemption categories.
      (f) The CSV is byte-for-byte identical to the committed fixture
          ``tests/fixtures/expected_synthetic_bad_orb.csv`` — proving that the
          demo's seeded RNG produces a deterministic, reproducible output.

    Forbidden patterns enforced:
      * NO ``pytest.skip`` / ``@pytest.mark.skip`` / ``@pytest.mark.xfail``.
      * NO mocking of the demo module — the subprocess invokes it as-is.
      * NO ``assert True`` or tautological assertion (every ``assert`` here
        compares two distinguishable expressions or captures state from a
        real subprocess run).
    """
    # ----------------------------------------------------------------------
    # (a) The demo exits cleanly
    # ----------------------------------------------------------------------
    returncode, _stdout, stderr = _run_demo()
    assert returncode == 0, (
        f"AC-11: `python -m kurort_engine.demos.synthetic_bad_orb_month` must "
        f"exit 0, got returncode={returncode}. Subprocess stderr:\n{stderr}"
    )

    # ----------------------------------------------------------------------
    # (b) The CSV file exists at the documented path
    # ----------------------------------------------------------------------
    produced_csv = _find_produced_csv()
    assert produced_csv is not None, (
        f"AC-11: demo must write a CSV at "
        f"{_DEMOS_OUT_DIR}/synthetic_bad_orb_<yyyy_mm>.csv but no such file was "
        f"found. Directory exists: {_DEMOS_OUT_DIR.is_dir()}. "
        f"Directory contents: "
        f"{list(_DEMOS_OUT_DIR.iterdir()) if _DEMOS_OUT_DIR.is_dir() else 'N/A'}."
    )
    assert produced_csv.is_file(), (
        f"AC-11: produced path {produced_csv} exists but is not a regular file"
    )

    # ----------------------------------------------------------------------
    # (c) The CSV has >=100 data rows AND a 12-column header in spec order
    # ----------------------------------------------------------------------
    header, data_rows = _parse_csv_rows(produced_csv)
    assert tuple(header) == AC11_HEADER_COLUMNS, (
        f"AC-11: header must match the spec 12-column schema verbatim.\n"
        f"  expected: {AC11_HEADER_COLUMNS}\n"
        f"  got:      {tuple(header)}"
    )
    assert len(data_rows) >= 100, (
        f"AC-11: CSV must contain >=100 data rows (100 reservations; multi-guest "
        f"stays expand row count), got {len(data_rows)} rows"
    )

    # ----------------------------------------------------------------------
    # (d) All 5 Hessen Bad Orb rate bands are present across the dataset
    # ----------------------------------------------------------------------
    seen_bands = {row.get("rate_band", "") for row in data_rows}
    missing_bands = [b for b in AC11_RATE_BANDS if b not in seen_bands]
    assert not missing_bands, (
        f"AC-11: dataset must span all 5 Hessen Bad Orb rate bands "
        f"{AC11_RATE_BANDS}. Missing: {missing_bands}. "
        f"Seen bands: {sorted(seen_bands)}"
    )

    # ----------------------------------------------------------------------
    # (e) Both currently-recognised exemption categories are present
    # ----------------------------------------------------------------------
    seen_exemptions = {row.get("exemption_flag", "") for row in data_rows}
    seen_exemptions.discard("")  # paying guests have empty exemption_flag
    missing_exemptions = [
        e for e in AC11_EXEMPTION_CATEGORIES if e not in seen_exemptions
    ]
    assert not missing_exemptions, (
        f"AC-11: dataset must include all recognised exemption categories "
        f"{AC11_EXEMPTION_CATEGORIES}. Missing: {missing_exemptions}. "
        f"Seen exemption_flag values: {sorted(seen_exemptions)}"
    )

    # ----------------------------------------------------------------------
    # (f) Byte-for-byte reproducibility — diff against the committed fixture
    # ----------------------------------------------------------------------
    assert _FIXTURE_PATH.is_file(), (
        f"AC-11: fixture file {_FIXTURE_PATH} (the golden-master CSV) must "
        f"exist alongside the demo implementation for diff-checking. The "
        f"green phase commits this fixture from the demo's first deterministic "
        f"run."
    )
    fixture_bytes = _FIXTURE_PATH.read_bytes()
    produced_bytes = produced_csv.read_bytes()
    assert produced_bytes == fixture_bytes, (
        f"AC-11: produced CSV must be byte-for-byte identical to the committed "
        f"fixture.\n"
        f"  fixture SHA-256: {__import__('hashlib').sha256(fixture_bytes).hexdigest()}\n"
        f"  produced SHA-256: {__import__('hashlib').sha256(produced_bytes).hexdigest()}\n"
        f"  fixture size: {len(fixture_bytes)} bytes\n"
        f"  produced size: {len(produced_bytes)} bytes\n"
        f"  first-diff context (first line that differs, or '' if sizes differ):\n"
        f"  {next((f'fixture={fl!r}  produced={pl!r}' for fl, pl in zip(fixture_bytes.splitlines(keepends=True), produced_bytes.splitlines(keepends=True)) if fl != pl), 'N/A')}"
    )

    # ALSO run the demo a SECOND time and confirm output is byte-identical to
    # the first run — this catches an RNG that is "seeded" but not "deterministic"
    # across separate invocations.
    returncode2, _stdout2, stderr2 = _run_demo()
    assert returncode2 == 0, (
        f"AC-11: second demo run must also exit 0, got returncode={returncode2}. "
        f"Subprocess stderr:\n{stderr2}"
    )
    produced_csv_2 = _find_produced_csv()
    assert produced_csv_2 is not None and produced_csv_2.is_file(), (
        f"AC-11: second demo run must also write a CSV; got {produced_csv_2}"
    )
    assert produced_csv_2.read_bytes() == fixture_bytes, (
        f"AC-11: second demo run produced a different CSV than the first; the "
        f"demo's RNG is not deterministic across separate invocations.\n"
        f"  fixture SHA-256:    {__import__('hashlib').sha256(fixture_bytes).hexdigest()}\n"
        f"  first-run SHA-256:  {__import__('hashlib').sha256(produced_csv.read_bytes()).hexdigest()}\n"
        f"  second-run SHA-256: {__import__('hashlib').sha256(produced_csv_2.read_bytes()).hexdigest()}"
    )

    # Optional hygiene: shutil.rmtree the demos/out directory after the test
    # so re-runs of pytest do not accumulate stale CSVs (cleanup is not a
    # test-pass criterion, but keeps the workspace tidy). The rm is best-effort
    # and must not raise — pytest will not fail the suite if it errors.
    if tmp_path is not None:  # pragma: no cover — guaranteed by pytest fixture
        pass  # no-op placeholder; we intentionally do NOT delete the CSV
              # because downstream debugging may want to inspect it.


# ---------------------------------------------------------------------------
# Helpers — narrow assertions, each broken out for readable failure messages
# ---------------------------------------------------------------------------
#
# These exist primarily as RED diagnostics — they share the `_run_demo`
# subprocess call via the main test (not via a fresh subprocess run each)
# so the suite cost stays at ONE demo invocation for the full AC-11 verdict.
# Left here intentionally to document the contract piecewise; the main test
# already covers them in its inline asserts.


def test_ac11_module_path_is_importable_without_demo_invocation() -> None:
    """AC-11 collateral: the demo module must be importable from any cwd.

    This is NOT the AC-11 spec test_oracle (that's the master test above);
    it is a separate assertion that documents the module's import surface
    is not gated on directory state. If this fails, the demo's directory
    layout is broken and the master test will also fail downstream.
    """
    # `importlib.import_module` from the module-name path proves the
    # Python path can find the demo. We assert importability without
    # invoking `main()`.
    import importlib

    module = importlib.import_module("kurort_engine.demos.synthetic_bad_orb_month")
    assert module is not None, (
        "AC-11: demo module must be importable as "
        "'kurort_engine.demos.synthetic_bad_orb_month'"
    )
    assert hasattr(module, "main"), (
        "AC-11: demo module must expose a `main()` function (called via "
        "`python -m ...` and by the AC-11 spec test_oracle)"
    )
    assert callable(module.main), "AC-11: demo `main` must be callable"
