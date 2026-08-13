"""MinLOS profile loader for the channel_manager_minstay package (AC-1).

Loads per-Bundesland × per-Kurort MinLOS peak-week rules from declarative
YAML profiles. Mirrors the pattern of ``kurort_engine.rates.load_profile``:

* Frozen-dataclass domain types (``MinLosRule``, ``MinLosProfile``).
* ``yaml.safe_load`` (NOT ``yaml.load``) per AC-1's explicit security clause.
* Ordered search-path walker — package-bundled ``profiles/`` directory first,
  then ``tests/fixtures/channel_manager_minstay/profiles/`` (so the test
  fixtures can shadow the production profile if needed).
* ``FileNotFoundError`` raised when no profile matches — naming both
  searched directories so the caller can diagnose the miss.

The five canonical DHV Saison rule names (``easter`` / ``whitsun`` /
``summer`` / ``christmas`` / ``shoulder``) are NOT hard-coded here — they
live in the YAML profile. The loader is generic; future per-Bundesland
profiles can introduce new Saison names (e.g. Bayern "Starkbierfest",
B-W "Cannstatter Volksfest") without touching the loader code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Ordered profile search path. The package-bundled ``profiles/`` directory
# is listed FIRST so that the production default is authoritative; the
# test-fixtures directory comes SECOND so tests can shadow the production
# default if needed (parity with the ``kurort_engine.rates`` convention
# documented at rates.py:12-22 — note: that loader has the OPPOSITE order
# for historical reasons; we preserve "production first" here).
#
#   Path(__file__)             = repo/src/channel_manager_minstay/profile_loader.py
#   Path(__file__).parents[0]  = repo/src/channel_manager_minstay/  -> 'profiles/'
#   Path(__file__).parents[2]  = repo/                              -> 'tests/fixtures/...'
_PROFILE_SEARCH_PATH: tuple[Path, ...] = (
    Path(__file__).parents[0] / "profiles",
    Path(__file__).parents[2] / "tests" / "fixtures" / "channel_manager_minstay" / "profiles",
)


@dataclass(frozen=True)
class MinLosRule:
    """One MinLOS peak-week rule (e.g. Easter 2026-04-03..2026-04-12, minlos=5).

    Mirrors the field schema declared in the YAML profile:

      * ``name``           — canonical rule identifier ("easter" / "whitsun" /
                              "summer" / "christmas" / "shoulder"; future
                              profiles may introduce new identifiers).
      * ``date_range``     — ISO-8601 ``[start, end]`` date tuple (strings,
                              parsed at the dataclass level so the consumer
                              can interpret them as ``datetime.date`` if
                              desired; the loader does NOT coerce to
                              ``date`` to preserve YAML-as-string parity
                              with the source file).
      * ``minlos``         — minimum length of stay in nights (int).
      * ``applies_to_ota`` — whether this rule pushes to OTA channels
                              (bool). Shoulder rules typically set this to
                              ``False`` so 1-night bookings are not blocked
                              on Booking.com / HRS.

    The dataclass is ``frozen=True`` so a rule, once loaded, cannot be
    mutated by downstream consumers (the MinLOS push scheduler reads from
    immutable snapshots to keep audit-log hashes deterministic).
    """

    name: str
    date_range: tuple[str, str]
    minlos: int
    applies_to_ota: bool


@dataclass(frozen=True)
class MinLosProfile:
    """The resolved MinLOS profile for one (Bundesland, Kurort) pair.

    Carries:

      * ``bundesland`` — e.g. "hessen".
      * ``kurort``     — e.g. "bad_orb".
      * ``rules``      — tuple of :class:`MinLosRule` entries (one per
                         named DHV Saison + a default ``shoulder`` rule).
                         A ``tuple`` (not ``list``) keeps the dataclass
                         hashable and signals to readers that the rules
                         are immutable in load order.

    The dataclass is ``frozen=True`` so a profile, once loaded, cannot be
    mutated by downstream consumers.
    """

    bundesland: str
    kurort: str
    rules: tuple[MinLosRule, ...] = field(default_factory=tuple)


def _coerce_rule(raw: dict[str, Any]) -> MinLosRule:
    """Convert one raw YAML rule dict into a :class:`MinLosRule`.

    ``date_range`` arrives as a 2-element list from ``yaml.safe_load``; we
    coerce it to a ``tuple`` so the dataclass field type matches the
    declared ``tuple[str, str]``. ``minlos`` arrives as an int (already
    parsed by PyYAML). ``applies_to_ota`` arrives as a bool.

    No defensive ``None``-stripping here — the YAML schema is fixed and a
    missing required field surfaces as a clear ``KeyError`` /
    ``TypeError`` from the dataclass constructor (fail-loud per the
    project's pattern from ``kurort_engine.rates._coerce_band``).
    """
    date_range = raw["date_range"]
    if not isinstance(date_range, (list, tuple)) or len(date_range) != 2:
        raise ValueError(
            f"MinLOS rule {raw.get('name')!r} has invalid date_range "
            f"(expected [start, end] list/tuple, got {date_range!r})"
        )
    return MinLosRule(
        name=str(raw["name"]),
        date_range=(str(date_range[0]), str(date_range[1])),
        minlos=int(raw["minlos"]),
        applies_to_ota=bool(raw["applies_to_ota"]),
    )


def load_minlos_profile(bundesland: str, kurort: str) -> MinLosProfile:
    """Load a :class:`MinLosProfile` for one (Bundesland, Kurort) pair.

    Walks :data:`_PROFILE_SEARCH_PATH` in order; the first directory that
    contains ``<bundesland>_<kurort>_minlos.yaml`` wins. Raises
    :class:`FileNotFoundError` (naming both searched directories) if no
    match is found.

    Parameters
    ----------
    bundesland:
        Canonical Bundesland identifier (e.g. ``"hessen"``). Used to
        construct the profile filename ``<bundesland>_<kurort>_minlos.yaml``.
    kurort:
        Canonical Kurort identifier (e.g. ``"bad_orb"``).

    Returns
    -------
    MinLosProfile
        The resolved profile with a ``.rules`` tuple of
        :class:`MinLosRule` entries.

    Raises
    ------
    FileNotFoundError
        When no matching ``<bundesland>_<kurort>_minlos.yaml`` exists in
        any searched directory. The error message names both searched
        directories so the caller can diagnose the miss.

    Notes
    -----
    Uses :func:`yaml.safe_load` (NOT :func:`yaml.load`) so an untrusted
    profile cannot execute arbitrary Python via the YAML tag mechanism.
    This is the AC-1 security clause — preserved verbatim in the
    spec.yaml EARS statement.
    """
    filename = f"{bundesland}_{kurort}_minlos.yaml"
    for directory in _PROFILE_SEARCH_PATH:
        candidate = directory / filename
        if candidate.is_file():
            with candidate.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
            rules: tuple[MinLosRule, ...] = tuple(
                _coerce_rule(rule) for rule in data["rules"]
            )
            return MinLosProfile(
                bundesland=str(data["bundesland"]),
                kurort=str(data["kurort"]),
                rules=rules,
            )
    searched = ", ".join(str(path) for path in _PROFILE_SEARCH_PATH)
    raise FileNotFoundError(
        f"No MinLOS profile found for {bundesland!r}/{kurort!r} "
        f"(searched: {searched})"
    )