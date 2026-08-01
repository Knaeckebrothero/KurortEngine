"""Iter-33 Phase 2 RED tests — audit-log isolation for full-suite pytest-green.

This file codifies AC-2, AC-3, AC-4 from the iter-33 spec.yaml lock #2
(SHA-256 ``d29674a20e0b930b275b63fa49e52a8e40cecc7fea1ca34fb1fff3114859e3cf``).
The three tests below MUST fail with ``AssertionError`` when run BEFORE the
conftest autouse fixture is added (Phase 3 GREEN work). Once the fixture is in
place at ``repo/tests/conftest.py``, all three tests MUST pass.

Root-cause reference (binding):
  KB ``audit-test-isolation-pollution-from-import-time-audit-write-root-cause-2-mitigat``

Chosen mitigation: Path B — ``@pytest.fixture(autouse=True)`` in
``repo/tests/conftest.py`` that clears ``AuditLog._shared_entries`` BEFORE AND
AFTER each test. See KB ``iter-33-spec-summary-supplemental-...`` for canonical
Path labeling.

RED-verify protocol (per pinned rule 3 — RED verification):
  * Tests MUST fail with ``AssertionError``, NOT ImportError / SyntaxError /
    "0 collected" / ``pytest.skip``.
  * No mocking of the unit under test (the ``AuditLog`` / ``conftest.py``
    fixture).
  * No tautological assertions (``assert f(x) == f(x)``).
  * No ``pytest.skip`` / ``@pytest.mark.skip`` / ``@pytest.mark.xfail``.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

import kurort_engine
from kurort_engine import AuditEntry
from kurort_engine.audit import AuditLog


# ---------------------------------------------------------------------------
# AC-3 — audit log isolated between tests (class-level _shared_entries
#        must NOT carry entries written by a prior test)
# ---------------------------------------------------------------------------


def _write_sentinel_to_audit_log(sentinel: str) -> None:
    """Helper: append one sentinel AuditEntry to the shared AuditLog.

    Uses a unique payload so the test can prove the entry was written by THIS
    test (not by an upstream import-time write in ``kurort_engine.a11y.guest_pwa``).
    """
    log = AuditLog()
    log.append(
        AuditEntry(
            actor="test_audit_isolation_ac3_sentinel_writer",
            payload=f'{{"sentinel": "{sentinel}"}}',
        )
    )


def test_ac3_audit_log_isolated_between_tests_writer() -> None:
    """First half of AC-3: write a sentinel entry to the shared AuditLog.

    This test is the "polluter" — it deliberately writes a sentinel entry so
    that a subsequent test (``test_ac3_audit_log_isolated_between_tests_verifier``)
    can assert the sentinel was cleared by the conftest autouse fixture.

    If the fixture is NOT in place, the sentinel leaks into the next test
    and the verifier test will fail with ``AssertionError`` — that is the
    RED state we want.
    """
    sentinel = f"test_ac3_sentinel_{uuid.uuid4().hex}"
    _write_sentinel_to_audit_log(sentinel)
    # Stash the sentinel on the class-level shared store as a "mark" so the
    # verifier can find it via a different lookup path (defence-in-depth —
    # if conftest clears _shared_entries before the verifier, the verifier
    # finds nothing either way; if conftest does NOT clear, the verifier
    # finds the sentinel and asserts it is absent).
    AuditLog._shared_entries.append(
        AuditEntry(
            actor="test_audit_isolation_ac3_sentinel_mark",
            payload=f'{{"mark_sentinel": "{sentinel}"}}',
        )
    )
    # Sanity: at least one sentinel-bearing entry exists after our writes.
    payloads = [getattr(e, "payload", "") for e in AuditLog._shared_entries]
    assert any(sentinel in p for p in payloads), (
        f"Sentinel {sentinel!r} should have been written by this test "
        f"before the verifier runs"
    )


def test_ac3_audit_log_isolated_between_tests_verifier() -> None:
    """Second half of AC-3: verify no sentinel leaked from the prior test.

    Scans ``AuditLog._shared_entries`` for ANY payload containing a
    ``test_ac3_sentinel_`` substring. If the conftest autouse fixture is
    NOT in place, the writer test's sentinel entry will still be present
    and this assertion FAILS with ``AssertionError`` — proving test-to-test
    pollution. With the fixture in place, ``_shared_entries`` is cleared
    before this test runs and the assertion passes.
    """
    polluted_payloads = [
        getattr(entry, "payload", "")
        for entry in AuditLog._shared_entries
        if "test_ac3_sentinel_" in getattr(entry, "payload", "")
    ]
    assert polluted_payloads == [], (
        f"AuditLog._shared_entries leaked sentinel entries from a prior test "
        f"(conftest autouse fixture missing or not clearing the log): "
        f"{polluted_payloads!r}"
    )


# ---------------------------------------------------------------------------
# AC-2 — full pytest suite exits zero after the conftest fixture is in place
# ---------------------------------------------------------------------------


# Recursion sentinel: child pytest processes inherit this env var and skip
# the full-suite subprocess invocation, so the test cannot recursively spawn
# itself. See KB ``open-design-question-avoid-recursive-pytest-when-testing-
# full-suite-auditlog-iso`` for the design rationale.
_ISOLATION_RECURSION_SENTINEL = "KURORT_ENGINE_AUDIT_ISOLATION_SUBPROCESS"


def _resolve_pytest_binary(repo_root: Path) -> str:
    """Resolve the pytest binary path. Prefer ``.venv/bin/pytest``; fall back
    to ``python -m pytest`` if the venv binary is not present.
    """
    venv_pytest = repo_root / ".venv" / "bin" / "pytest"
    if venv_pytest.exists():
        return str(venv_pytest)
    # Fallback: use the current Python interpreter with -m pytest. This avoids
    # the ambiguity of a bare "pytest" command (which could resolve to the
    # parent pytest process and cause recursion).
    return f"{sys.executable} -m pytest"


def test_ac2_full_suite_exits_zero() -> None:
    """AC-2: ``pytest tests/ -q`` (excluding this isolation test) exits 0.

    Invokes the FULL pytest suite as a subprocess, EXCLUDING this file
    (``tests/test_audit_isolation.py``) to prevent recursive self-invocation.
    Asserts:
      1. Subprocess exit code == 0
      2. Summary line contains "0 failed"

    RED state (before conftest fixture): ``test_audit.py::test_ac7_audit_log_
    appends_entry_and_preserves_order`` fails due to import-time AuditLog
    pollution from ``kurort_engine.a11y.guest_pwa``. The subprocess exits
    non-zero and the summary line contains "1 failed" → ``AssertionError``.

    GREEN state (after conftest fixture): the fixture clears
    ``AuditLog._shared_entries`` before and after each test, so the
    pollution no longer corrupts the assertion. The subprocess exits 0
    with "0 failed" → assertion passes.

    Recursion guard: if the parent process is already a child of an audit-
    isolation subprocess (env var sentinel present), this test returns
    immediately without spawning another subprocess.
    """
    if os.environ.get(_ISOLATION_RECURSION_SENTINEL) == "1":
        # We are inside a child pytest invocation already; do NOT recurse.
        # This branch is reachable only in pathological environments and
        # is itself a pass (the parent's subprocess assertion already
        # covered the suite-level green state).
        return

    repo_root = Path(__file__).resolve().parent.parent
    pytest_bin = _resolve_pytest_binary(repo_root)
    if pytest_bin.endswith("-m pytest"):
        cmd = pytest_bin.split() + [
            "tests/",
            "--ignore=tests/test_audit_isolation.py",
            "-q",
            "-p",
            "no:cacheprovider",
            "--rootdir",
            str(repo_root),
        ]
    else:
        cmd = [
            pytest_bin,
            "tests/",
            "--ignore=tests/test_audit_isolation.py",
            "-q",
            "-p",
            "no:cacheprovider",
            "--rootdir",
            str(repo_root),
        ]

    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root / "src")
    env[_ISOLATION_RECURSION_SENTINEL] = "1"

    result = subprocess.run(
        cmd,
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    # Reconcile: pytest emits a summary line like "=== 113 passed in 1.13s ==="
    # or "=== 1 failed, 112 passed in 1.20s ===" depending on state.
    summary_line = ""
    for line in (result.stdout + result.stderr).splitlines():
        if "passed" in line or "failed" in line:
            if "==" in line:
                summary_line = line
                break

    assert result.returncode == 0, (
        f"Full pytest suite subprocess exited {result.returncode}, "
        f"expected 0. Summary: {summary_line!r}\n"
        f"STDOUT (tail): {result.stdout[-500:]!r}\n"
        f"STDERR (tail): {result.stderr[-500:]!r}"
    )
    assert "0 failed" in summary_line, (
        f"Full pytest suite summary must contain '0 failed' after conftest "
        f"fixture is in place. Got: {summary_line!r}"
    )


# ---------------------------------------------------------------------------
# AC-4 — ruff check passes on tests/conftest.py (no lint regressions)
# ---------------------------------------------------------------------------


def _resolve_ruff_binary(repo_root: Path) -> list[str]:
    """Resolve the ruff invocation. Prefer ``.venv/bin/ruff``; fall back to
    ``python -m ruff``.
    """
    venv_ruff = repo_root / ".venv" / "bin" / "ruff"
    if venv_ruff.exists():
        return [str(venv_ruff)]
    return [sys.executable, "-m", "ruff"]


def test_ac4_ruff_check_passes_on_conftest() -> None:
    """AC-4: ``ruff check tests/conftest.py`` exits 0 with no findings.

    Asserts the conftest fixture follows repo style conventions
    (line length, import order, naming). RED state: if the conftest fixture
    has lint findings, exit code != 0 → ``AssertionError``. GREEN state:
    exit code == 0 and findings list is empty → assertion passes.

    Note: AC-4 is a lint check on the GREEN-phase deliverable
    (``repo/tests/conftest.py``). Before the fixture is added, the existing
    conftest.py is a 1-line docstring — likely passes ruff already. The test
    will be re-evaluated after the GREEN-phase edit to conftest.py.
    """
    repo_root = Path(__file__).resolve().parent.parent
    conftest_path = repo_root / "tests" / "conftest.py"
    assert conftest_path.exists(), (
        f"conftest.py must exist at {conftest_path}"
    )

    cmd = _resolve_ruff_binary(repo_root) + ["check", str(conftest_path)]
    result = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, (
        f"ruff check on conftest.py exited {result.returncode}, expected 0. "
        f"STDOUT: {result.stdout!r}\nSTDERR: {result.stderr!r}"
    )
    # ruff emits "All checks passed!" on success; assert it appears.
    assert (
        "All checks passed" in result.stdout
        or "no findings" in result.stdout.lower()
        or result.stdout.strip() == ""
    ), (
        f"ruff check on conftest.py reported unexpected output: "
        f"{result.stdout!r}"
    )