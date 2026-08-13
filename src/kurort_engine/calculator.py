"""Reservation / Guest domain model and the calculate_kurtaxe entry point."""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal

from kurort_engine.audit import AuditEntry
from kurort_engine.exemptions import Exemption, is_exempt
from kurort_engine.rates import RateBand, Satzung


@dataclass(frozen=True)
class Guest:
    """A single overnight guest (one stay, one Kurtaxe row)."""

    name: str
    birth_date: date
    nationality: str
    disability_pct: int | None = None


@dataclass(frozen=True)
class Reservation:
    """A booking span with one or more guests.

    exemptions carries reservation-scope exemption markers (one per
    recognised category that applies to any guest on this booking). The
    reporting layer (AC-4) matches these markers to individual guests by
    name token. The calculator's per-call exemptions mapping (passed
    to :func:`calculate_kurtaxe_for_reservation`) is the auditable-proof
    pathway (AC-3) and is a separate input.
    """

    reservation_id: str
    arrival: date
    departure: date
    guests: tuple[Guest, ...] = field(default_factory=tuple)
    exemptions: tuple[Exemption, ...] = field(default_factory=tuple)


def _age_at(guest: Guest, anchor: date) -> int:
    """Return the guest's integer age on ``anchor``.

    Walks the year boundary manually so callers do not need
    ``python-dateutil.relativedelta``; subtracts one when the anchor's
    month/day precedes the guest's birthday in the anchor year.
    """
    age = anchor.year - guest.birth_date.year - (
        1 if (anchor.month, anchor.day) < (guest.birth_date.month, guest.birth_date.day) else 0
    )
    return age


def _band_disability_matches(band: RateBand, guest: Guest) -> bool:
    """True if ``band`` is open to ``guest`` on the disability axis.

    A band whose ``disability_pct_min`` equals the no-bound sentinel
    (0) is open to every guest, with or without a recorded disability.
    A band with a positive threshold is open only to a guest whose
    recorded ``disability_pct`` is at least that threshold — a guest
    with no recorded disability does NOT qualify for a Schwerbehindert
    band.
    """
    if band.disability_pct_min == 0:
        return True
    return guest.disability_pct is not None and band.disability_pct_min <= guest.disability_pct


def _find_band_for_guest(guest: Guest, satzung: Satzung, arrival: date) -> RateBand:
    """Return the ``RateBand`` that applies to the guest at ``arrival``.

    Match rule (GdB 100 upper-bound policy):

    * ``band.min_age <= age <= band.max_age`` — age window
    * ``_band_disability_matches(band, guest)`` — a no-bound band
      (``disability_pct_min == 0``) is open to every guest; a band
      with a positive threshold only to a recorded Schwerbehinderter.
      The upper bound ``disability_pct_max`` is intentionally NOT
      checked: the Hessen YAML uses 99 as a soft ceiling that must
      still admit a Schwerbehinderter with GdB = 100.
    * among bands that pass the age + disability window, the band with
      the **highest** ``disability_pct_min`` wins. This makes a
      Schwerbehinderter-specific band (e.g. ``adult_disabled_70``,
      dis_min=70) override the corresponding generic band
      (``adult``, dis_min=0) when the guest qualifies for both — the
      natural reading of the Bad Orb Satzung's "ab GdB 70" wording.

    Raises ``ValueError`` if no band matches — fail loud, never silent
    zero. The exemption workflow (AC-3) is the correct place to zero
    out a posting, not the band matcher.
    """
    age = _age_at(guest, arrival)
    candidates: list[RateBand] = [
        band
        for band in satzung.bands
        if band.min_age <= age <= band.max_age
        and _band_disability_matches(band, guest)
    ]
    if not candidates:
        raise ValueError(
            f"no RateBand matches age={age} disability_pct={guest.disability_pct} "
            f"for satzung {satzung.bundesland}/{satzung.kurort}"
        )
    return max(candidates, key=lambda band: band.disability_pct_min)


