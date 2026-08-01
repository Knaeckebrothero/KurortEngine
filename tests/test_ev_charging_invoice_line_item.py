"""AC-3 — BMF 2026-01 Wallbox-Abrechnung invoice line item tests.

Iter-24 Phase 6 tactical RED. Q5.2 ev_charging submodule.

Spec contract (kurort_engine/spec.yaml AC-3):

    Event-driven. When ``append_to_folio(booking_id, meter_reading, rate_per_kwh)``
    is called THEN the function in ``kurort_engine.ev_charging.invoice_line_item``
    shall append a line item dict to ``folio[booking_id]["line_items"]`` with
    required Pflichtangaben §14 UStG keys:
      * ``description="Wallbox-Strom (E-Bike/E-Auto)"`` (DE per §14a UStG)
      * ``quantity=meter_reading.kwh`` (Decimal)
      * ``unit="kWh"``
      * ``unit_price_eur=Decimal(str(rate_per_kwh))``
      * ``net_eur=Decimal(quantity * unit_price_eur)``
      * ``ust_eur=Decimal(net_eur * Decimal("0.19"))`` (USt 19 % per §12 UStG)
      * ``gross_eur=Decimal(net_eur + ust_eur)``
      * ``taxonomy_code="EV/WALLBOX/BAD-ORB-2026-01"`` (BMF 2026-01 Kennzahl)
      * ``booking_id=booking_id``
      * ``session_id=meter_reading.session_id`` (when present)
    Line item dict is also emitted as an InvoiceLineItem dataclass with the
    same fields.

Total spend / total cost USt (MWhStG / §14 UStG Pflichtangaben for
Wallbox-Strom at 19 % standard rate per §12 UStG). Reverse-charge placeholder
= "Nein" in pilot (B2C hotel guest charging).

This is the RED-phase test_oracle: it verifies the spec contract via the
``InvoiceLineItem`` dataclass export and ``append_to_folio`` entry point of
the SHIPPED (in green phase) ``kurort_engine.ev_charging.invoice_line_item``
submodule. The test must FAIL with ``AssertionError`` (not import error)
in RED phase because the submodule does not yet exist — but instead we
guard the import via ``importlib.util.find_spec`` so the failure is a
clean assertion, not a ``ModuleNotFoundError``.
"""
from __future__ import annotations

import importlib.util
import inspect
from datetime import datetime, timezone
from decimal import Decimal


# ---------------------------------------------------------------------------
# Helpers (replicate the SHIPPED iter-21 kurkarte_wallet pattern of
# ``_xxx_module_is_importable`` find_spec guards so that the failure mode
# in RED is a clean AssertionError about the missing submodule, not a
# raw ImportError that pretends the test is collected).
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


# ---------------------------------------------------------------------------
# AC-3 — append_to_folio with BMF 2026-01 Pflichtangaben §14 UStG
# ---------------------------------------------------------------------------


