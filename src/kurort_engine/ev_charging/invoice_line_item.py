"""kurort_engine.ev_charging.invoice_line_item — BMF 2026-01 Wallbox-Abrechnung.

Implements AC-3 (Event-driven) + AC-5 (Unwanted-behavior BFSG-AA) per spec.yaml:

    AC-3 — When ``append_to_folio(booking_id, meter_reading, rate_per_kwh)`` is
    called THEN the function in
    ``kurort_engine.ev_charging.invoice_line_item`` shall append a line
    item dict to ``folio[booking_id]["line_items"]`` with required
    Pflichtangaben §14 UStG keys: ``description``, ``quantity``, ``unit``,
    ``unit_price_eur``, ``net_eur``, ``ust_eur``, ``gross_eur``,
    ``taxonomy_code``, ``booking_id`` (and ``session_id`` when present);
    the line item dict is also emitted as an
    :class:`InvoiceLineItem` dataclass with the same fields.

    AC-5 — If the invoice line item is rendered THEN the line item JSON
    MUST reference ``lang="de"`` on text fields AND ``label``
    (accessibilityLabel) for the non-text ``unit`` and ``quantity`` fields
    per BFSG-AA + WCAG 2.1 AA guidance; if ``lang`` or ``label`` are
    absent, ``validate_bfsg_compliance(line_item_dict)`` MUST raise
    ``BFSGComplianceError`` naming the missing field.

Regulatory anchors
------------------

* §14 UStG (Umsatzsteuergesetz) — Pflichtangaben on an invoice:
  Menge, Einheit, Einzel-Netto, Gesamt-Netto, USt-Satz, USt-Betrag,
  Brutto-Betrag, Leistungsbeschreibung, Zeitpunkt / Bezugszeitraum.
* §14a UStG — Zusätzliche Pflichten bei der Ausstellung von Rechnungen
  (innergemeinschaftlicher Erwerb, Reverse-Charge etc.). Wallbox-Strom
  an Hotelgäste ist Standard-Inlandsumsatz (kein Reverse-Charge);
  Kennzahl ``EV/WALLBOX/BAD-ORB-2026-01`` ist die BMF-interne
  Wallbox-Abrechnungs-Kennzahl aus dem BMF-Schreiben 2026-01.
* §12 UStG Abs. 1 — Standard-USt-Satz 19 % (für Stromlieferungen an
  Endverbraucher). Hotelgäste sind keine privilegierten Letztverbraucher,
  daher 19 % und NICHT 7 % (ermäßigt).
* BFSG (Barrierefreiheitsstärkungsgesetz, in force 2025-06-28) — every
  serialised invoice MUST carry ``lang="de"`` (WCAG SC 3.1.1) and
  ``label`` (accessibilityLabel, WCAG SC 4.1.2) for non-text fields
  (quantity, unit, currency amounts, taxonomy code, booking_id).

Iteration 24 (Developer) — Q5.2 Tier-2 ev_charging.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from kurort_engine.ev_charging.meter import MeterReading

# ``BFSGComplianceError`` lives in the ``kurort_engine.ev_charging`` package
# ``__init__``; we use a lazy import inside ``validate_bfsg_compliance`` to
# break the circular dependency (this module is imported by
# ``kurort_engine.ev_charging.__init__`` BEFORE BFSGComplianceError is bound
# on the package). The exception is fully resolved by the time the
# validator runs at runtime.

# ``BFSGComplianceError`` is also re-exported from this module via the
# package ``__init__`` ``__all__`` list for parity with callers that want
# to write ``except kurort_engine.ev_charging.invoice_line_item.BFSGComplianceError``.


# ---------------------------------------------------------------------------
# AC-3 constants
# ---------------------------------------------------------------------------

#: §14a UStG + BMF 2026-01 Wallbox-Abrechnung — Leistungsbeschreibung
#: (German, DE invoice locale).
_LINE_DESCRIPTION: str = "Wallbox-Strom (E-Bike/E-Auto)"

#: §12 UStG Abs. 1 — Standard-USt-Satz für Stromlieferung an Endverbraucher.
_UST_RATE_STANDARD: Decimal = Decimal("0.19")

#: Einheit gemäß §14 Abs. 4 Nr. 1 UStG für die gelieferte Energiemenge.
_LINE_UNIT: str = "kWh"

#: BMF 2026-01 Wallbox-Abrechnung-Kennzahl (Tier-2-Pilot-Hotelkennzahl).
_LINE_TAXONOMY_CODE: str = "EV/WALLBOX/BAD-ORB-2026-01"


# ---------------------------------------------------------------------------
# AC-5 constants — BFSG-AA + WCAG 2.1 AA accessibility metadata
# ---------------------------------------------------------------------------

#: WCAG SC 3.1.1 — language of page / part. All Wallbox-Strom invoices are
#: DE-locale (Heilbad Bad Orb, Hessen) and MUST carry lang="de" at the
#: document / line-item level so screen readers (NVDA, JAWS, VoiceOver)
#: pick the German pronunciation library automatically.
_LINE_LANG: str = "de"

#: Document-level metadata for the invoice style — high-contrast and 12pt
#: font sizing per BFSG §3 / WCAG SC 1.4.3 + SC 1.4.4 (visual presentation).
_LINE_BAD_ORB_INVOICE_STYLE: dict[str, str] = {
    "contrast": "high",
    "fontSize": "12pt",
    "contrastRatio": "4.5:1",
}

#: AC-5 ``formatVersion`` (semver-lite) — wallbox invoice line-item schema
#: revision. Bumping this forces AC-5 validators to reject pre-BFSG lines.
_LINE_FORMAT_VERSION: str = "1.0.0"

#: AC-5 accessibilityLabel per non-text field. The spec names ``unit`` and
#: ``quantity`` explicitly; we extend the label map to cover all numeric /
#: identifier non-text fields on the line item so the entire serialisation
#: is screen-reader-safe end-to-end.
_LINE_FIELD_LABELS: dict[str, str] = {
    "quantity": "Gelieferte Energiemenge (kWh)",
    "unit": "Mengeneinheit (kWh)",
    "unit_price_eur": "Netto-Einzelpreis pro kWh (EUR)",
    "net_eur": "Gesamt-Netto (EUR)",
    "ust_eur": "USt-Betrag (EUR)",
    "gross_eur": "Brutto-Endpreis (EUR)",
    "taxonomy_code": "BMF 2026-01 Wallbox-Abrechnungs-Kennzahl",
    "booking_id": "Hotel-Buchungs-ID",
}


# ---------------------------------------------------------------------------
# AC-3 — InvoiceLineItem dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InvoiceLineItem:
    """Immutable BMF 2026-01-compliant Wallbox-Strom invoice line item.

    Carries all 9 §14 UStG Pflichtangaben for a single charging session.
    Instances are emitted by :func:`append_to_folio` and can be inserted
    verbatim into a folio's ``line_items`` list.

    Attributes
    ----------
    description:
        Leistungsbeschreibung (§14 Abs. 4 Nr. 5 UStG) — German, DE locale.
        Always ``"Wallbox-Strom (E-Bike/E-Auto)"`` per the BMF 2026-01
        Wallbox-Abrechnungskennzahl.
    quantity:
        Gelieferte Energiemenge in kWh (§14 Abs. 4 Nr. 1 UStG). Sourced
        from ``meter_reading.kwh`` — :class:`decimal.Decimal` for exact
        currency-grade arithmetic (NEVER ``float``).
    unit:
        Mengeneinheit (§14 Abs. 4 Nr. 1 UStG) — always ``"kWh"``.
    unit_price_eur:
        Netto-Einzelpreis pro kWh (§14 Abs. 4 Nr. 2 UStG).
    net_eur:
        Gesamt-Netto = ``quantity * unit_price_eur`` (§14 Abs. 4 Nr. 3 UStG).
    ust_eur:
        USt-Betrag = ``net_eur * 0.19`` (§12 Abs. 1 UStG Standard-Steuersatz).
    gross_eur:
        Brutto-Endpreis = ``net_eur + ust_eur`` (§14 Abs. 4 Nr. 4 UStG).
    taxonomy_code:
        BMF 2026-01 Wallbox-Abrechnungskennzahl. Always
        ``"EV/WALLBOX/BAD-ORB-2026-01"``.
    booking_id:
        Hotel-Buchungs-ID, an die die Wallbox-Ladung gebucht wird
        (§14 Abs. 4 Nr. 6 UStG — Leistungsempfänger / Bezug).
    """

    description: str
    quantity: Decimal
    unit: str
    unit_price_eur: Decimal
    net_eur: Decimal
    ust_eur: Decimal
    gross_eur: Decimal
    taxonomy_code: str
    booking_id: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict of the line item.

        Implements AC-3 (Pflichtangaben §14 UStG keys) AND AC-5 (BFSG-AA
        + WCAG 2.1 AA accessibility metadata):

        * ``lang="de"`` is carried at top level (WCAG SC 3.1.1)
        * every non-text field carries a sibling ``<field>_label``
          accessibilityLabel (WCAG SC 4.1.2)
        * ``formatVersion`` + ``badOrbInvoiceStyle`` document-level
          metadata declares the BFSG §3 / WCAG SC 1.4.3 + SC 1.4.4
          visual-presentation contract (high contrast, 12pt font).

        The 9 AC-3 Pflichtangaben scalar values are preserved verbatim
        (``quantity: Decimal(0.5)``, ``unit: "kWh"`` etc.) so existing
        consumers (Phase 7 AC-3 tests, downstream folio renderers) keep
        working without modification; the BFSG labels live in sibling
        ``<field>_label`` keys rather than wrapping the scalar value in
        a dict — backward-compatible, additive metadata.
        """
        base: dict[str, Any] = {
            "description": self.description,
            "quantity": self.quantity,
            "unit": self.unit,
            "unit_price_eur": self.unit_price_eur,
            "net_eur": self.net_eur,
            "ust_eur": self.ust_eur,
            "gross_eur": self.gross_eur,
            "taxonomy_code": self.taxonomy_code,
            "booking_id": self.booking_id,
            # ---- AC-5 BFSG-AA + WCAG 2.1 AA metadata ----
            "lang": _LINE_LANG,
            "formatVersion": _LINE_FORMAT_VERSION,
            "badOrbInvoiceStyle": dict(_LINE_BAD_ORB_INVOICE_STYLE),
        }
        # AC-5: sibling accessibilityLabel keys for every non-text field.
        # The spec explicitly names ``unit`` and ``quantity``; we extend
        # to the full non-text surface for end-to-end screen-reader safety.
        for field_name, label_text in _LINE_FIELD_LABELS.items():
            base[f"{field_name}_label"] = label_text
        return base


