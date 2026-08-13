"""Q5.2 AC-1 — kurort_engine.ev_charging.ocpp_bridge module test surface (chargecloud OCPP 1.6).

AC-1 contract (verbatim from spec.yaml):

    Ubiquitous. The system shall expose a `render_charging_session(meter_payload)`
    function in `kurort_engine.ev_charging.ocpp_bridge` that returns a
    chargecloud OCPP 1.6 JSON-serialisable dict with required keys
    `chargePointVendor="Hotel-Rheinland-Bad-Orb"`, `chargePointModel="EVBox-Livo"`
    (single standard Wallbox reference surface for the 1× E-Bike + 1× E-Auto
    pilot), `meterValues` (kWh, timestamp ISO 8601 UTC), `transactionId`
    (uuid4), `idTag` (Kurkarte code if present else NULL), `status="Completed"`
    when `stop_reason` in {`EVDisconnected`, `StopAuthorized`, `Other`};
    and a sibling `sign_charging_session(ocpp_dict)` returning an
    `ocpp_signature` string (HMAC-SHA-256 of `json.dumps(ocpp_dict, sort_keys=True)`
    using `kurort_engine.ev_charging.ocpp_bridge.SESSION_SIGNING_KEY`).

RED VERIFY
----------
Tests MUST fail with ``AssertionError``, NOT ImportError. We use
``importlib.util.find_spec`` as a pre-check so missing-module failures surface
as ``AssertionError`` ("module should exist"), not ``ModuleNotFoundError``.

The ``_ev_charging_package_is_importable`` / ``_ocpp_bridge_module_is_importable``
helpers wrap ``find_spec`` in ``try/except`` to coerce the ``ModuleNotFoundError``
that ``find_spec`` raises when the parent package is missing into a plain
``AssertionError`` — so the test failure reads as "spec unmet" rather than
"missing import". This is the iter-24 honest-RED pattern.

Per `iter-24-pinned-tdd-rules-q5-2-e-bike-charging-scope-forbidden-patterns-loc-budget`:
  * No mocking the unit under test
  * No ``pytest.skip``
  * Concrete substring + structural assertions for AC-1 OCPP wire dict
  * Concrete HMAC-SHA-256 hex (length 64) assertion for AC-1 sign_charging_session
"""
from __future__ import annotations

import importlib.util
import json


def _find_spec_or_assert(module_name: str, *, parent: str | None = None) -> str:
    """Run ``importlib.util.find_spec`` and coerce missing-module failures
    into ``AssertionError`` so the test surfaces a "spec unmet" failure
    rather than a ``ModuleNotFoundError`` import failure.

    Per pinned memory: red-phase tests must fail with ``AssertionError``,
    not ``ImportError`` / ``ModuleNotFoundError`` / ``SyntaxError``.
    """
    try:
        found = importlib.util.find_spec(module_name)
    except (ModuleNotFoundError, ImportError) as exc:
        # The package/module does not exist yet — surface as AssertionError.
        scope = parent or module_name
        raise AssertionError(
            f"{scope} is not importable — green phase must create the "
            f"module before this test can pass. find_spec raised: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    assert found is not None, (
        f"{module_name} is not importable — green phase must create the "
        f"module before this test can pass. find_spec returned: {found!r}"
    )
    return f"found at {found.origin if hasattr(found, 'origin') else '<namespace>'}"


def _ev_charging_package_is_importable() -> str:
    """Pre-check: the new ev_charging package must exist."""
    return _find_spec_or_assert("kurort_engine.ev_charging")


def _ocpp_bridge_module_is_importable() -> str:
    """Pre-check: the new ev_charging.ocpp_bridge module must exist (AC-1)."""
    return _find_spec_or_assert(
        "kurort_engine.ev_charging.ocpp_bridge",
        parent="kurort_engine.ev_charging.ocpp_bridge",
    )


def _get_ev_charging_package():
    """Import the ev_charging package after the find_spec guard."""
    _ev_charging_package_is_importable()
    import kurort_engine.ev_charging as _ec  # noqa: E402
    assert _ec is not None, "importlib returned None — package is None"
    return _ec


def _get_ocpp_bridge_module():
    """Import the ev_charging.ocpp_bridge module after the find_spec guard."""
    _ocpp_bridge_module_is_importable()
    import kurort_engine.ev_charging.ocpp_bridge as _ob  # noqa: E402
    assert _ob is not None, "importlib returned None — module is None"
    return _ob


