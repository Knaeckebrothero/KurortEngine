"""Google Wallet Generic pass serialiser for the Kurkarte digital Gästekarte.

Iter-21 AC-1 (Ubiquitous): renders a Google Wallet Generic pass object from
a :class:`kurort_engine.kurpaket_guest_card.KurpaketGuestCard` instance.

The Google Wallet Generic pass JSON is a different shape from the Apple PKPass
(see :mod:`kurort_engine.kurkarte_wallet.passkit`). It uses
``textModulesData`` for structured text rows (header / body) and exposes a
``classId`` reference to a server-side class definition. JWT signing is
deferred to the production wallet pipeline; tests use the placeholder
test-mode signing key in :func:`_sign_jwt_with_test_key`.

Iter-21 AC-2 (Event-driven): the 4-tier Kurbeitrag table is loaded from the
L4-004 SHIPPED ``kurort_engine.profiles.hessen_bad_orb.yaml`` Satzung
profile and serialised as ``textModulesData`` entries.

Iter-21 AC-3 (Event-driven): the "Heilbad 2026" badge is appended to the
``textModulesData`` collection iff ``today`` falls within the
04.03.2026..2036 Reprädikatisierung window
(``kurort_engine.heilbad_badge.badge_visible``).

Iter-21 AC-4 (Event-driven): the ``wallet_add_url`` discriminator returns
the platform-specific deep-link URL.

Pre-engagement: production requires a real Google Wallet API issuer account
+ JWT signing key. The placeholder signing key is documented as test-only.
"""
from __future__ import annotations

from datetime import date
from typing import Any

# ---------------------------------------------------------------------------
# Google Wallet issuer constants (Bad Orb Kurkarte)
# ---------------------------------------------------------------------------

ISSUER_NAME: str = "Hotel Rheinland Bad Orb"
ISSUER_ID: str = "3388000000022101111"  # PRODUCTION: replace with real Google Wallet issuer ID.
CLASS_ID: str = f"{ISSUER_ID}.kurkarte_bad_orb"


# ---------------------------------------------------------------------------
# Test-mode placeholder JWT signing key (PRODUCTION ROTATION POINT)
# ---------------------------------------------------------------------------
#
# Production rotation: replace this constant with the real Google Wallet API
# JWT signing key (OAuth 2.0 service account JSON). The signing function
# below exposes the rotation point so production callers can swap the key.
_TEST_JWT_SIGNING_KEY: bytes = b"kurkarte-wallet-google-test-mode-placeholder-key"


