# Repro 004: load_2026_profile silently accepts string-typed period (or reprdikatisierung_window),
# violating the AC-2 contract that the field MUST be tuple[str, str].
#
# Run: pytest output/repros/004_load_2026_profile_period_string_bypass.py -v
# Expected: this test should pass after the bug is fixed.
#
# Bug: at kurort_engine.predicate_filing.2026_validate.load_2026_profile lines 178-187:
#     for tuple_field in ("period", "reprdikatisierung_window"):
#         value = profile.get(tuple_field)
#         if isinstance(value, list):
#             value_tuple = tuple(value)
#             if len(value_tuple) != 2 or not all(isinstance(s, str) for s in value_tuple):
#                 raise ValueError(...)
#             profile[tuple_field] = value_tuple
#
# The `isinstance(value, list)` check is THE ONLY guard. If the YAML profile
# (or a caller-supplied dict override) emits a non-list scalar (e.g., a single
# string), the loader returns the dict with the field still as a `str` —
# silently violating the AC-2 contract that `period: tuple[str, str]`.
# Downstream consumers (predicate_packet_assembler + audit + audit) that rely
# on profile.period being a tuple will crash with TypeError on `period[0]`
# or `period[1]` indexing, AFTER the profile has been persisted + the
# attestation generated (so the attestation is corrupt upstream).
"""Repro 004 — load_2026_profile silently accepts string-typed period."""

from __future__ import annotations

import os
import tempfile

import pytest

_v = __import__(
    "kurort_engine.predicate_filing.2026_validate",
    fromlist=["_dummy_"],
)


def _load_custom_yaml(yaml_text: str) -> dict:
    """Helper: monkey-patch `_resolve_profile_path` and call `load_2026_profile`."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_text)
        path = f.name
    orig = _v._resolve_profile_path
    _v._resolve_profile_path = lambda: path
    try:
        return _v.load_2026_profile()
    finally:
        _v._resolve_profile_path = orig
        os.unlink(path)


# Use literal substitution, not str.format() (the YAML has { and } characters
# that interact badly with format()).
_TEST_YAML_PERIOD_AS_STRING = """
predicate_label: "test"
period: "2026-07-01"
reprdikatisierung_window: ["2034-01-01", "2044-12-31"]
accessibility_label: "test"
non_affirmation_footer: "test"
bfsg_aa_compliant: true
bundesland: hessen
kurort: bad_orb
predicate: heilbad
satzung_date: "2026-07-01"
attestation_template_id: "bad_orb_2026_v1"
beglaubigung_clauses: []
stale_pending: false
bands:
  - name: adult
    rate_eur: "2.50"
preserves_iter33_fields: true
"""


def test_repro_004_period_as_string_returns_tuple() -> None:
    """AC-2 contract: profile.period MUST be `tuple[str, str]`.

    The shipped loader silently accepts a string-typed period (because the
    guard at 2026_validate.py:178-187 only checks `isinstance(value, list)`).
    A caller that accidentally provides a string gets back `period: str`
    instead of `period: tuple[str, str]` — silently violating the contract.
    """
    profile = _load_custom_yaml(_TEST_YAML_PERIOD_AS_STRING)

    period = profile["period"]
    assert isinstance(period, tuple), (
        f"BUG: AC-2 requires profile.period to be tuple[str, str]; "
        f"got {type(period).__name__}: {period!r}. The loader accepts the "
        f"string silently because the only guard is "
        f"`isinstance(value, list)` at "
        f"kurort_engine.predicate_filing.2026_validate.load_2026_profile:180. "
        f"A string-typed period will silently propagate downstream, where "
        f"tuple-unpacking (`start, end = profile.period`) will crash with "
        f"`TypeError: cannot unpack non-iterable str object`."
    )
    assert len(period) == 2 and all(isinstance(s, str) for s in period), (
        f"AC-2: period must be tuple[str, str] of length 2; got {period!r}"
    )