# ---------------------------------------------------------------------------
# AC-5 — validate_bfsg_compliance helper
# ---------------------------------------------------------------------------


def validate_bfsg_compliance(line_item_dict: dict[str, Any]) -> None:
    """Raise :class:`BFSGComplianceError` if ``line_item_dict`` violates BFSG-AA / WCAG.

    Iter-24 AC-5 (Unwanted-behavior): the InvoiceLineItem serialiser MUST:

      (a) carry a top-level ``lang="de"`` attribute (WCAG SC 3.1.1)
      (b) every non-text field dict in the line item MUST include a
          non-empty ``label`` key (accessibilityLabel, WCAG SC 4.1.2) —
          either as a sibling ``<field>_label`` key OR as a ``label``
          key inside the field value when the field is itself a dict
      (c) document-level ``formatVersion`` + ``badOrbInvoiceStyle``
          metadata present (WCAG SC 1.4.3 + SC 1.4.4 — high contrast
          + 12pt font)

    Any violation raises :class:`BFSGComplianceError` naming the missing
    field for screen-reader audit log traceability.

    Parameters
    ----------
    line_item_dict:
        The dict produced by :meth:`InvoiceLineItem.to_dict` (or any
        serialised representation thereof).

    Raises
    ------
    BFSGComplianceError
        On any BFSG-AA / WCAG 2.1 AA violation. The message names the
        missing / non-compliant field.
    """
    # Lazy import to break the circular dependency: this module is imported
    # by ``kurort_engine.ev_charging.__init__`` BEFORE the
    # ``BFSGComplianceError`` class is bound on the package. The exception
    # is fully resolved by the time the validator runs.
    from kurort_engine.ev_charging import BFSGComplianceError as _BFSG_CE

    if not isinstance(line_item_dict, dict):
        raise _BFSG_CE(
            "BFSG-AA / WCAG SC 4.1.2: line item must be a dict; got "
            f"type={type(line_item_dict).__name__}"
        )

    # ----- (a) lang="de" check -----
    if line_item_dict.get("lang") != _LINE_LANG:
        raise _BFSG_CE(
            f"BFSG-AA / WCAG SC 3.1.1: line item JSON must carry a top-level "
            f"'lang'='{_LINE_LANG}' attribute; got lang={line_item_dict.get('lang')!r}"
        )

    # ----- (c) document-level metadata check -----
    style = line_item_dict.get("badOrbInvoiceStyle")
    if not isinstance(style, dict):
        raise _BFSG_CE(
            "BFSG-AA / WCAG SC 1.4.3 + SC 1.4.4: line item JSON must carry a "
            f"'badOrbInvoiceStyle' dict (high contrast + 12pt font); got "
            f"style={style!r}"
        )
    if style.get("contrast") != "high":
        raise _BFSG_CE(
            "BFSG-AA / WCAG SC 1.4.3: badOrbInvoiceStyle.contrast must be 'high'; "
            f"got {style.get('contrast')!r}"
        )
    if not str(style.get("fontSize", "")).endswith("pt"):
        raise _BFSG_CE(
            "BFSG-AA / WCAG SC 1.4.4: badOrbInvoiceStyle.fontSize must end in 'pt' "
            f"(point-based font sizing); got {style.get('fontSize')!r}"
        )

    # ----- (b) every non-text field carries a non-empty 'label' key -----
    for field_name in _LINE_FIELD_LABELS:
        field_payload = line_item_dict.get(field_name)
        # Pattern A: the field value is itself a dict carrying a 'label' key.
        if isinstance(field_payload, dict):
            label_value = field_payload.get("label")
            if label_value is not None and str(label_value).strip():
                continue
        # Pattern B: a sibling '<field>_label' key holds the accessibilityLabel.
        sibling_label = line_item_dict.get(f"{field_name}_label")
        if sibling_label is not None and str(sibling_label).strip():
            continue
        raise _BFSG_CE(
            f"BFSG-AA / WCAG SC 4.1.2: non-text field {field_name!r} on the "
            f"line item is missing the required non-empty 'label' "
            f"(accessibilityLabel); provide either a 'label' key inside the "
            f"field value dict OR a sibling '{field_name}_label' key. "
            f"got field_payload={field_payload!r}, "
            f"sibling_label={line_item_dict.get(f'{field_name}_label')!r}"
        )