# ---------------------------------------------------------------------------
# Audit-log accessor for AC-3 (exemption workflow)
# ---------------------------------------------------------------------------
#
# The AC-3 tests read the audit log written by the most recent call to
# ``calculate_kurtaxe_for_reservation`` via the duck-typed hook
# ``calculate_kurtaxe_for_reservation._last_audit_log``. We expose the
# module-level singleton through a function attribute so that:
#
#   * the singleton can be inspected and asserted on by tests;
#   * the public ``get_audit_log()`` helper returns a snapshot copy of
#     the entries (callers cannot mutate the audit chain in place);
#   * the log is reset at the start of every ``calculate_kurtaxe_for_reservation``
#     call, so test isolation is automatic (the next call starts from
#     a clean log).
_audit_log: list[AuditEntry] = []


def get_audit_log() -> list[AuditEntry]:
    """Return a snapshot copy of the audit-log entries from the last call.

    Returns a fresh list each time so callers cannot mutate the audit
    chain in place. To read the live list (used by the AC-3 tests'
    duck-typed accessor), read the function attribute
    ``calculate_kurtaxe_for_reservation._last_audit_log`` directly.
    """
    return list(_audit_log)


def _reset_audit_log() -> None:
    """Clear the module-level audit log (test-isolation helper)."""
    _audit_log.clear()


def _record_exemption_audit(
    *,
    guest: Guest,
    exemption: Exemption,
    reservation_id: str,
) -> None:
    """Append one ``AuditEntry`` to the module-level log for an exempt guest.

    The payload is the canonical-JSON form of
    ``{guest_name, reservation_id, category, evidence}`` — same shape
    the SHA-256 hash in AC-7 expects — so the entry is serialisable
    and verifiable end-to-end.
    """
    payload = json.dumps(
        {
            "guest_name": guest.name,
            "reservation_id": reservation_id,
            "category": exemption.category,
            "evidence": exemption.evidence,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    entry = AuditEntry(actor="exemptions", payload=payload)
    _audit_log.append(entry)


def calculate_kurtaxe_for_reservation(
    reservation: Reservation,
    satzung: Satzung,
    exemptions: Mapping[Guest, Exemption] | None = None,
) -> Decimal:
    """Return the total Kurtaxe for ``reservation`` under ``satzung``.

    Sums ``band.rate_per_day * day_count`` across every paying guest,
    then quantises to cents with bankers' rounding (``ROUND_HALF_EVEN``).
    A guest present as a key in ``exemptions`` whose ``Exemption`` is
    in a recognised category (see :func:`kurort_engine.exemptions.is_exempt`)
    contributes ``Decimal("0.00")`` and emits an immutable
    :class:`~kurort_engine.audit.AuditEntry` to the module-level
    audit log (exposed via :func:`get_audit_log` and via the
    function attribute ``calculate_kurtaxe_for_reservation._last_audit_log``).

    The log is reset at the start of every call so test isolation is
    automatic: each call starts from a clean log and finishes with a
    log that records exactly the exemptions applied in that call.
    """
    _reset_audit_log()
    # Expose the live list via a function attribute for the duck-typed
    # test accessor. Tests call
    #   getattr(calculate_kurtaxe_for_reservation, "_last_audit_log", None)
    # and use ``list(...)`` on the result, so a plain list is fine.
    calculate_kurtaxe_for_reservation._last_audit_log = _audit_log  # type: ignore[attr-defined]

    day_count = (reservation.departure - reservation.arrival).days
    total = Decimal("0.00")
    exemption_map: dict[Guest, Exemption] = dict(exemptions or {})
    for guest in reservation.guests:
        exemption = exemption_map.get(guest)
        if exemption is not None and is_exempt(exemption):
            _record_exemption_audit(
                guest=guest,
                exemption=exemption,
                reservation_id=reservation.reservation_id,
            )
            continue
        band = _find_band_for_guest(guest, satzung, reservation.arrival)
        total += band.rate_per_day * Decimal(day_count)
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)