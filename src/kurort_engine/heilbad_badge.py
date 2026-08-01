"""Heilbad 2026 badge — auto-expiry post-2036 Reprädikatisierung.

The property holds the Heilbad designation under the 04.03.2026..2036
Reprädikatisierung. After 2036-12-31 the badge is suppressed from every
booking confirmation and Gästekarte (spec.yaml AC-6).
"""
from __future__ import annotations

from datetime import date

# Inclusive end of the Reprädikatisierung window (Bad Orb Heilbad 2026).
HEILBAD_EFFECTIVE_FROM: date = date(2026, 3, 4)
HEILBAD_EXPIRY: date = date(2036, 12, 31)
BADGE_LABEL: str = "Heilbad 2026"


def badge_visible(today: date) -> bool:
    """Return True iff ``today`` falls within the Heilbad 2026..2036 window.

    The window is inclusive on both ends: the badge appears from the
    Reprädikatisierung date (2026-03-04) through 2036-12-31 and is hidden
    from 2037-01-01 onwards.
    """
    return HEILBAD_EFFECTIVE_FROM <= today <= HEILBAD_EXPIRY


def render_badge(today: date) -> str:
    """Return the badge label when the Heilbad predicate is visible, else ''.

    An empty string (rather than ``None``) keeps downstream ``str``-concat
    patterns safe.
    """
    return BADGE_LABEL if badge_visible(today) else ""