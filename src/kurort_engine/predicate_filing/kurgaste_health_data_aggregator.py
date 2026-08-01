"""kurort_engine.predicate_filing.kurgaste_health_data_aggregator — AC-2 + AC-5.

Iter-33 Developer. Tier-2 chain-extension.

Provides:
  * `validate_kurgaste_health_data(records)` — DSGVO Art. 9 + §23 SGB V
    Badekur validation gate (AC-2, Event-driven).
  * `aggregate_kurgaste_health_data(records)` — Kurgäste §23 SGB V + DSGVO
    Art. 9 aggregation with badekurst / classic / consent counts (AC-5,
    Ubiquitous).
  * `DSGVOArt9ValidationError(ValueError)` — raised when a Kurgäste record
    lacks explicit DSGVO Art. 9 consent.

Pattern F chain-extends the SHIPPED iter-18
`kurort_engine.kurpaket_orchestrator.SGBV23CertificateMissing` exception class
(re-exported via this module so AC-2 can raise it without an extra import).

Reference: iter-31 Scholar pick-first H1 (AC-2 + AC-5 verbatim from
spec.yaml PROTECTED block). SHA-256 of the AC block:
17d4eea23a1534123aa90687e1bb31bf55e589aad2779b251ca7285c3fc9a127.
"""
from __future__ import annotations

from datetime import date
from typing import Any

# Re-export the SHIPPED iter-18 §23 SGB V Muster 13 missing exception class so
# downstream callers can do ``from kurort_engine.predicate_filing import
# SGBV23CertificateMissing`` if they want — but the canonical import path is
# `kurort_engine.kurpaket_orchestrator.SGBV23CertificateMissing` and we use
# it directly in this module.
from kurort_engine.kurpaket_orchestrator import (  # noqa: E402,F401
    SGBV23CertificateMissing,
)

# ---------------------------------------------------------------------------
# Exception class (NEW) — DSGVO Art. 9 explicit consent validation
# ---------------------------------------------------------------------------

class DSGVOArt9ValidationError(ValueError):
    """Raised when a Kurgäste record lacks explicit DSGVO Art. 9 consent.

    Per AC-2 (Event-driven): ``validate_kurgaste_health_data(records)`` MUST
    raise :class:`DSGVOArt9ValidationError` for any record where
    ``consent_dsgvo_art9`` is ``False`` or missing.

    Per AC-5 (Ubiquitous): ``aggregate_kurgaste_health_data(records)`` MUST
    raise :class:`DSGVOArt9ValidationError` for any record missing the
    ``consent_dsgvo_art9`` field entirely.

    Inherits from :class:`ValueError` so callers can catch either
    ``ValueError`` (broad) or ``DSGVOArt9ValidationError`` (specific).
    """

    def __init__(self, message: str = "DSGVO Art. 9 explicit consent required") -> None:
        super().__init__(message)


# ---------------------------------------------------------------------------
# AC-2 — validate_kurgaste_health_data
# ---------------------------------------------------------------------------