def _sign_jwt_with_test_key(payload: bytes, signing_key: bytes = _TEST_JWT_SIGNING_KEY) -> str:
    """Return an HMAC-SHA256 hex digest of ``payload`` under ``signing_key``.

    TEST-MODE placeholder. Production must replace with the real Google Wallet
    API RS256-signed JWT flow (``google-auth`` library + service-account JSON).
    """
    import hashlib
    import hmac

    return hmac.new(signing_key, payload, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# 4-tier Kurbeitrag table loader (L4-004 SHIPPED Satzung profile)
# ---------------------------------------------------------------------------

_KURBEITRAG_TABLE_HEADER: str = "Kurbeitrag"
_KURBEITRAG_TABLE_FOOTER: str = "EUR / Tag"


def _kurbeitrag_table_rows() -> list[dict[str, str]]:
    """Return 4 textModulesData rows for the L4-004 4-tier Kurbeitrag table.

    Iter-21 AC-2 (Event-driven): the table is loaded at runtime from the
    SHIPPED ``kurort_engine.profiles.hessen_bad_orb.yaml`` Satzung profile.
    No hardcoded literals in the pass serialisation (per spec.yaml A-2).
    """
    # Lazy import: the kurort_engine package's __init__ runs at import time;
    # using a local import keeps the google_wallet module importable even
    # during partial bootstrap.
    import kurort_engine
    from kurort_engine.rates import RateBand

    satzung = kurort_engine.load_profile("hessen", "bad_orb")
    rows: list[dict[str, str]] = []
    for band in satzung.bands:
        assert isinstance(band, RateBand), (
            f"Satzung bands must be RateBand instances; got {type(band).__name__}"
        )
        rows.append({
            "header": f"{_KURBEITRAG_TABLE_HEADER} — {band.name}",
            "body": f"{band.rate_per_day} {_KURBEITRAG_TABLE_FOOTER}",
        })
    return rows


def _heilbad_badge_row(today: date | None) -> dict[str, str] | None:
    """Return a textModulesData entry for the Heilbad 2026 badge, or None.

    Iter-21 AC-3 (Event-driven): the badge is included iff ``today`` falls
    within the 04.03.2026..2036 Reprädikatisierung window
    (``kurort_engine.heilbad_badge.badge_visible``). When ``today`` is None,
    ``date.today()`` is used as the default (per AC-3 EARS ambiguity rule).
    """
    from kurort_engine.heilbad_badge import BADGE_LABEL, badge_visible

    if today is None:
        today = date.today()
    if badge_visible(today):
        return {
            "header": "Prädikat",
            "body": BADGE_LABEL,
        }
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_google_pass_object(card: Any, today: date | None = None) -> dict[str, Any]:
    """Return a Google Wallet Generic pass object serialisation of ``card``.

    Parameters
    ----------
    card:
        A :class:`kurort_engine.kurpaket_guest_card.KurpaketGuestCard`
        instance (AC-7 SHIPPED iter-18).
    today:
        Optional date used to gate the Heilbad 2026 badge visibility
        (AC-3). If ``None``, ``date.today()`` is used.

    Returns
    -------
    dict
        A JSON-serialisable dict matching the Google Wallet Generic pass
        shape. Top-level keys include:

        * ``id`` (= ``card.booking_id``)
        * ``classId`` (``<ISSUER_ID>.kurkarte_bad_orb``)
        * ``issuerName`` (``Hotel Rheinland Bad Orb``)
        * ``cardTitle`` (= ``card.guest_name``)
        * ``header`` (= ``card.template_code``)
        * ``textModulesData`` (4-tier Kurbeitrag table + Heilbad badge if
          visible + booking_id/validity row)
        * ``hexBackgroundColor`` (default high-contrast charcoal)
    """
    fields = getattr(card, "__dict__", None) or vars(card)

    booking_id = str(fields.get("booking_id", ""))
    guest_name = str(fields.get("guest_name", ""))
    template_code = str(fields.get("template_code", "")).upper()

    text_modules: list[dict[str, str]] = list(_kurbeitrag_table_rows())

    badge_row = _heilbad_badge_row(today)
    if badge_row is not None:
        text_modules.append(badge_row)

    text_modules.append({
        "header": "Buchung",
        "body": booking_id,
    })

    return {
        "id": booking_id,
        "classId": CLASS_ID,
        "issuerName": ISSUER_NAME,
        "cardTitle": guest_name,
        "header": template_code,
        "hexBackgroundColor": "#3C414C",
        "textModulesData": text_modules,
    }


def wallet_add_url(platform: str, pass_id: str) -> str:
    """Return the deep-link URL for adding the pass to the given wallet platform.

    Iter-21 AC-4 (Event-driven): returns:

    * ``"apple"`` → ``passkit://1?passTypeIdentifier=pass.com.bad-orb.kurkarte&serialNumber=<pass_id>``
    * ``"google"`` → ``https://pay.google.com/gp/v/save/<pass_id>``

    Parameters
    ----------
    platform:
        Either ``"apple"`` or ``"google"``. Any other value raises ``ValueError``.
    pass_id:
        The serial number / booking ID to embed in the URL.

    Returns
    -------
    str
        The platform-specific deep-link URL.
    """
    if platform == "apple":
        return (
            "passkit://1?"
            f"passTypeIdentifier=pass.com.bad-orb.kurkarte&serialNumber={pass_id}"
        )
    if platform == "google":
        return f"https://pay.google.com/gp/v/save/{pass_id}"
    raise ValueError(
        f"wallet_add_url: unsupported platform {platform!r}; "
        "expected 'apple' or 'google'"
    )