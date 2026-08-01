"""Satzung profile and rate-band definitions for kurort_engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

# Ordered profile search path. The test-fixtures directory is listed FIRST
# so that tests can shadow the production default (see AC-10). Both paths
# are resolved relative to this file's location inside the installed package:
#
#   Path(__file__)             = repo/src/kurort_engine/rates.py
#   Path(__file__).parents[0]  = repo/src/kurort_engine/  -> 'profiles/'
#   Path(__file__).parents[2]  = repo/                    -> 'tests/fixtures/profiles/'
_PROFILE_SEARCH_PATH: tuple[Path, ...] = (
    Path(__file__).parents[2] / "tests" / "fixtures" / "profiles",
    Path(__file__).parents[0] / "profiles",
)


# ``max_age`` and the ``disability_pct_*`` fields carry the convention that
# a YAML ``null`` (no value declared) means "no bound on this side". When
# the loader fills those into ``RateBand`` we substitute the conventions:
#   * ``max_age`` no-bound  -> 999  (well above any plausible guest age)
#   * ``disability_pct_min`` no-bound -> 0
#   * ``disability_pct_max`` no-bound -> 0
# These defaults let the dataclass stay typed as ``int`` while preserving
# the YAML's "absent" semantics.
_MAX_AGE_NO_BOUND: int = 999
_DISABILITY_PCT_NO_BOUND: int = 0


@dataclass(frozen=True)
class RateBand:
    """One row of a Kurbeitragssatzung tariff table.

    The age and disability-pct fields are stored as ``int`` rather than
    ``Optional[int]`` so the dataclass stays trivially hashable and
    comparable. A YAML ``null`` is mapped to a sentinel default documented
    above (``_MAX_AGE_NO_BOUND`` / ``_DISABILITY_PCT_NO_BOUND``).
    """

    name: str
    min_age: int
    rate_per_day: Decimal
    max_age: int = _MAX_AGE_NO_BOUND
    disability_pct_min: int = _DISABILITY_PCT_NO_BOUND
    disability_pct_max: int = _DISABILITY_PCT_NO_BOUND


@dataclass(frozen=True)
class Satzung:
    """Placeholder: the resolved Satzung object for one (Bundesland, Kurort) pair."""

    bundesland: str
    kurort: str
    satzung_date: str
    predicate: str
    bands: tuple[RateBand, ...] = field(default_factory=tuple)


def _coerce_band(raw: dict[str, Any]) -> RateBand:
    """Convert one raw YAML band dict into a ``RateBand``.

    ``None`` values (e.g. ``max_age: null``) are dropped so that the
    dataclass default takes over. ``rate_per_day`` may arrive as either a
    quoted ``str`` (preferred — avoids float drift) or a bare ``float``;
    both shapes are normalised via ``str(value)``.
    """
    cleaned: dict[str, Any] = {}
    for key, value in raw.items():
        if value is None:
            continue
        if key == "name":
            cleaned[key] = str(value)
        elif key == "rate_per_day":
            cleaned[key] = Decimal(str(value))
        else:
            cleaned[key] = int(value)
    return RateBand(**cleaned)


def load_profile(bundesland: str, kurort: str) -> Satzung:
    """Load a ``Satzung`` for one (Bundesland, Kurort) pair from a YAML profile.

    Walks ``_PROFILE_SEARCH_PATH`` in order; the first directory that
    contains ``<bundesland>_<kurort>.yaml`` wins. Raises
    ``FileNotFoundError`` (naming both searched directories) if no match
    is found.
    """
    filename = f"{bundesland}_{kurort}.yaml"
    for directory in _PROFILE_SEARCH_PATH:
        candidate = directory / filename
        if candidate.is_file():
            with candidate.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
            bands: tuple[RateBand, ...] = tuple(
                _coerce_band(band) for band in data["bands"]
            )
            return Satzung(
                bundesland=data["bundesland"],
                kurort=data["kurort"],
                satzung_date=data["satzung_date"],
                predicate=data["predicate"],
                bands=bands,
            )
    searched = ", ".join(str(path) for path in _PROFILE_SEARCH_PATH)
    raise FileNotFoundError(
        f"No profile found for {bundesland!r}/{kurort!r} (searched: {searched})"
    )