def validate_kurgaste_health_data(kurgaste_records: list[dict[str, Any]]) -> bool:
    """Validate Kurgäste health-data records for DSGVO Art. 9 + §23 SGB V.

    Per AC-2 (Event-driven): the function MUST return ``True`` if every record
    has ``consent_dsgvo_art9: bool = True`` AND every Spezial-Heilbad
    (template_code = "E") record carries a non-empty ``muster13_id: str``
    (i.e. a §23 SGB V Muster 13 Badekur certificate).

    The function MUST raise
    :class:`kurort_engine.kurpaket_orchestrator.SGBV23CertificateMissing`
    (re-used from SHIPPED iter-18) for any Spezial-Heilbad record missing
    ``muster13_id``.

    The function MUST raise :class:`DSGVOArt9ValidationError` (NEW exception
    class defined in this module) for any record where ``consent_dsgvo_art9``
    is ``False`` or missing.
    """
    for idx, record in enumerate(kurgaste_records):
        # DSGVO Art. 9 explicit consent validation (AC-2)
        consent = record.get("consent_dsgvo_art9")
        if consent is False or consent is None:
            raise DSGVOArt9ValidationError(
                f"Kurgäste record at index {idx} missing DSGVO Art. 9 "
                f"explicit consent (consent_dsgvo_art9={consent!r})"
            )

        # §23 SGB V Muster 13 Badekur certificate validation (AC-2)
        template_code = str(record.get("template_code", "")).upper()
        muster13_id = record.get("muster13_id")
        if template_code == "E" and not muster13_id:
            raise SGBV23CertificateMissing(
                f"Kurgäste record at index {idx} (template_code='E' "
                f"Spezial-Heilbad) missing §23 SGB V Muster 13 certificate "
                f"(muster13_id={muster13_id!r})"
            )

    return True


# ---------------------------------------------------------------------------
# AC-5 — aggregate_kurgaste_health_data
# ---------------------------------------------------------------------------

def aggregate_kurgaste_health_data(
    kurgaste_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate Kurgäste health-data records for predicate-filing envelope.

    Per AC-5 (Ubiquitous): the function MUST return a JSON-serializable dict
    with required keys:
      * ``total_records: int`` (count of records)
      * ``badekurst_guests: int`` (Spezial-Heilbad template_E with valid
        ``muster13_id``)
      * ``classic_guests: int`` (template_A/B/C/D)
      * ``consent_art9_count: int`` (records with ``consent_dsgvo_art9=True``)
      * ``period: tuple[str, str]`` (ISO format of first arrival + last
        departure)
      * ``consent_compliance: bool`` (True iff every record has
        ``consent_dsgvo_art9=True``)

    The function MUST raise :class:`DSGVOArt9ValidationError` for any record
    missing the ``consent_dsgvo_art9`` field entirely.
    """
    total_records = len(kurgaste_records)
    badekurst_guests = 0
    classic_guests = 0
    consent_art9_count = 0
    earliest_arrival: date | None = None
    latest_departure: date | None = None

    for idx, record in enumerate(kurgaste_records):
        # DSGVO Art. 9 field must be present (AC-5 stricter than AC-2)
        if "consent_dsgvo_art9" not in record:
            raise DSGVOArt9ValidationError(
                f"Kurgäste record at index {idx} missing consent_dsgvo_art9 "
                f"field entirely (cannot aggregate without explicit consent flag)"
            )

        template_code = str(record.get("template_code", "")).upper()
        muster13_id = record.get("muster13_id")
        consent = record.get("consent_dsgvo_art9")

        # Spezial-Heilbad (template_E) WITH valid muster13 → badekurst_guests
        if template_code == "E" and muster13_id:
            badekurst_guests += 1
        # Classic templates A/B/C/D → classic_guests
        elif template_code in {"A", "B", "C", "D"}:
            classic_guests += 1

        if consent is True:
            consent_art9_count += 1

        # Track earliest arrival + latest departure for period envelope
        arrival = record.get("arrival")
        departure = record.get("departure")
        if isinstance(arrival, date):
            if earliest_arrival is None or arrival < earliest_arrival:
                earliest_arrival = arrival
        if isinstance(departure, date):
            if latest_departure is None or departure > latest_departure:
                latest_departure = departure

    period = (
        earliest_arrival.isoformat() if earliest_arrival else "",
        latest_departure.isoformat() if latest_departure else "",
    )
    consent_compliance = all(
        record.get("consent_dsgvo_art9") is True
        for record in kurgaste_records
    )

    return {
        "total_records": total_records,
        "badekurst_guests": badekurst_guests,
        "classic_guests": classic_guests,
        "consent_art9_count": consent_art9_count,
        "period": period,
        "consent_compliance": consent_compliance,
    }