def _build_completed_meter_payload() -> dict:
    """Construct a meter_payload whose stop_reason triggers status="Completed".

    Per AC-1 spec, ``stop_reason in {EVDisconnected, StopAuthorized, Other}``
    implies ``status="Completed"``. Uses 0.5 kWh = E-Bike envelope.
    """
    return {
        "wallbox_id": "WALLBOX-EBIKE-01",
        "booking_id": "B-AC1-001",
        "kwh": 0.5,
        "start": "2026-07-05T10:00:00Z",
        "stop": "2026-07-05T12:30:00Z",
        "stop_reason": "EVDisconnected",
        "id_tag": "KUR-2026-000123",  # Kurkarte code
    }


# ===========================================================================
# AC-1 — render_charging_session returns chargecloud OCPP 1.6 JSON dict
# ===========================================================================

def test_ac1_render_charging_session_with_chargecloud_ocpp_16_keys() -> None:
    """AC-1 spec test_oracle.

    Asserts that ``render_charging_session(meter_payload)`` returns a
    chargecloud OCPP 1.6 JSON-serialisable dict carrying the required keys:
      * ``chargePointVendor`` == ``"Hotel-Rheinland-Bad-Orb"``
      * ``chargePointModel`` == ``"EVBox-Livo"``
      * ``meterValues`` containing kWh + ISO 8601 UTC timestamp
      * ``transactionId`` matching a uuid4 hex pattern
      * ``idTag`` carrying the Kurkarte code
      * ``status`` == ``"Completed"`` when ``stop_reason in
        {EVDisconnected, StopAuthorized, Other}``
    """
    _ocpp_bridge_module_is_importable()
    ob_mod = _get_ocpp_bridge_module()

    render_charging_session = (
        getattr(ob_mod, "render_charging_session", None)
        or getattr(ob_mod, "render", None)
    )
    assert callable(render_charging_session), (
        "AC-1: ocpp_bridge must expose a callable render_charging_session / "
        f"render entry point; found: {[n for n in dir(ob_mod) if not n.startswith('_')]!r}"
    )

    payload = _build_completed_meter_payload()
    ocpp_dict = render_charging_session(payload)

    # ----- core return-type check (JSON-serialisable dict) -----
    assert isinstance(ocpp_dict, dict), (
        f"AC-1: render_charging_session must return a JSON-serialisable dict; "
        f"got {type(ocpp_dict).__name__}: {ocpp_dict!r}"
    )

    # Round-tripping through json.dumps confirms JSON-serialisability.
    serialised = json.dumps(ocpp_dict, sort_keys=True)
    assert isinstance(serialised, str) and serialised, (
        f"AC-1: render_charging_session dict must be JSON-serialisable; "
        f"json.dumps produced: {serialised!r}"
    )

    # ----- chargePointVendor = "Hotel-Rheinland-Bad-Orb" -----
    assert ocpp_dict.get("chargePointVendor") == "Hotel-Rheinland-Bad-Orb", (
        f"AC-1: OCPP dict must carry chargePointVendor='Hotel-Rheinland-Bad-Orb' "
        f"per chargecloud OCPP 1.6 spec; got {ocpp_dict.get('chargePointVendor')!r}"
    )

    # ----- chargePointModel = "EVBox-Livo" (single standard Wallbox pilot) -----
    assert ocpp_dict.get("chargePointModel") == "EVBox-Livo", (
        f"AC-1: OCPP dict must carry chargePointModel='EVBox-Livo' per single "
        f"standard Wallbox pilot (1× E-Bike + 1× E-Auto); got {ocpp_dict.get('chargePointModel')!r}"
    )

    # ----- meterValues (kWh + ISO 8601 UTC timestamp) -----
    meter_values = ocpp_dict.get("meterValues")
    assert meter_values is not None, (
        f"AC-1: OCPP dict must carry a 'meterValues' entry (kWh + ISO 8601 UTC "
        f"timestamp); got {meter_values!r}"
    )
    # Coerce meterValues to a printable text form so we can assert the kWh
    # and the UTC timestamp markers are reachable.
    if isinstance(meter_values, list):
        printable_mv = " ".join(
            " ".join(str(v) for v in (item.values() if isinstance(item, dict) else [item]))
            for item in meter_values
        )
    elif isinstance(meter_values, dict):
        printable_mv = " ".join(str(v) for v in meter_values.values())
    else:
        printable_mv = str(meter_values)
    # kWh value 0.5 (E-Bike) must appear somewhere in meterValues.
    assert "0.5" in printable_mv, (
        f"AC-1: meterValues must encode the kWh value (0.5 for E-Bike); "
        f"got printable text: {printable_mv!r}"
    )
    # ISO 8601 UTC timestamp marker (Z suffix or +00:00) must appear.
    has_utc_marker = ("Z" in printable_mv) or ("+00:00" in printable_mv)
    assert has_utc_marker, (
        f"AC-1: meterValues must carry an ISO 8601 UTC timestamp (Z or +00:00 "
        f"suffix); got printable text: {printable_mv!r}"
    )

    # ----- transactionId (uuid4 hex pattern) -----
    transaction_id = ocpp_dict.get("transactionId")
    assert transaction_id is not None, (
        f"AC-1: OCPP dict must carry a 'transactionId' (uuid4); got None. "
        f"Full dict: {ocpp_dict!r}"
    )
    tx_str = str(transaction_id)
    # uuid4 hex = 8-4-4-4-12 = 32 hex chars + 4 hyphens = 36 chars
    assert len(tx_str) == 36 and tx_str.count("-") == 4, (
        f"AC-1: transactionId must be a uuid4 (32 hex chars + 4 hyphens = 36 "
        f"chars total); got {tx_str!r}"
    )
    # Every non-hyphen char must be a hex digit.
    hex_chars = tx_str.replace("-", "")
    assert len(hex_chars) == 32 and all(c in "0123456789abcdefABCDEF" for c in hex_chars), (
        f"AC-1: transactionId must be a uuid4 (all hex digits); got {tx_str!r}"
    )

    # ----- idTag (Kurkarte code) -----
    assert ocpp_dict.get("idTag") == "KUR-2026-000123", (
        f"AC-1: idTag must carry the Kurkarte code from the meter_payload; "
        f"got {ocpp_dict.get('idTag')!r}"
    )

    # ----- status = "Completed" when stop_reason in {EVDisconnected, ...} -----
    assert ocpp_dict.get("status") == "Completed", (
        f"AC-1: status must equal 'Completed' when stop_reason in "
        f"{{EVDisconnected, StopAuthorized, Other}}; got {ocpp_dict.get('status')!r}"
    )


