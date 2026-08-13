"""Pytest configuration for kurort_engine tests (intentionally empty during bootstrap)."""
from __future__ import annotations

from collections.abc import Generator

import pytest

from kurort_engine.audit import AuditLog


@pytest.fixture(autouse=True)
def _reset_audit_log_between_tests() -> Generator[None, None, None]:
    """Isolate AuditLog._shared_entries between tests (F-12 baseline-restore, iter-33 Path B).

    AuditLog stores the audit trail in a class-level list shared across every
    AuditLog() instance. Without this autouse fixture, entries written by an
    earlier test leak into later tests and produce cross-test pollution that
    breaks the AC-* test oracle assertions (F-12). Pre-yield clear scrubs
    state left by prior tests; post-yield clear scrubs state added by the
    current test so it cannot leak to the next. The fixture is intentionally
    minimal — it does NOT re-trigger ``kurort_engine.a11y.guest_pwa`` import-
    time audit emissions, because that coupling (added in iter-39 iter-2
    conftest) bled a11y entries into ``tests/test_audit.py::test_ac7`` and
    broke its order-preservation invariant. Per iter-33's shipped Path B
    design, the fixture ONLY clears the store; tests that depend on
    observing the SHIPPED audit infrastructure manage their own setup.
    """
    AuditLog._shared_entries.clear()
    yield
    AuditLog._shared_entries.clear()
