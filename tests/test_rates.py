"""AC-1: Hessen KAG Bad Orb Heilbad profile (Satzung 01.07.2020) — 5 bands + day-count rule.

Test_oracle path recorded in spec.yaml:60. This is the red-phase test that
will fail with `AttributeError: module 'kurort_engine' has no attribute
'load_profile'` until Phase 4 green implements the loader in
`kurort_engine.rates`.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

import kurort_engine
from kurort_engine import RateBand, Satzung


def test_ac1_hessen_bad_orb_satzung_table_loads_with_five_bands_and_day_count_rule() -> None:
    # --- Profile load (5-rate-band table from Satzung 01.07.2020) ------------
    satzung: Satzung = kurort_engine.load_profile("hessen", "bad_orb")

    assert isinstance(satzung, Satzung), (
        f"load_profile must return a Satzung, got {type(satzung).__name__}"
    )
    assert satzung.bundesland == "hessen"
    assert satzung.kurort == "bad_orb"
    assert satzung.satzung_date == "2020-07-01"
    assert satzung.predicate == "heilbad"

    # Exactly five bands, in the canonical order declared by the Satzung.
    assert len(satzung.bands) == 5, (
        f"Bad Orb Satzung 01.07.2020 has exactly 5 bands; got {len(satzung.bands)}"
    )
    for band in satzung.bands:
        assert isinstance(band, RateBand), (
            f"each band must be a RateBand, got {type(band).__name__}"
        )

    # Rate-band content keyed by `name` so the test stays readable when the
    # YAML is re-ordered by a future loader refactor.
    by_name = {b.name: b for b in satzung.bands}
    assert set(by_name) == {
        "adult",
        "adult_disabled_70",
        "child",
        "youth",
        "youth_disabled_70",
    }, f"unexpected band names: {sorted(by_name)}"

    # Per-day rates as Decimal(€). Match the published Satzung 01.07.2020
    # (adult 2.50, adult_disabled_70 1.25, youth 1.00, youth_disabled_70
    # 0.50, child 0.00). Decimal equality is exact — no float drift.
    assert by_name["adult"].rate_per_day == Decimal("2.50")
    assert by_name["adult_disabled_70"].rate_per_day == Decimal("1.25")
    assert by_name["youth"].rate_per_day == Decimal("1.00")
    assert by_name["youth_disabled_70"].rate_per_day == Decimal("0.50")
    assert by_name["child"].rate_per_day == Decimal("0.00")

    # --- Day-count rule ("An- und Abreisetag als ein Tag berechnet") ----------
    # Per spec.yaml:57-59: day_count = (departure - arrival).days. An- und
    # Abreisetag both count as one day each, so 2024-06-10..2024-06-13 is 3
    # full nights = 3 days of Kurtaxe.
    day_count = (date(2024, 6, 13) - date(2024, 6, 10)).days
    assert day_count == 3

    # And the resulting adult Kurtaxe for that stay is exact-Decimal.
    adult_total = by_name["adult"].rate_per_day * Decimal(day_count)
    assert adult_total == Decimal("7.50")