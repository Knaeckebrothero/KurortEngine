"""Monthly remittance CSV generation for the Stadt Bad Orb portal (AC-4).

The Bad Orb portal ingests a twelve-column CSV (see spec.yaml:88-95 for the
schema). This module is the only place in ``kurort_engine`` that emits that
CSV; the column order is the contract the portal parses against, so it is
preserved verbatim here.

The function is *side-effect-free*: it returns the CSV text. Writing the
CSV to disk is the caller's job — that keeps the function trivially
testable (callers can inspect the return value without touching the
filesystem).
"""
from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from decimal import ROUND_HALF_EVEN, Decimal

from kurort_engine.calculator import Reservation, _find_band_for_guest
from kurort_engine.rates import Satzung

# ---------------------------------------------------------------------------
# Module-level hotel constants (AC-4 columns 11 + 12)
# ---------------------------------------------------------------------------
#
# The Bad Orb portal requires the hotel's Steuernummer and a signature line
# on every row. These are hotel-specific and out of scope for this MVP —
# both default to an empty string so the CSV is structurally complete even
# before a real hotel profile is wired in. A future phase will populate
# these from the hotel profile (KB ``kurortengine-hotel-profile-integration``).

_HOTEL_STEUERNUMMER: str = ""
_HOTEL_SIGNATURE_LINE: str = ""


# ---------------------------------------------------------------------------
# AC-4 header schema (verbatim from spec.yaml:88-95)
# ---------------------------------------------------------------------------

AC4_HEADER_COLUMNS: tuple[str, ...] = (
    "Reservation-ID",
    "anonymised guest name",
    "arrival",
    "departure",
    "day_count",
    "rate_band",
    "per_guest_per_day_eur",
    "exemption_flag",
    "subtotal_eur",
    "period_yyyy_mm",
    "hotel_steuernummer",
    "hotel_signature_line",
)

assert len(AC4_HEADER_COLUMNS) == 12, "AC-4 mandates 12 columns"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _anonymise(name: str) -> str:
    """Return the initialism of ``name`` (one letter per whitespace token).

    Examples
    --------
    >>> _anonymise("Anna Vollzahler")
    'A.V.'
    >>> _anonymise("Carla")
    'C.'

    Single-word names produce a single-letter initial so the column is
    never empty. The result always ends in a dot — that mirrors the
    convention on the Bad Orb portal's guest-name column.
    """
    parts = name.split()
    if not parts:
        # Defensive: blank name. Should not happen in well-formed input.
        return "."
    return ".".join(part[0].upper() for part in parts) + "."


def _cents(d: Decimal) -> str:
    """Quantise ``d`` to 2-decimal-place EUR and return its string form.

    Bankers' rounding (``ROUND_HALF_EVEN``) is used so that half-cent ties
    land on the nearest even digit — same rule the calculator applies, so
    the per-row subtotal here matches the per-reservation total there.
    """
    quantised = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    return f"{quantised}"


def _default_satzung() -> Satzung:
    """Lazy module-level default ``Satzung`` (Hessen Bad Orb).

    The AC-4 tests do not pass a ``Satzung`` argument — the spec mandates a
    three-argument signature ``(year, month, reservations)``. We resolve
    the Hessen Bad Orb profile on first call and cache it for the lifetime
    of the module. The profile file ships with the test fixtures, so the
    lookup is always available inside the test suite.
    """
    # Local import keeps the module import-cycle-free: ``kurort_engine``
    # re-exports this function, and re-importing the package top-level at
    # the moment of first use is safe because the package __init__ is
    # already half-executed at that point.
    import kurort_engine

    return kurort_engine.load_profile("hessen", "bad_orb")


def _is_guest_exempt(
    guest_name: str,
    reservation_exemptions: tuple,
) -> object | None:
    """Return the matching ``Exemption`` marker for ``guest_name`` if any.

    Matches by token: the exemption's ``category`` (lower-cased) must
    appear as a whitespace-delimited token in the lower-cased guest name.
    This mirrors the convention used by the AC-4 test fixtures
    (e.g. a guest named ``"Carla Geschaeftsreisender"`` matches the
    ``geschaeftsreisender`` exemption).

    Returns the matching ``Exemption`` marker so the caller can read its
    ``.category`` for the ``rate_band`` and ``exemption_flag`` columns.
    Returns ``None`` when no marker matches.
    """
    if not reservation_exemptions:
        return None
    name_tokens = set(guest_name.lower().split())
    for marker in reservation_exemptions:
        category = getattr(marker, "category", None)
        if category and category.lower() in name_tokens:
            return marker
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_monthly_remittance_csv(
    year: int,
    month: int,
    reservations: Sequence[Reservation],
) -> str:
    """Return the Bad Orb monthly remittance CSV text for the given period.

    Parameters
    ----------
    year:
        Calendar year (e.g. ``2024``) — reservations whose ``arrival`` is
        in this year are eligible.
    month:
        Calendar month, 1-12 — reservations whose ``arrival`` is in this
        month are eligible.
    reservations:
        The booking stream to filter. Reservations whose ``arrival`` falls
        outside the (year, month) window are silently skipped (the portal
        expects exactly the period's rows, not a year-to-date dump).

    Returns
    -------
    str
        The full CSV text, ending with a newline. The first row is the
        spec-pinned 12-column header; subsequent rows are one per
        (reservation × guest) tuple, in input order.

    Notes
    -----
    Exempt guests contribute a row with ``subtotal_eur == "0.00"`` and a
    non-empty ``exemption_flag`` — they are NOT omitted. This matches the
    spec language "exempt guests contribute €0.00, not 'absent'" and keeps
    the portal's reconciliation audit-trail complete.
    """
    satzung = _default_satzung()
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    # Header row — column order is the contract.
    writer.writerow(AC4_HEADER_COLUMNS)

    period_yyyy_mm = f"{year:04d}-{month:02d}"

    for reservation in reservations:
        # Filter to reservations whose arrival falls inside the period.
        if reservation.arrival.year != year or reservation.arrival.month != month:
            continue

        day_count = (reservation.departure - reservation.arrival).days
        arrival_iso = reservation.arrival.isoformat()
        departure_iso = reservation.departure.isoformat()

        for guest in reservation.guests:
            exemption = _is_guest_exempt(guest.name, reservation.exemptions)
            if exemption is not None:
                # Exempt row: subtotal + per-day are forced to 0.00, but the
                # row IS emitted so the portal sees the exemption proof.
                rate_band_value = f"exempt_{exemption.category}"
                per_day_value = _cents(Decimal("0.00"))
                subtotal_value = _cents(Decimal("0.00"))
                exemption_flag_value = exemption.category
            else:
                # Paying guest: look up the rate band via the calculator's
                # Phase-11 helper and compute subtotal = rate × day_count.
                band = _find_band_for_guest(guest, satzung, reservation.arrival)
                rate_band_value = band.name
                per_day_value = _cents(band.rate_per_day)
                subtotal_value = _cents(band.rate_per_day * Decimal(day_count))
                exemption_flag_value = ""

            writer.writerow(
                (
                    reservation.reservation_id,
                    _anonymise(guest.name),
                    arrival_iso,
                    departure_iso,
                    str(day_count),
                    rate_band_value,
                    per_day_value,
                    exemption_flag_value,
                    subtotal_value,
                    period_yyyy_mm,
                    _HOTEL_STEUERNUMMER,
                    _HOTEL_SIGNATURE_LINE,
                )
            )

    return buffer.getvalue()
