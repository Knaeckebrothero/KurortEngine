"""AC-5 — BFSG-AA + WCAG 2.1 AA accessibility compliance for InvoiceLineItem.

Iter-24 Phase 8 tactical RED. Q5.2 ev_charging submodule.

Spec contract (kurort_engine/spec.yaml AC-5):

    Unwanted-behavior. If the invoice line item is rendered THEN the line
    item JSON MUST reference ``lang="de"`` on text fields AND ``label``
    (accessibilityLabel) for the non-text ``unit`` and ``quantity`` fields
    per BFSG-AA + WCAG 2.1 AA guidance (screen-reader text contrast ≥ 4.5:1,
    font sizing ≥ 12pt — values declared as document-level metadata
    ``formatVersion`` + ``badOrbInvoiceStyle``); if ``lang`` or ``label``
    are absent, the invoice line item builder MUST raise
    ``BFSGComplianceError`` naming the missing field.

    test_oracle: repo/tests/test_ev_charging_bfsg_compliance.py::
                 test_ac5_invoice_line_item_enforces_lang_de_and_accessibility_labels

Total spend / total cost USt (MWhStG / §14 UStG Pflichtangaben for
Wallbox-Strom at 19 % standard rate per §12 UStG). Reverse-charge placeholder
= "Nein" in pilot (B2C hotel guest charging).

This is the RED-phase test_oracle: it verifies the spec contract via the
``InvoiceLineItem`` dataclass export, ``append_to_folio`` entry point of
the SHIPPED (Phase 7 green) ``kurort_engine.ev_charging.invoice_line_item``
submodule, and the NEW ``validate_bfsg_compliance(line_item_dict)`` helper
that MUST be added in green phase. The test must FAIL with
``AssertionError`` (not import error) in RED phase because:

  1. ``validate_bfsg_compliance`` does not yet exist on
     ``kurort_engine.ev_charging.invoice_line_item`` (RED guard fires).
  2. ``InvoiceLineItem.to_dict()`` does not yet emit ``lang="de"`` /
     ``label`` keys / document-level metadata (RED assertion fails).

Pattern reference: SHIPPED iter-21
``kurort_engine.kurkarte_wallet.passkit._assert_bfsg_compliance`` (line 73)
+ ``kurort_engine.kurkarte_wallet.passkit.render_apple_pass`` (line 147)
for the BFSG-AA + WCAG 2.1 AA validation style replicated here.
"""
from __future__ import annotations

import importlib.util
import inspect
from datetime import datetime, timezone
from decimal import Decimal


# ---------------------------------------------------------------------------
# Helpers (replicate the SHIPPED iter-21 kurkarte_wallet pattern of
# ``_xxx_module_is_importable`` find_spec guards so that the failure mode
# in RED is a clean AssertionError about the missing submodule / helper, not
# a raw ImportError that pretends the test is collected).
# ---------------------------------------------------------------------------


def _invoice_line_item_module_is_importable() -> str:
    """Pre-check: ``kurort_engine.ev_charging.invoice_line_item`` must exist.

    Returns a diagnostic string. Raises ``AssertionError`` if missing.
    """
    found = importlib.util.find_spec(
        "kurort_engine.ev_charging.invoice_line_item"
    )
    assert found is not None, (
        "kurort_engine.ev_charging.invoice_line_item is not importable — "
        "green phase must create "
        "repo/src/kurort_engine/ev_charging/invoice_line_item.py before this "
        f"test can pass. find_spec returned: {found!r}"
    )
    return f"found at {found.origin if hasattr(found, 'origin') else '<namespace>'}"


def _bfsg_compliance_error_is_importable() -> str:
    """Pre-check: ``BFSGComplianceError`` must be importable from the
    ``kurort_engine.ev_charging`` package (SHIPPED Phase 5 as stub).
    """
    spec = importlib.util.find_spec("kurort_engine.ev_charging")
    assert spec is not None, (
        "kurort_engine.ev_charging is not importable — Phase 5 ship "
        f"regressed. find_spec returned: {spec!r}"
    )
    import kurort_engine.ev_charging as _ev_charging  # noqa: E402
    BFSGComplianceError = getattr(_ev_charging, "BFSGComplianceError", None)
    assert BFSGComplianceError is not None, (
        "kurort_engine.ev_charging must export BFSGComplianceError "
        "(SHIPPED Phase 5 as stub) before AC-5 tests can pass; got "
        f"attributes={[n for n in dir(_ev_charging) if not n.startswith('_')]!r}"
    )
    return f"BFSGComplianceError={BFSGComplianceError!r}"


def _validate_bfsg_compliance_helper_is_callable() -> str:
    """Pre-check: ``validate_bfsg_compliance`` must be a callable helper on
    ``kurort_engine.ev_charging.invoice_line_item`` (green phase MUST add it).
    """
    _invoice_line_item_module_is_importable()
    import kurort_engine.ev_charging.invoice_line_item as _ili  # noqa: E402
    helper = getattr(_ili, "validate_bfsg_compliance", None)
    assert callable(helper), (
        "kurort_engine.ev_charging.invoice_line_item must expose a callable "
        "validate_bfsg_compliance(line_item_dict) helper per AC-5 spec; got "
        f"attributes={[n for n in dir(_ili) if not n.startswith('_')]!r}"
    )
    return f"validate_bfsg_compliance={helper!r}"


