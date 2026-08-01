"""AC-10: per-Bundesland plug-in profile — second profile loads without code change.

Test_oracle path recorded in spec.yaml:159. This is the red-phase test that
will fail with `AttributeError: module 'kurort_engine' has no attribute
'load_profile'` until Phase 4 green implements the loader in
`kurort_engine.rates`.

The fixture under `repo/tests/fixtures/profiles/bayern_bad_reichenhall.yaml`
is deliberately a different schema from the Hessen Bad Orb default (2 bands,
adult €3.00, satzung_date 2020-01-01) so the assertion can prove the loader
is config-driven rather than hardcoded to a single Satzung.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import kurort_engine
from kurort_engine import RateBand, Satzung


def test_ac10_second_bundesland_profile_loads_without_code_change() -> None:
    # The second profile must resolve purely from the YAML fixture; no
    # import or attribute access on kurort_engine.rates itself (the loader
    # is allowed to live there, but the test must not couple to its
    # private symbol names).
    satzung: Satzung = kurort_engine.load_profile("bayern", "bad_reichenhall")

    assert isinstance(satzung, Satzung), (
        f"load_profile must return a Satzung, got {type(satzung).__name__}"
    )
    assert satzung.bundesland == "bayern"
    assert satzung.kurort == "bad_reichenhall"
    assert satzung.satzung_date == "2020-01-01"
    assert satzung.predicate == "heilbad"

    # Bayern Bad Reichenhall fixture has exactly 2 bands (adult + child) —
    # deliberately different from Hessen Bad Orb's 5. If the loader were
    # hardcoded, len(satzung.bands) would be 5, not 2.
    assert len(satzung.bands) == 2, (
        f"second profile fixture has 2 bands; got {len(satzung.bands)} "
        "(loader may be hardcoded to the Hessen Bad Orb table)"
    )
    for band in satzung.bands:
        assert isinstance(band, RateBand)

    by_name = {b.name: b for b in satzung.bands}
    assert set(by_name) == {"adult", "child"}, (
        f"second profile fixture declares adult + child; got {sorted(by_name)}"
    )
    assert by_name["adult"].rate_per_day == Decimal("3.00")
    assert by_name["child"].rate_per_day == Decimal("0.00")