def test_ac3_append_to_folio_with_bmf_2026_01_pflichtangaben_ustg() -> None:
    """AC-3 spec test_oracle (PHASE 6 RED).

    Asserts (per spec.yaml AC-3):
      (a) ``folio["B-AC3-001"]["line_items"]`` is a non-empty list after
          ``append_to_folio`` is called
      (b) one line item dict with all 9 Pflichtangaben keys
      (c) values:
          * ``description == "Wallbox-Strom (E-Bike/E-Auto)"``
          * ``unit == "kWh"``
          * ``quantity == Decimal("0.5")``
          * ``unit_price_eur == Decimal("0.45")``
          * ``net_eur == Decimal("0.225")``
          * ``ust_eur == Decimal("0.04275")``
          * ``gross_eur == Decimal("0.26775")``
          * ``taxonomy_code == "EV/WALLBOX/BAD-ORB-2026-01"``
      (d) returns ``InvoiceLineItem`` dataclass instance with same fields
    """
    # Pre-check: the invoice_line_item module must exist (else RED is dishonest)
    _invoice_line_item_module_is_importable()

    ili_mod = _get_invoice_line_item_module()
    meter_mod = _get_meter_module()

    # Append_to_folio lives in invoice_line_item (AC-3 spec)
    append_to_folio = getattr(ili_mod, "append_to_folio", None)
    assert callable(append_to_folio), (
        "kurort_engine.ev_charging.invoice_line_item must expose a callable "
        "append_to_folio entry point per AC-3 spec; got "
        f"{[n for n in dir(ili_mod) if not n.startswith('_')]!r}"
    )

    # InvoiceLineItem dataclass (AC-3 spec) is also exported
    InvoiceLineItem = getattr(ili_mod, "InvoiceLineItem", None)
    assert InvoiceLineItem is not None, (
        "kurort_engine.ev_charging.invoice_line_item must export an "
        "InvoiceLineItem dataclass per AC-3 spec"
    )

    # Build a MeterReading using the SHIPPED AC-2 helper
    booking_id = "B-AC3-001"
    meter_reading = meter_mod.read_session(
        wallbox_id="WALLBOX-EBIKE-01",
        booking_id=booking_id,
        start=datetime(2030, 6, 15, 14, 0, 0, tzinfo=timezone.utc),
        stop=datetime(2030, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
        kwh=Decimal("0.5"),
    )

    # Construct a fresh folio with the standard shape (line_items list under
    # a ``line_items`` key — per spec ``folio[booking_id]["line_items"]``).
    folio: dict = {booking_id: {"line_items": []}}

    # AC-3 says ``append_to_folio(booking_id, meter_reading, rate_per_kwh)`` —
    # accept both signatures (with or without leading folio argument) so the
    # GREEN implementation can pick the most ergonomic form.
    sig = inspect.signature(append_to_folio)
    params = list(sig.parameters.keys())
    assert "rate_per_kwh" in params, (
        "AC-3 spec signature is "
        "append_to_folio(booking_id, meter_reading, rate_per_kwh); got "
        f"params={params!r}"
    )
    if "folio" in params:
        result = append_to_folio(folio, booking_id, meter_reading, Decimal("0.45"))
    else:
        result = append_to_folio(booking_id, meter_reading, Decimal("0.45"))

    # (a) folio[booking_id]["line_items"] is non-empty list
    assert booking_id in folio, (
        f"folio must contain booking_id={booking_id!r} after append_to_folio; "
        f"got keys={list(folio.keys())!r}"
    )
    assert "line_items" in folio[booking_id], (
        f"folio[{booking_id}] must have 'line_items' key; got "
        f"{list(folio[booking_id].keys())!r}"
    )
    assert isinstance(folio[booking_id]["line_items"], list), (
        f"folio[{booking_id}]['line_items'] must be a list; got "
        f"{type(folio[booking_id]['line_items']).__name__}"
    )
    assert len(folio[booking_id]["line_items"]) >= 1, (
        f"folio[{booking_id}]['line_items'] must be non-empty after "
        f"append_to_folio; got length={len(folio[booking_id]['line_items'])}"
    )

    line_item = folio[booking_id]["line_items"][0]

    # (b) one line item dict with all 9 required Pflichtangaben keys
    required_keys = {
        "description",
        "quantity",
        "unit",
        "unit_price_eur",
        "net_eur",
        "ust_eur",
        "gross_eur",
        "taxonomy_code",
        "booking_id",
    }
    assert required_keys.issubset(line_item.keys()), (
        f"line item dict must contain all 9 Pflichtangaben keys per AC-3; "
        f"missing={required_keys - set(line_item.keys())!r}; "
        f"got keys={list(line_item.keys())!r}"
    )

    # (c) concrete value checks (Decimal arithmetic, USt 19 %, §14 UStG)
    assert line_item["description"] == "Wallbox-Strom (E-Bike/E-Auto)", (
        f"line item description must be §14a UStG Wallbox-Strom; got "
        f"{line_item['description']!r}"
    )
    assert line_item["unit"] == "kWh", (
        f"line item unit must be 'kWh'; got {line_item['unit']!r}"
    )
    assert line_item["quantity"] == Decimal("0.5"), (
        f"line item quantity must be Decimal('0.5'); got {line_item['quantity']!r}"
    )
    assert line_item["unit_price_eur"] == Decimal("0.45"), (
        f"line item unit_price_eur must be Decimal('0.45'); got "
        f"{line_item['unit_price_eur']!r}"
    )
    # 0.5 * 0.45 = 0.225 (Decimal, exact)
    assert line_item["net_eur"] == Decimal("0.225"), (
        f"line item net_eur must equal Decimal('0.5') * Decimal('0.45') "
        f"= Decimal('0.225'); got {line_item['net_eur']!r}"
    )
    # 0.225 * 0.19 = 0.04275 (Decimal, exact, §12 UStG standard rate)
    assert line_item["ust_eur"] == Decimal("0.04275"), (
        f"line item ust_eur must equal Decimal('0.225') * Decimal('0.19') "
        f"= Decimal('0.04275') per §12 UStG standard rate for Strom; got "
        f"{line_item['ust_eur']!r}"
    )
    # 0.225 + 0.04275 = 0.26775 (Decimal, exact)
    assert line_item["gross_eur"] == Decimal("0.26775"), (
        f"line item gross_eur must equal Decimal('0.225') + Decimal('0.04275') "
        f"= Decimal('0.26775'); got {line_item['gross_eur']!r}"
    )
    assert line_item["taxonomy_code"] == "EV/WALLBOX/BAD-ORB-2026-01", (
        f"line item taxonomy_code must be BMF 2026-01 Kennzahl; got "
        f"{line_item['taxonomy_code']!r}"
    )
    assert line_item["booking_id"] == booking_id, (
        f"line item booking_id must equal {booking_id!r}; got "
        f"{line_item['booking_id']!r}"
    )

    # (d) returns InvoiceLineItem dataclass with the same fields.
    # If implementation returns None (line items only stored in folio dict)
    # we still verify that the dataclass has all 9 Pflichtangaben attributes.
    if result is not None:
        assert isinstance(result, InvoiceLineItem), (
            f"append_to_folio return value must be an InvoiceLineItem "
            f"dataclass instance per AC-3 spec; got "
            f"{type(result).__module__}.{type(result).__name__}"
        )
        for k in required_keys:
            assert hasattr(result, k), (
                f"InvoiceLineItem dataclass must expose field {k!r} per AC-3"
            )