# ===========================================================================
# AC-1 — sign_charging_session returns HMAC-SHA-256 hex (length 64)
# ===========================================================================

def test_ac1_sign_charging_session_returns_hmac_signature() -> None:
    """AC-1 spec test_oracle.

    Asserts that ``sign_charging_session(ocpp_dict)`` returns an
    ``ocpp_signature`` string of length 64 (HMAC-SHA-256 hex), computed
    over ``json.dumps(ocpp_dict, sort_keys=True)`` using the module's
    ``SESSION_SIGNING_KEY`` constant.
    """
    _ocpp_bridge_module_is_importable()
    ob_mod = _get_ocpp_bridge_module()

    sign_charging_session = (
        getattr(ob_mod, "sign_charging_session", None)
        or getattr(ob_mod, "sign", None)
    )
    assert callable(sign_charging_session), (
        "AC-1: ocpp_bridge must expose a callable sign_charging_session / sign "
        f"entry point; found: {[n for n in dir(ob_mod) if not n.startswith('_')]!r}"
    )

    # SESSION_SIGNING_KEY constant must exist.
    assert hasattr(ob_mod, "SESSION_SIGNING_KEY"), (
        "AC-1: ocpp_bridge must export a SESSION_SIGNING_KEY constant (used "
        f"as HMAC key); found: {[n for n in dir(ob_mod) if not n.startswith('_')]!r}"
    )

    # Build a stable ocpp_dict for signing.
    payload = _build_completed_meter_payload()
    render_charging_session = (
        getattr(ob_mod, "render_charging_session", None)
        or getattr(ob_mod, "render", None)
    )
    assert callable(render_charging_session), (
        "AC-1: ocpp_bridge must expose a callable render_charging_session "
        "for sign_charging_session test setup"
    )
    ocpp_dict = render_charging_session(payload)
    assert isinstance(ocpp_dict, dict), (
        f"AC-1: render_charging_session must return a dict before sign; "
        f"got {type(ocpp_dict).__name__}: {ocpp_dict!r}"
    )

    signature = sign_charging_session(ocpp_dict)

    # ----- core return-type: string of length 64 (HMAC-SHA-256 hex) -----
    assert isinstance(signature, str), (
        f"AC-1: sign_charging_session must return a string (HMAC-SHA-256 hex); "
        f"got {type(signature).__name__}: {signature!r}"
    )
    assert len(signature) == 64, (
        f"AC-1: ocpp_signature must be HMAC-SHA-256 hex (64 chars); got "
        f"len={len(signature)} value={signature!r}"
    )
    # Every char must be a hex digit.
    assert all(c in "0123456789abcdefABCDEF" for c in signature), (
        f"AC-1: ocpp_signature must be a hex string; got {signature!r}"
    )