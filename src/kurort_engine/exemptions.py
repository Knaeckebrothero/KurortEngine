"""Exemption categories and exemption-row construction (AC-3).

An ``Exemption`` records the auditable proof that a particular guest
qualifies for a Kurtaxe exemption on a particular day. The two
categories the kurort_engine currently honours are:

* ``geschaeftsreisender`` — business traveller; per Hessen KAG the
  Kurtaxe is waived when the stay is shown to be business-motivated
  (employer's letter on company letterhead is the typical evidence).
* ``schwerbehindert_100`` — Schwerbehinderter with Grad der
  Behinderung (GdB) of 100; the Schwerbehindertenausweis reference is
  the auditable proof.

The ``is_exempt`` pure function classifies an ``Exemption`` row so the
calculator can decide whether to zero a guest's posting. Anything not
in the recognised set is treated as NOT exempt (fail-closed: an
unrecognised category does NOT silently waive Kurtaxe).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# Recognised exemption categories. Frozen-set so it can be shared across
# threads and so ``is_exempt`` can do an O(1) membership check.
_RECOGNISED_CATEGORIES: frozenset[str] = frozenset(
    {"geschaeftsreisender", "schwerbehindert_100"}
)


@dataclass(frozen=True)
class Exemption:
    """A documented exemption for one guest-day row.

    ``guest_name`` and ``reservation_id`` identify the row; ``category``
    names the exemption reason; ``evidence`` is the auditable-proof
    reference (a letterhead reference for Geschäftsreisende, the
    Schwerbehindertenausweis reference for GdB-100 guests); ``valid_on``
    is the calendar day on which the exemption applies.
    """

    guest_name: str
    reservation_id: str
    category: str
    evidence: str
    valid_on: date


# ---------------------------------------------------------------------------
# Class-level convenience constants (AC-4 reporting layer)
# ---------------------------------------------------------------------------
#
# The AC-4 reporting tests construct Reservation(exemptions=(Exemption.geschaeftsreisender,))
# — they need to reference a category marker by name, not construct a full
# Exemption with five required fields. We expose a class-level constant
# for each recognised category. The sentinel values for guest_name,
# reservation_id, evidence and valid_on are placeholders; only
# .category is consumed by the reporting layer.
#
# These constants are appended AFTER the dataclass body so they live on the
# class itself (not on instances) and survive the ``@dataclass(frozen=True)``
# constructor.

Exemption.geschaeftsreisender = Exemption(
    guest_name="",
    reservation_id="",
    category="geschaeftsreisender",
    evidence="",
    valid_on=date(1970, 1, 1),
)
Exemption.schwerbehindert_100 = Exemption(
    guest_name="",
    reservation_id="",
    category="schwerbehindert_100",
    evidence="",
    valid_on=date(1970, 1, 1),
)


def is_exempt(exemption: Exemption) -> bool:
    """Return ``True`` iff ``exemption`` is in a recognised exemption category.

    Fail-closed: any category not in :data:`_RECOGNISED_CATEGORIES`
    returns ``False``. The calculator relies on this so an unrecognised
    string in a row does NOT silently waive Kurtaxe.
    """
    return exemption.category in _RECOGNISED_CATEGORIES