def _get_invoice_line_item_module():
    """Import the invoice_line_item module after the find_spec guard."""
    _invoice_line_item_module_is_importable()
    import kurort_engine.ev_charging.invoice_line_item as _ili  # noqa: E402
    assert _ili is not None, "importlib returned None — module is None"
    return _ili


def _get_meter_module():
    """Import SHIPPED meter module (AC-2 SHIPPED iter-24 Phase 5)."""
    spec = importlib.util.find_spec("kurort_engine.ev_charging.meter")
    assert spec is not None, (
        "kurort_engine.ev_charging.meter (AC-2 SHIPPED) is not importable — "
        f"Phase 5 ship regressed. find_spec returned: {spec!r}"
    )
    import kurort_engine.ev_charging.meter as _meter  # noqa: E402
    return _meter


def _get_ev_charging_module():
    """Import the SHIPPED ev_charging package (for BFSGComplianceError)."""
    _bfsg_compliance_error_is_importable()
    import kurort_engine.ev_charging as _ev  # noqa: E402
    return _ev


def _build_valid_invoice_line_item():
    """Build a valid InvoiceLineItem via the SHIPPED AC-3 helper.

    Returns (InvoiceLineItem, MeterReading, folio_dict_or_None).
    """
    ili_mod = _get_invoice_line_item_module()
    meter_mod = _get_meter_module()

    append_to_folio = getattr(ili_mod, "append_to_folio", None)
    assert callable(append_to_folio), (
        "kurort_engine.ev_charging.invoice_line_item must expose a callable "
        "append_to_folio entry point per AC-3 spec; got "
        f"{[n for n in dir(ili_mod) if not n.startswith('_')]!r}"
    )

    booking_id = "B-AC5-001"
    meter_reading = meter_mod.read_session(
        wallbox_id="WALLBOX-EBIKE-01",
        booking_id=booking_id,
        start=datetime(2030, 6, 15, 14, 0, 0, tzinfo=timezone.utc),
        stop=datetime(2030, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
        kwh=Decimal("0.5"),
    )
    folio: dict[str, dict] = {}
    line_item = append_to_folio(folio, booking_id, meter_reading, Decimal("0.45"))
    assert line_item is not None, "append_to_folio returned None"
    return line_item, meter_reading, folio


# ---------------------------------------------------------------------------
# AC-5 — InvoiceLineItem enforces lang="de" on text fields + label on
# non-text `unit` and `quantity` fields; BFSGComplianceError raised when
# any required BFSG-AA / WCAG 2.1 AA field is missing.
# ---------------------------------------------------------------------------


def test_ac5_invoice_line_item_enforces_lang_de_and_accessibility_labels() -> None:
    """AC-5 spec test_oracle (PHASE 8 RED).

    Asserts (per spec.yaml AC-5 — Unwanted-behavior BFSG-AA + WCAG 2.1 AA):

      (a) A valid InvoiceLineItem built via
          ``append_to_folio(folio, "B-AC5-001", meter_reading, Decimal("0.45"))``
          can be converted to a dict via ``.to_dict()``.

      (b) The dict carries ``lang="de"`` (a top-level / on the text-field
          surface — WCAG SC 3.1.1 language of page / part).

      (c) The dict carries ``label`` (accessibilityLabel, WCAG SC 4.1.2)
          keys for the non-text ``unit`` and ``quantity`` fields.

      (d) Calling ``validate_bfsg_compliance(invoice_line_item_dict)`` on
          the valid dict returns OK / does NOT raise.

      (e) Mutating the dict to remove the ``lang="de"`` entry (or remove
          the ``label`` key from one of the non-text fields) and calling
          ``validate_bfsg_compliance`` raises
          ``kurort_engine.ev_charging.BFSGComplianceError`` (or its
          ``ValueError`` subclass) with a diagnostic message naming the
          missing field.

    Reference: SHIPPED iter-21
    ``kurort_engine.kurkarte_wallet.passkit._assert_bfsg_compliance`` for
    the BFSG-AA + WCAG 2.1 AA validation style replicated here.
    """
    # ----- pre-checks: every required symbol exists (else RED is dishonest) -----
    _invoice_line_item_module_is_importable()
    _bfsg_compliance_error_is_importable()
    _validate_bfsg_compliance_helper_is_callable()

    ili_mod = _get_invoice_line_item_module()
    ev_mod = _get_ev_charging_module()

    # ----- (a) build a valid line item + dict -----
    line_item, _meter_reading, folio = _build_valid_invoice_line_item()
    assert hasattr(line_item, "to_dict"), (
        "InvoiceLineItem must expose a .to_dict() method to render "
        "JSON-serialisable dict per AC-5 spec"
    )
    line_dict = line_item.to_dict()
    assert isinstance(line_dict, dict), (
        f"InvoiceLineItem.to_dict() must return a dict; got {type(line_dict).__name__}"
    )

    # The SHIPPED Phase 7 folio mutator already appended the line dict —
    # confirm the folio mutation contract still holds after AC-5 wiring.
    assert "B-AC5-001" in folio, (
        "append_to_folio must mutate the folio by registering booking_id "
        f"per AC-3 spec; got folio keys={list(folio.keys())!r}"
    )

    # ----- (b) the dict carries ``lang="de"`` -----
    lang_value = line_dict.get("lang")
    assert lang_value == "de", (
        f"AC-5 BFSG-AA / WCAG SC 3.1.1: InvoiceLineItem JSON must carry "
        f"lang='de' on text fields; got lang={lang_value!r}"
    )

    # ----- (c) the dict carries ``label`` (accessibilityLabel) on the
    # non-text `unit` and `quantity` fields. Per spec, these are the
    # non-text fields that MUST be labelled so screen readers announce
    # the value (kWh, EUR) context.
    non_text_fields = ("unit", "quantity")
    for field_name in non_text_fields:
        field_payload = line_dict.get(field_name)
        # The label may live on the field value itself (when the field is
        # rendered as a dict payload {value, label}) OR on a sibling key.
        # The spec says "label (accessibilityLabel) for the non-text
        # `unit` and `quantity` fields"; the cleanest mapping is to wrap
        # each non-text field as {value, label} — assert the label key
        # is reachable via either pattern.
        label_value: object | None
        if isinstance(field_payload, dict):
            label_value = field_payload.get("label")
        else:
            # Sibling-pattern fallback: lookup "<field_name>_label"
            label_value = line_dict.get(f"{field_name}_label")

        assert label_value is not None and str(label_value).strip(), (
            f"AC-5 BFSG-AA / WCAG SC 4.1.2: non-text field {field_name!r} "
            f"must carry a non-empty 'label' (accessibilityLabel); "
            f"got label={label_value!r} (field payload={field_payload!r})"
        )

    # ----- (d) validate_bfsg_compliance on the valid dict does NOT raise -----
    validate_bfsg_compliance = ili_mod.validate_bfsg_compliance
    # Helper signature: validate_bfsg_compliance(line_item_dict) -> None
    sig = inspect.signature(validate_bfsg_compliance)
    assert len(sig.parameters) >= 1, (
        f"validate_bfsg_compliance must accept at least one parameter "
        f"(the line item dict); got signature={sig!r}"
    )
    # Must NOT raise on a valid dict.
    validate_bfsg_compliance(line_dict)

    # ----- (e) mutating the dict to remove ``lang`` (or remove the label
    # on a non-text field) MUST raise BFSGComplianceError naming the
    # missing field. -----
    BFSGComplianceError = ev_mod.BFSGComplianceError
    assert issubclass(BFSGComplianceError, ValueError), (
        "BFSGComplianceError must subclass ValueError so callers can "
        "catch a single base class for all BFSG-AA / WCAG violations; "
        f"got MRO={[c.__name__ for c in BFSGComplianceError.__mro__]!r}"
    )

    # ----- (e.1) remove top-level ``lang`` key -----
    bad_dict_missing_lang = dict(line_dict)
    bad_dict_missing_lang.pop("lang", None)
    raised_lang = False
    try:
        validate_bfsg_compliance(bad_dict_missing_lang)
    except BFSGComplianceError as exc:
        raised_lang = True
        # Diagnostic message must name the missing field for screen-reader
        # audit log traceability (per spec: "naming the missing field").
        msg = str(exc)
        assert "lang" in msg.lower(), (
            f"BFSGComplianceError message must name the missing 'lang' "
            f"field for diagnostic clarity; got message={msg!r}"
        )
    assert raised_lang, (
        "validate_bfsg_compliance MUST raise BFSGComplianceError when the "
        "top-level 'lang' attribute is absent from the line item dict"
    )

    # ----- (e.2) remove the ``label`` key from the non-text `unit` field -----
    bad_dict_missing_label = dict(line_dict)
    unit_payload = bad_dict_missing_label.get("unit")
    if isinstance(unit_payload, dict):
        bad_unit = dict(unit_payload)
        bad_unit.pop("label", None)
        bad_dict_missing_label["unit"] = bad_unit
    else:
        # Sibling-pattern fallback
        bad_dict_missing_label.pop("unit_label", None)

    raised_label = False
    try:
        validate_bfsg_compliance(bad_dict_missing_label)
    except BFSGComplianceError as exc:
        raised_label = True
        msg = str(exc)
        # Either "label" or "unit" must appear in the diagnostic message.
        assert ("label" in msg.lower()) or ("unit" in msg.lower()), (
            f"BFSGComplianceError message must name the missing 'label' / "
            f"'unit' field for diagnostic clarity; got message={msg!r}"
        )
    assert raised_label, (
        "validate_bfsg_compliance MUST raise BFSGComplianceError when the "
        "'label' (accessibilityLabel) is absent from the non-text 'unit' "
        "field on the line item dict"
    )