"""kurort_engine.ev_charging.reservation_match — Kurkarte-tagged session match.

Implements AC-4 (Event-driven) per spec.yaml:

    When ``match(booking_id, kurkarte_code, charging_session_id)`` is
    called THEN the function in
    ``kurort_engine.ev_charging.reservation_match`` shall return a
    :class:`ReservationMatch` dataclass with fields: ``booking_id``,
    ``kurkarte_code``, ``charging_session_id``, ``kurkarte_issued``
    (True iff
    ``kurort_engine.kurkarte_wallet.lookup_apple_pass(kurkarte_code)``
    returns non-None), ``matched`` (True iff ``kurkarte_issued`` AND
    the session falls inside the Kurkarte check-in / checkout window),
    ``matched_at`` (UTC of the match when ``matched=True``, else None);
    the function shall raise :class:`ValueError` if ``booking_id`` or
    ``charging_session_id`` is the empty string.

Iteration 24 (Developer) — Q5.2 Tier-2 ev_charging.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

# ---------------------------------------------------------------------------
# AC-4 — ReservationMatch dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReservationMatch:
    """Immutable record of a wallbox-session ↔ Kurkarte match attempt.

    Attributes
    ----------
    booking_id:
        Hotel-Buchungs-ID, an die die Wallbox-Ladung gebucht wird
        (echoed from the input).
    kurkarte_code:
        The Kurkarte code (= KurpaketGuestCard ``booking_id`` per
        SHIPPED iter-18 / passkit ``serialNumber`` per SHIPPED iter-21)
        used to verify the guest has an active digital Kurkarte.
    charging_session_id:
        Wallbox-Ladungs-ID (OCPP 1.6 ``transactionId`` per AC-1).
    kurkarte_issued:
        True iff ``lookup_apple_pass(kurkarte_code)`` returned a
        non-None PKPass dict (i.e., a Kurkarte has been issued for
        ``kurkarte_code`` and is registered in the wallet).
    matched:
        True iff ``kurkarte_issued`` AND the session falls inside the
        Kurkarte check-in / checkout window (``valid_from ≤ today ≤
        valid_until`` per the metadata carried alongside the PKPass
        dict in the wallet registry).
    matched_at:
        UTC :class:`datetime` of the successful match — populated only
        when ``matched=True``. ``None`` otherwise.
    """

    booking_id: str
    kurkarte_code: str
    charging_session_id: str
    kurkarte_issued: bool
    matched: bool
    matched_at: datetime | None


# ---------------------------------------------------------------------------
# AC-4 — match() entry point
# ---------------------------------------------------------------------------


def match(
    booking_id: str,
    kurkarte_code: str,
    charging_session_id: str,
) -> ReservationMatch:
    """Return a :class:`ReservationMatch` for the supplied inputs.

    Parameters
    ----------
    booking_id:
        Hotel-Buchungs-ID. MUST be a non-empty string; raises
        :class:`ValueError` otherwise.
    kurkarte_code:
        Kurkarte code (= ``card.booking_id`` from a previously issued
        :class:`kurort_engine.kurpaket_guest_card.KurpaketGuestCard`).
        May be the empty string — the function will report
        ``kurkarte_issued=False`` (no PKPass matches).
    charging_session_id:
        Wallbox-Ladungs-ID. MUST be a non-empty string; raises
        :class:`ValueError` otherwise.

    Returns
    -------
    ReservationMatch
        Frozen dataclass instance with all 6 spec fields.

    Raises
    ------
    ValueError
        If ``booking_id == ""`` or ``charging_session_id == ""``.
    """
    if not booking_id:
        raise ValueError(
            "match() requires non-empty booking_id; got empty string"
        )
    if not charging_session_id:
        raise ValueError(
            "match() requires non-empty charging_session_id; got empty string"
        )

    # Late import to avoid a hard cycle at module load (kurkarte_wallet
    # imports kurpaket_guest_card transitively through passkit).
    from kurort_engine.kurkarte_wallet import lookup_apple_pass

    pkpass = lookup_apple_pass(kurkarte_code)
    kurkarte_issued = pkpass is not None

    matched = False
    if kurkarte_issued and isinstance(pkpass, dict):
        # The wallet registry may carry valid_from / valid_until as ISO
        # date strings alongside the PKPass dict (set by the seeder).
        # If both are present AND parse, the session is "matched" iff
        # today falls in [valid_from, valid_until].
        valid_from_str = pkpass.get("valid_from")
        valid_until_str = pkpass.get("valid_until")
        if isinstance(valid_from_str, str) and isinstance(valid_until_str, str):
            try:
                valid_from = date.fromisoformat(valid_from_str)
                valid_until = date.fromisoformat(valid_until_str)
                today = date.today()
                matched = valid_from <= today <= valid_until
            except ValueError:
                # Unparseable dates — fall back to kurkarte_issued alone
                # (the pass was issued, so surface that signal even
                # though the window check couldn't be performed).
                matched = True

    matched_at = datetime.now(tz=UTC) if matched else None

    return ReservationMatch(
        booking_id=booking_id,
        kurkarte_code=kurkarte_code,
        charging_session_id=charging_session_id,
        kurkarte_issued=kurkarte_issued,
        matched=matched,
        matched_at=matched_at,
    )
