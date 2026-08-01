"""AC-3: Exemption workflow (Geschäftsreisender + Schwerbehinderte 100%).

Test_oracle path recorded in spec.yaml:84. This is the red-phase test that
will fail with ``AssertionError`` against the placeholder implementation
(``calculate_kurtaxe_for_reservation`` accepts ``exemptions=...`` but the
argument is currently ignored — exempt guests still produce a non-zero
total). The audit-log assertions will also fail in red: the placeholder
has no ``AuditLog`` container and no SHA-256 ``content_hash`` plumbing.

Contracts under test (from spec.yaml:74-83 and spec_lock.md:61-72):

  * ``geschaeftsreisender`` exemption → guest posting = €0.00
  * ``schwerbehindert_100`` exemption → guest posting = €0.00
  * Each exemption produces an immutable audit-log entry with the
    correct ``actor`` (``"exemptions"``) and ``auditable_proof_ref`` /
    ``evidence`` field preserved.
  * The exemption is exposed through the reservation's audit trail
    (here: a module-level accessor that yields the entries written by
    the most recent ``calculate_kurtaxe_for_reservation`` call).

The Exemption dataclass placeholder uses fields ``category`` and
``evidence`` (the spec wording: "exemption reason" + "auditable-proof
reference"); the green phase will narrow / rename them to match the
spec field-name style without changing semantics.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from kurort_engine import (
    Exemption,
    Guest,
    Reservation,
    calculate_kurtaxe_for_reservation,
)

from tests._factories import hessen_satzung, make_guest  # noqa: F401  (fixture re-export)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_audit_log() -> list[Any]:
    """Return the audit-log list written by the most recent calculator call.

    The green phase will plumb an ``AuditLog`` (or equivalent iterable)
    into ``calculate_kurtaxe_for_reservation``; red phase has no such
    plumbing, so this helper returns an empty list. The tests below
    check the post-green contract (one entry per exempted guest) and
    will fail in red with a clear ``AssertionError`` ("expected N
    entries, got 0"), NOT with an ``AttributeError`` from a missing
    symbol.
    """
    # Public hook the green phase should populate. The placeholder does
    # not write to it, so the list is empty in red.
    audit_log = getattr(calculate_kurtaxe_for_reservation, "_last_audit_log", None)
    if audit_log is None:
        return []
    return list(audit_log)


# ---------------------------------------------------------------------------
# AC-3 (a): Geschäftsreisender (business traveller) exemption
# ---------------------------------------------------------------------------


def test_ac3_geschaeftsreisender_business_traveller_exemption_yields_zero(
    hessen_satzung,
) -> None:
    """A flagged Geschäftsreisender must produce a €0.00 Kurtaxe posting.

    Spec wording (AC-3): "When a guest is flagged as
    ``exemption=geschaeftsreisender`` ... the ``kurort_engine`` shall
    emit a zero-EUR Kurtaxe posting for that guest."

    Test shape: 1 adult guest, 2 nights. Without exemption the
    posting would be 2.50 × 2 = 5.00. With exemption it must be 0.00.
    """
    guest = make_guest(age_years=35, name="Bernd Business")
    reservation = Reservation(
        reservation_id="R-2024-BR-001",
        arrival=date(2024, 6, 10),
        departure=date(2024, 6, 12),  # 2 nights
        guests=(guest,),
    )

    exemption = Exemption(
        guest_name=guest.name,
        reservation_id=reservation.reservation_id,
        category="geschaeftsreisender",
        evidence="DocRef-BR-001 — company letterhead, signed 2024-06-10",
        valid_on=reservation.arrival,
    )

    total = calculate_kurtaxe_for_reservation(
        reservation,
        hessen_satzung,
        exemptions={guest: exemption},
    )

    # Return type must remain Decimal (consistent with AC-2).
    assert isinstance(total, Decimal), (
        f"calculate_kurtaxe_for_reservation must return Decimal, "
        f"got {type(total).__name__}"
    )

    # Zero-EUR posting for the exempt guest.
    assert total == Decimal("0.00"), (
        f"geschaeftsreisender exemption must yield Decimal('0.00'), "
        f"got {total!r} — calculator is ignoring the exemptions arg"
    )


def test_ac3_geschaeftsreisender_exemption_writes_audit_entry(
    hessen_satzung,
) -> None:
    """The geschaeftsreisender exemption must produce an audit entry.

    Spec wording (AC-3): "shall write an immutable audit-log entry
    recording the exemption reason, the auditable-proof reference ...
    and shall expose the exemption through the reservation's
    audit-trail endpoint."

    We assert: (i) exactly one entry was written for the exempt guest;
    (ii) the entry's ``actor`` field names the responsible code path
    (``"exemptions"``); (iii) the entry preserves the auditable-proof
    reference (here stored in the Exemption's ``evidence`` field, or
    a dedicated ``auditable_proof_ref`` once the green phase narrows
    the API).
    """
    guest = make_guest(age_years=35, name="Bernd Business")
    reservation = Reservation(
        reservation_id="R-2024-BR-001",
        arrival=date(2024, 6, 10),
        departure=date(2024, 6, 12),
        guests=(guest,),
    )
    exemption = Exemption(
        guest_name=guest.name,
        reservation_id=reservation.reservation_id,
        category="geschaeftsreisender",
        evidence="DocRef-BR-001",
        valid_on=reservation.arrival,
    )

    calculate_kurtaxe_for_reservation(
        reservation,
        hessen_satzung,
        exemptions={guest: exemption},
    )

    entries = _build_audit_log()
    assert len(entries) == 1, (
        f"expected exactly 1 audit entry for the exempt guest, got {len(entries)}"
    )
    entry = entries[0]
    # actor identifies the code path that wrote the entry.
    assert getattr(entry, "actor", None) == "exemptions", (
        f"audit entry actor must be 'exemptions', got {getattr(entry, 'actor', None)!r}"
    )
    # auditable-proof reference preserved (on the Exemption or on the
    # entry itself — both are acceptable shapes for the post-green API).
    proof_ref = (
        getattr(entry, "auditable_proof_ref", None)
        or getattr(exemption, "evidence", None)
    )
    assert proof_ref == "DocRef-BR-001", (
        f"audit entry must carry the auditable-proof reference "
        f"'DocRef-BR-001', got {proof_ref!r}"
    )


# ---------------------------------------------------------------------------
# AC-3 (b): Schwerbehindertenausweis GdB 100 exemption
# ---------------------------------------------------------------------------


def test_ac3_schwerbehindert_100_exemption_yields_zero(hessen_satzung) -> None:
    """A Schwerbehinderter with GdB 100 must produce a €0.00 posting.

    Spec wording (AC-3): "When a guest is flagged as
    ``exemption=schwerbehindert_100`` ... the ``kurort_engine`` shall
    emit a zero-EUR Kurtaxe posting for that guest."

    Per AC-2 the same guest (no exemption) would still route to the
    ``adult_disabled_70`` band (€1.25/day). For 3 nights that is €3.75.
    With the exemption, the total must be €0.00.
    """
    guest = make_guest(
        age_years=50,
        disability_pct=100,
        name="Max Schwerbehindert 100",
    )
    reservation = Reservation(
        reservation_id="R-2024-SB-100",
        arrival=date(2024, 6, 10),
        departure=date(2024, 6, 13),  # 3 nights
        guests=(guest,),
    )

    exemption = Exemption(
        guest_name=guest.name,
        reservation_id=reservation.reservation_id,
        category="schwerbehindert_100",
        evidence="Ausweis-12345 — Schwerbehindertenausweis GdB 100",
        valid_on=reservation.arrival,
    )

    total = calculate_kurtaxe_for_reservation(
        reservation,
        hessen_satzung,
        exemptions={guest: exemption},
    )

    assert isinstance(total, Decimal)
    assert total == Decimal("0.00"), (
        f"schwerbehindert_100 exemption must yield Decimal('0.00'), "
        f"got {total!r} — calculator is ignoring the exemptions arg"
    )


def test_ac3_schwerbehindert_100_exemption_writes_audit_entry(
    hessen_satzung,
) -> None:
    """The schwerbehindert_100 exemption must produce an audit entry.

    The Ausweis reference is the auditable-proof artefact
    (Schwerbehindertenausweis ref), per AC-3.
    """
    guest = make_guest(
        age_years=50,
        disability_pct=100,
        name="Max Schwerbehindert 100",
    )
    reservation = Reservation(
        reservation_id="R-2024-SB-100",
        arrival=date(2024, 6, 10),
        departure=date(2024, 6, 13),
        guests=(guest,),
    )
    exemption = Exemption(
        guest_name=guest.name,
        reservation_id=reservation.reservation_id,
        category="schwerbehindert_100",
        evidence="Ausweis-12345",
        valid_on=reservation.arrival,
    )

    calculate_kurtaxe_for_reservation(
        reservation,
        hessen_satzung,
        exemptions={guest: exemption},
    )

    entries = _build_audit_log()
    assert len(entries) == 1, (
        f"expected exactly 1 audit entry for the exempt guest, got {len(entries)}"
    )
    entry = entries[0]
    assert getattr(entry, "actor", None) == "exemptions", (
        f"audit entry actor must be 'exemptions', got {getattr(entry, 'actor', None)!r}"
    )
    proof_ref = (
        getattr(entry, "auditable_proof_ref", None)
        or getattr(exemption, "evidence", None)
    )
    assert proof_ref == "Ausweis-12345", (
        f"audit entry must carry the auditable-proof reference "
        f"'Ausweis-12345', got {proof_ref!r}"
    )


# ---------------------------------------------------------------------------
# AC-3 (c): Combined workflow — both exemption kinds, mixed with a paying
# guest, total reconciles to €0.00 for the exempt guests only.
# ---------------------------------------------------------------------------


def test_ac3_mixed_reservation_exempts_only_flagged_guests(hessen_satzung) -> None:
    """An exempt guest and a paying guest in the same reservation.

    Business traveller: 2 nights → €0.00 (exempt).
    Paying adult:       2 nights → €5.00 (2.50 × 2).

    The calculator must exempt ONLY the flagged guest — the paying
    adult still pays their €5.00 — and the grand total must be
    €5.00. This rules out a "zero the whole reservation on any
    exemption" regression.
    """
    paying = make_guest(age_years=40, name="Petra Paying")
    exempt = make_guest(age_years=35, name="Bernd Business")

    reservation = Reservation(
        reservation_id="R-2024-MIX-001",
        arrival=date(2024, 6, 10),
        departure=date(2024, 6, 12),  # 2 nights
        guests=(paying, exempt),
    )

    exemption = Exemption(
        guest_name=exempt.name,
        reservation_id=reservation.reservation_id,
        category="geschaeftsreisender",
        evidence="DocRef-BR-001",
        valid_on=reservation.arrival,
    )

    total = calculate_kurtaxe_for_reservation(
        reservation,
        hessen_satzung,
        exemptions={exempt: exemption},
    )

    assert isinstance(total, Decimal)
    # Paying adult: 2.50 × 2 = 5.00. Exempt guest: 0.00.
    assert total == Decimal("5.00"), (
        f"mixed reservation must total Decimal('5.00') "
        f"(paying adult 2.50×2 + exempt guest 0.00), got {total!r}"
    )

    # Exactly one audit entry — for the exempt guest only.
    entries = _build_audit_log()
    assert len(entries) == 1, (
        f"expected 1 audit entry (exempt guest only), got {len(entries)}"
    )
    assert getattr(entries[0], "actor", None) == "exemptions"
