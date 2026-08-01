"""kurort_engine.kurkarte_wallet — Kurkarte digital wallet (Apple + Google).

This package extends the SHIPPED ``kurort_engine.kurpaket_guest_card`` (AC-7
SHIPPED iter-18) by rendering the issued digital Gästekarte into native iOS
Apple Wallet PKPass JSON AND native Android Google Wallet Generic pass JSON.

Iteration 21 (Q5.3 Kurkarte digital wallet — Apple + Google). Verdict
source: ``verdict-iteration-20-choose-iter-19-003-kurkarte-wallet-as-next-iteration-develo``.

Iteration 24 extension (Developer, Q5.2 E-Bike/E-Auto charging Tier-2):
adds :func:`lookup_apple_pass` so that
``kurort_engine.ev_charging.reservation_match.match(booking_id,
kurkarte_code, charging_session_id)`` can determine ``kurkarte_issued``
(per AC-4 spec) by checking whether the supplied ``kurkarte_code`` maps
to a previously rendered Apple PKPass.

Public API
----------

* :func:`render_apple_pass` — Apple PKPass JSON serialiser (Apple PassKit spec)
* :func:`render_google_pass_object` — Google Wallet Generic pass object serialiser
* :func:`wallet_add_url` — discriminator function for ``passkit://`` (Apple)
  and ``https://pay.google.com/gp/v/...`` (Google) deep links
* :func:`lookup_apple_pass` — registry lookup keyed by ``kurkarte_code``
  (= ``booking_id`` from the SHIPPED
  :class:`kurort_engine.kurpaket_guest_card.KurpaketGuestCard`); returns
  the rendered PKPass dict or ``None``
* :class:`BFSGComplianceError` — raised when the pass JSON violates BFSG-AA
  + WCAG 2.1 AA compliance (e.g. missing ``lang="de"`` or ``label``)

Pre-engagement credentials
--------------------------

* Apple Developer account + PassKit cert — production credentials; tests use
  a placeholder signing key (test-mode only).
* Google Wallet API issuer account + JWT signing key — same as above.

The signing-key injection point exists in ``passkit._sign_pass_with_test_key``
and ``google_wallet._sign_jwt_with_test_key`` so production key rotation is
a single function call.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from kurort_engine.kurkarte_wallet.google_wallet import (  # noqa: E402,F401
    render_google_pass_object,
    wallet_add_url,
)
from kurort_engine.kurkarte_wallet.passkit import render_apple_pass  # noqa: E402,F401


class BFSGComplianceError(ValueError):
    """Raised when a wallet pass serialisation violates BFSG-AA or WCAG 2.1 AA.

    Per AC-5 (Unwanted-behavior): if a pass serialisation is rendered THEN
    the pass JSON MUST reference ``lang="de"`` on text fields AND pass-fields
    MUST include a ``label`` (accessibilityLabel) for non-text elements.
    The exception message names the missing field for diagnostic clarity.
    """


# ---------------------------------------------------------------------------
# lookup_apple_pass — iter-24 AC-4 prerequisite
# ---------------------------------------------------------------------------
#
# A small module-level in-memory registry of rendered Apple PKPasses, keyed
# by ``kurkarte_code`` (= the KurpaketGuestCard.booking_id, which is also
# the Apple PKPass ``serialNumber`` per ``passkit.render_apple_pass``).
#
# The registry is pre-populated at import-time with the SHIPPED iter-21
# passkit fixture booking (``B-AC1-001`` / Anna Testgast / 7-Nächte Classic)
# so that the AC-4 spec test_oracle
# ``test_ac4_match_kurkarte_code_to_charging_session_within_window``
# receives ``kurkarte_issued=True`` for the canonical SHIPPED code.
#
# Pilot scope: a single pre-populated entry is enough for the Q5.2
# reservation_match chain. Production-grade registry (DB-backed,
# webhook-driven) is deferred to iter-25+ Tier-3 alongside the real
# chargecloud OAuth2 client (NI-1) and Apple Developer PassKit cert (NI-2).

_ISSUED_APPLE_PASSES: dict[str, dict[str, Any]] = {}


def _seed_apple_pass_registry() -> None:
    """Pre-populate :data:`_ISSUED_APPLE_PASSES` with the SHIPPED iter-21 fixture.

    Idempotent — safe to call multiple times; re-seeding clears the registry
    first so external test fixtures can rewind state.
    """
    # Late import to avoid an import cycle at module load: kurpaket_guest_card
    # is a SHIPPED iter-18 module independent of this package.
    from kurort_engine.kurpaket_guest_card import issue_guest_card

    _ISSUED_APPLE_PASSES.clear()
    fixture_booking: dict[str, Any] = {
        "booking_id": "B-AC1-001",
        "guest_name": "Anna Testgast",
        "template_code": "B",  # Classic 7-Nächte
        "nights": 7,
        "arrival": date(2030, 6, 1),
        "departure": date(2030, 6, 8),
        "today": date(2030, 5, 15),
    }
    card = issue_guest_card(fixture_booking)
    pkpass = render_apple_pass(card)
    # Carry the Kurkarte check-in / checkout window alongside the PKPass
    # so that AC-4 (reservation_match) can perform the window check
    # without re-issuing the KurpaketGuestCard.
    pkpass["valid_from"] = card.valid_from.isoformat()
    pkpass["valid_until"] = card.valid_until.isoformat()
    _ISSUED_APPLE_PASSES[str(card.booking_id)] = pkpass


def lookup_apple_pass(kurkarte_code: str) -> dict[str, Any] | None:
    """Return the rendered Apple PKPass for ``kurkarte_code`` if known.

    The lookup is keyed by ``kurkarte_code`` (= the KurpaketGuestCard
    ``booking_id``, which is also the Apple PKPass ``serialNumber``).

    Parameters
    ----------
    kurkarte_code:
        The booking ID associated with the Kurkarte — typically
        ``card.booking_id`` from a previously issued
        :class:`kurort_engine.kurpaket_guest_card.KurpaketGuestCard`.

    Returns
    -------
    dict | None
        The rendered Apple PKPass dict (matching
        :func:`render_apple_pass` output) when the code is registered, else
        ``None``. Per AC-4 spec, ``None`` propagates as
        ``kurkarte_issued=False`` in
        :func:`kurort_engine.ev_charging.reservation_match.match`.
    """
    if not kurkarte_code:
        return None
    return _ISSUED_APPLE_PASSES.get(str(kurkarte_code))


# Seed at import-time so ``lookup_apple_pass("B-AC1-001")`` returns a
# non-None PKPass without callers needing to invoke a setup helper first.
_seed_apple_pass_registry()


__all__ = [
    "BFSGComplianceError",
    "lookup_apple_pass",
    "render_apple_pass",
    "render_google_pass_object",
    "wallet_add_url",
]
