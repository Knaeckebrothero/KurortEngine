"""Test-only factories for kurort_engine calculator tests.

This module isolates test fixtures from the package's own ``kurort_engine``
modules. The factories are imported by ``tests/conftest.py`` (so pytest can
discover the fixtures) and may also be imported directly for ad-hoc checks
(see the smoke-test snippet in the Phase 9 todo list).
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import pytest

import kurort_engine
from kurort_engine import Guest, Satzung


# Pinned anchor day used by every calculator test. Using a single reference
# date keeps the age-band assertions deterministic and easy to read.
_ARRIVAL_ANCHOR: date = date(2024, 6, 10)


def make_hessen_satzung() -> Satzung:
    """Return the Hessen Bad Orb ``Satzung`` (loaded from YAML).

    Defined as a plain function rather than a pytest fixture so it can be
    called from non-pytest contexts (e.g. the import-smoke-test the Phase 9
    todo list requires). The session-scoped pytest fixture
    ``hessen_satzung`` below wraps this call and adds caching.
    """
    return kurort_engine.load_profile("hessen", "bad_orb")


def make_guest(
    age_years: int,
    disability_pct: Optional[int] = None,
    *,
    name: str = "Test Guest",
    nationality: str = "DE",
) -> Guest:
    """Return a ``Guest`` whose age on the arrival anchor equals ``age_years``.

    ``age_years`` is computed as of ``_ARRIVAL_ANCHOR``. Subtraction is done
    with a manual year walk (not ``relativedelta``) so the factory has no
    ``python-dateutil`` dependency; ``relativedelta`` would be more precise
    for birthdays that fall after the anchor mid-year, but for the integer
    ages used by the calculator tests (0, 5, 6, 15, 16, 30, 35, 50) the
    simple subtraction lands on the same calendar year and the age-band
    matcher (which rounds by full year) yields identical results.
    """
    birth_year = _ARRIVAL_ANCHOR.year - age_years
    return Guest(
        name=name,
        birth_date=date(birth_year, _ARRIVAL_ANCHOR.month, _ARRIVAL_ANCHOR.day),
        nationality=nationality,
        disability_pct=disability_pct,
    )


# ---------------------------------------------------------------------------
# pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def hessen_satzung() -> Satzung:
    """Session-scoped Hessen Bad Orb ``Satzung`` (parsed once per test run)."""
    return make_hessen_satzung()