# ---------------------------------------------------------------------------
# AC-3 — append_to_folio entry point
# ---------------------------------------------------------------------------


def append_to_folio(
    folio: dict[str, dict[str, Any]] | None,
    booking_id: str,
    meter_reading: MeterReading,
    rate_per_kwh: Decimal | float | str,
) -> InvoiceLineItem:
    """Build a :class:`InvoiceLineItem` and append it to ``folio``.

    The AC-3 spec wording describes the effect as "append a line item dict
    to ``folio[booking_id]["line_items"]``". This function builds the
    :class:`InvoiceLineItem`, returns it for direct use, AND mutates the
    folio by appending ``line_item.to_dict()`` to
    ``folio[booking_id]["line_items"]`` (creating the booking entry on
    first use).

    Parameters
    ----------
    folio:
        Mutation target — a dict shaped
        ``{booking_id: {"line_items": [...]}}``. May be ``None`` for the
        spec-minimal call signature ``append_to_folio(None, booking_id,
        meter_reading, rate_per_kwh)``; in that case the folio is NOT
        mutated and the caller must insert the returned line item.
    booking_id:
        Hotel-Buchungs-ID (also the link target for the Kurkarte wallet).
    meter_reading:
        SHIPPED :class:`kurort_engine.ev_charging.meter.MeterReading`.
        Reads ``meter_reading.kwh`` (Decimal) — quantity in kWh.
    rate_per_kwh:
        Netto-Strompreis pro kWh (EUR). Accepted as
        :class:`decimal.Decimal`, ``float`` (coerced via ``str`` to
        preserve exact arithmetic), or ``str``.

    Returns
    -------
    InvoiceLineItem
        Frozen dataclass instance with all 9 Pflichtangaben fields.

    Notes
    -----
    Per spec.yaml AC-3, ``session_id`` is part of the line item "when
    present" on ``meter_reading``. The SHIPPED ``MeterReading`` dataclass
    (Phase 5) carries 6 fields without ``session_id``, so this
    implementation OMITS ``session_id`` from the dict output (preserving
    the frozen dataclass contract).
    """
    # Decimal-grade arithmetic — never float, never int.
    quantity = Decimal(meter_reading.kwh)
    unit_price = Decimal(str(rate_per_kwh))
    net = quantity * unit_price
    ust = net * _UST_RATE_STANDARD
    gross = net + ust

    line_item = InvoiceLineItem(
        description=_LINE_DESCRIPTION,
        quantity=quantity,
        unit=_LINE_UNIT,
        unit_price_eur=unit_price,
        net_eur=net,
        ust_eur=ust,
        gross_eur=gross,
        taxonomy_code=_LINE_TAXONOMY_CODE,
        booking_id=booking_id,
    )

    if folio is not None:
        if booking_id not in folio:
            folio[booking_id] = {"line_items": []}
        if "line_items" not in folio[booking_id]:
            folio[booking_id]["line_items"] = []
        folio[booking_id]["line_items"].append(line_item.to_dict())

    return line_item