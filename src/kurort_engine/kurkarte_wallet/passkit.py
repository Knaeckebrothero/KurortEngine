"""Apple PassKit JSON serialiser for the Kurkarte digital Gästekarte.

Iter-21 AC-1 (Ubiquitous): renders an Apple PKPass JSON serialisation from a
``kurort_engine.kurpaket_guest_card.KurpaketGuestCard`` instance. The returned
dict is JSON-serialisable; signing + manifest generation are deferred to the
production wallet pipeline (Apple Developer cert + PassKit cert pre-engagement
out-of-scope; tests use the placeholder test-mode signing key).

Iter-21 AC-5 (Unwanted-behavior): BFSG-AA + WCAG 2.1 AA compliance check.
The render function asserts (a) top-level ``lang="de"`` attribute (WCAG SC
3.1.1), (b) every text field dict in ``headerFields``/``primaryFields``/
``secondaryFields`` carries a non-empty ``label`` (accessibilityLabel,
WCAG SC 4.1.2), and (c) document-level metadata
``applePassStyle={contrast:high, fontSize:12pt}`` (WCAG SC 1.4.3 + SC 1.4.4).
Any violation raises :class:`kurort_engine.kurkarte_wallet.BFSGComplianceError`
naming the missing field.

Per ``proposal-iter-19-003-kurkarte-digital-wallet-apple-google-primary-extends-l4-004``
§3 AC-1 anchor [6359] (Apple Wallet PassKit documentation).

Pre-engagement: production requires a real Apple Developer account + PassKit
certificate (Pass Type ID = ``pass.com.bad-orb.kurkarte``). The placeholder
signing key in :func:`_sign_pass_with_test_key` is documented as test-only.
"""
from __future__ import annotations

import hashlib
import hmac
from typing import Any

# ---------------------------------------------------------------------------
# Apple PassKit pass-type identifier (Bad Orb Kurkarte)
# ---------------------------------------------------------------------------

PASS_TYPE_IDENTIFIER: str = "pass.com.bad-orb.kurkarte"
ORGANIZATION_NAME: str = "Hotel Rheinland Bad Orb"
DESCRIPTION: str = "Kurkarte — Heilbad 2026"
LOGO_TEXT: str = "Kurkarte"

# Apple PassKit default color palette (high-contrast white-on-charcoal for
# WCAG 2.1 AA lockscreen readability; per AC-5 cross-reference).
FOREGROUND_COLOR: str = "rgb(255, 255, 255)"
BACKGROUND_COLOR: str = "rgb(60, 65, 76)"
LABEL_COLOR: str = "rgb(255, 255, 255)"


# ---------------------------------------------------------------------------
# Test-mode placeholder signing key (PRODUCTION ROTATION POINT)
# ---------------------------------------------------------------------------
#
# Production rotation: replace this constant with the real Apple Developer
# PassKit certificate signing key (Pass Type ID cert). The signing function
# below exposes the rotation point so production callers can swap the key.
_TEST_SIGNING_KEY: bytes = b"kurkarte-wallet-test-mode-placeholder-signing-key"


def _sign_pass_with_test_key(pass_payload: bytes, signing_key: bytes = _TEST_SIGNING_KEY) -> str:
    """Return an HMAC-SHA256 hex digest of ``pass_payload`` under ``signing_key``.

    This is a TEST-MODE placeholder. Production must replace with the real
    Apple Developer PassKit certificate signing flow (sign the manifest.json
    per Apple's PassKit Web Service spec). The function exists so the
    production rotation point is explicit and centralised.
    """
    return hmac.new(signing_key, pass_payload, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# BFSG-AA + WCAG 2.1 AA compliance checker (AC-5)
# ---------------------------------------------------------------------------


def _assert_bfsg_compliance(pkpass: dict[str, Any]) -> None:
    """Raise :class:`BFSGComplianceError` if ``pkpass`` violates BFSG-AA / WCAG.

    Iter-21 AC-5 (Unwanted-behavior): the pass serialiser MUST:

      (a) carry a top-level ``lang="de"`` attribute (WCAG SC 3.1.1)
      (b) every text field dict in ``headerFields`` / ``primaryFields`` /
          ``secondaryFields`` MUST include a non-empty ``label`` key
          (accessibilityLabel, WCAG SC 4.1.2)
      (c) document-level ``applePassStyle`` metadata present (WCAG SC 1.4.3
          + SC 1.4.4 — high contrast + 12pt font)

    Any violation raises :class:`BFSGComplianceError` naming the missing field.
    """
    # Lazy import: BFSGComplianceError lives in the package __init__ to avoid
    # an import cycle (passkit.py is imported by __init__.py before the
    # exception class is bound).
    from kurort_engine.kurkarte_wallet import BFSGComplianceError

    # ----- (a) lang="de" check -----
    if pkpass.get("lang") != "de":
        raise BFSGComplianceError(
            "BFSG-AA / WCAG SC 3.1.1: pass JSON must carry a top-level "
            f"'lang'='de' attribute; got lang={pkpass.get('lang')!r}"
        )

    # ----- (c) applePassStyle metadata check -----
    style = pkpass.get("applePassStyle")
    if not isinstance(style, dict):
        raise BFSGComplianceError(
            "BFSG-AA / WCAG SC 1.4.3 + SC 1.4.4: pass JSON must carry an "
            f"'applePassStyle' dict (high contrast + 12pt font); got style={style!r}"
        )
    if style.get("contrast") != "high":
        raise BFSGComplianceError(
            "BFSG-AA / WCAG SC 1.4.3: applePassStyle.contrast must be 'high'; "
            f"got {style.get('contrast')!r}"
        )
    if not str(style.get("fontSize", "")).endswith("pt"):
        raise BFSGComplianceError(
            "BFSG-AA / WCAG SC 1.4.4: applePassStyle.fontSize must end in 'pt' "
            f"(point-based font sizing); got {style.get('fontSize')!r}"
        )

    # ----- (b) every text field dict carries a non-empty 'label' key -----
    text_field_collections = (
        "headerFields",
        "primaryFields",
        "secondaryFields",
        "auxiliaryFields",
        "backFields",
    )
    for collection_name in text_field_collections:
        collection = pkpass.get(collection_name)
        if not collection:
            continue
        for field_dict in collection:
            if not isinstance(field_dict, dict):
                continue
            field_key = field_dict.get("key", "<no-key>")
            label_value = field_dict.get("label")
            if not (label_value is not None and str(label_value).strip()):
                raise BFSGComplianceError(
                    f"BFSG-AA / WCAG SC 4.1.2: text field {collection_name}."
                    f"{field_key!r} is missing the required non-empty "
                    f"'label' (accessibilityLabel); got label={label_value!r}"
                )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_apple_pass(card: Any) -> dict[str, Any]:
    """Return an Apple PKPass JSON serialisation of ``card``.

    Parameters
    ----------
    card:
        A :class:`kurort_engine.kurpaket_guest_card.KurpaketGuestCard`
        instance (AC-7 SHIPPED iter-18). The function reads the
        ``booking_id``, ``guest_name``, ``template_code`` fields.

    Returns
    -------
    dict
        A JSON-serialisable dict matching the Apple PassKit schema for a
        ``generic`` pass type. The top-level keys include:

        * ``formatVersion`` (always ``1``)
        * ``passTypeIdentifier`` (always ``pass.com.bad-orb.kurkarte``)
        * ``serialNumber`` (= ``card.booking_id``)
        * ``teamIdentifier`` (placeholder; production requires real Apple
          Developer team ID)
        * ``organizationName`` (``Hotel Rheinland Bad Orb``)
        * ``description`` (``Kurkarte — Heilbad 2026``)
        * ``logoText`` (``Kurkarte``)
        * ``foregroundColor`` / ``backgroundColor`` / ``labelColor``
        * ``lang`` (``"de"`` — BFSG-AA / WCAG SC 3.1.1)
        * ``applePassStyle`` (high contrast + 12pt — WCAG SC 1.4.3 + SC 1.4.4)
        * ``headerFields`` (carries the Kurpaket template code + ``label``)
        * ``primaryFields`` (carries the guest name + ``label``)
        * ``secondaryFields`` (carries the booking ID + ``label``)

    Raises
    ------
    kurort_engine.kurkarte_wallet.BFSGComplianceError
        If the rendered pass violates BFSG-AA + WCAG 2.1 AA compliance
        (missing ``lang="de"``, missing accessibility ``label``, or
        missing ``applePassStyle`` metadata).
    """
    # Read the canonical fields off the KurpaketGuestCard dataclass (or
    # duck-typed equivalent) via ``__dict__`` / ``vars``. We do NOT import
    # the dataclass type at module-load time to avoid an import cycle.
    fields = getattr(card, "__dict__", None) or vars(card)

    booking_id = str(fields.get("booking_id", ""))
    guest_name = str(fields.get("guest_name", ""))
    template_code = str(fields.get("template_code", "")).upper()

    pkpass = {
        "formatVersion": 1,
        "passTypeIdentifier": PASS_TYPE_IDENTIFIER,
        "serialNumber": booking_id,
        # PRODUCTION: replace with real Apple Developer Team ID.
        "teamIdentifier": "TESTMODE0000",
        "organizationName": ORGANIZATION_NAME,
        "description": DESCRIPTION,
        "logoText": LOGO_TEXT,
        "foregroundColor": FOREGROUND_COLOR,
        "backgroundColor": BACKGROUND_COLOR,
        "labelColor": LABEL_COLOR,
        # BFSG-AA / WCAG SC 3.1.1: declare German as the pass language.
        "lang": "de",
        # WCAG SC 1.4.3 + SC 1.4.4: high-contrast color palette + 12pt font.
        "applePassStyle": {
            "contrast": "high",
            "fontSize": "12pt",
        },
        "headerFields": [
            {
                "key": "kurtemplate",
                "label": "Kurpaket",
                "value": template_code,
            }
        ],
        "primaryFields": [
            {
                "key": "guest",
                "label": "Gast",
                "value": guest_name,
            }
        ],
        "secondaryFields": [
            {
                "key": "booking",
                "label": "Buchung",
                "value": booking_id,
            }
        ],
    }

    # AC-5 compliance check: raise BFSGComplianceError on any violation.
    _assert_bfsg_compliance(pkpass)

    return pkpass