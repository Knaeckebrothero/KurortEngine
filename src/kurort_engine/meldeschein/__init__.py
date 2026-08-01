"""kurort_engine.meldeschein — BMG §30 Meldeschein PDF + DSGVO Art. 28 (3) AVV
+ BFSG-WCAG-2.1-AA booking-flow scanner (Kurort-vertical regulatory layer).

Kurort-vertical extension to ``kurort_engine`` for the Heilbad-vertical
Meldeschein (registration form) layer per the Scholar iter-4 Proposal #1
DE-Kurort-vertical handoff spec at KB note
``iter-6-developer-handoff-spec-proposal-1-kurort-vertical-12-day-burn-9-modules-5``.

Module surface (per AC-N bindings for the Stage-1 architectural mini-slice of
iteration 6, per ``spec.yaml`` + ``spec_lock.md`` PROTECTED block):
  - AC-1: BMG §30 Meldeschein PDF for foreign-national guests
          (BEG IV 2025-01-01 regime; foreign-guest Meldepflicht preserved per
          § 30 Abs. 2 BMG with Ausweis-Seriennummer capture).
  - AC-2: DSGVO Art. 28 (3) Auftragsverarbeitungsvertrag (AVV) generator
          with 10 H2 clauses (BfDI Muster-AVV template structure).
  - AC-3: BFSG-WCAG-2.1-AA booking-flow scanner (filter empty < 200,
          label empty < 30, contrast < 4.5:1, target size < 24px,
          lang attribute missing per EN 301 549 v3.2.1 §9.4.1.1, §10.5,
          §11.1, §11.5).

Bootstrap convention (iter-6 Phase-2 tactical):
- Stage-1 ships just this __init__.py with the 8-symbol public API
  (5 schemas/exceptions + 3 placeholder renderer entry points).
- Stage-2 (Phase-4 green) replaces the ``render`` placeholder with a
  minimum byte-emitting PDF blob (the real reportlab-based renderer is
  scheduled for a future Stage-3 iteration).
- Tests live in repo/tests/test_<module>.py::test_ac<N>_<name>.

Type hint convention: PEP 604 ``X | None`` (matches spa_wellness
PaymentAdapter / SpaBooking precedent at repo/src/kurort_engine/
spa_wellness/payment_adapter.py:110).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

# ---------------------------------------------------------------------------
# Exception classes (per AC-1, AC-2, AC-3 verbatim)
# ---------------------------------------------------------------------------


class MeldescheinValidationError(ValueError):
    """Raised when the MeldescheinForm is missing a BMG §30 Pflichtangabe (AC-1)."""

    def __init__(self, message: str = "missing required BMG §30 Pflichtangabe") -> None:
        super().__init__(message)
        self.message = message


class AVVValidationError(ValueError):
    """Raised when the ProcessingRecord is missing a DSGVO Art. 28 (3) field (AC-2)."""

    def __init__(self, message: str = "missing required DSGVO Art. 28 (3) field") -> None:
        super().__init__(message)
        self.message = message


class BFSGScannerInputError(ValueError):
    """Raised when bfsg_scanner.scan_booking_flow receives empty/None input (AC-3)."""

    def __init__(
        self, message: str = "html_bytes must be non-empty bytes for EN 301 549 v3.2.1 booking-flow scan"
    ) -> None:
        super().__init__(message)
        self.message = message


# ---------------------------------------------------------------------------
# Pydantic-style dataclass schemas (per AC-1, AC-2 verbatim)
#
# Implemented as @dataclass(frozen=True, init=False) so we can supply custom
# __init__ signatures that match the AC contracts (the auto-generated
# __init__ would otherwise expose every field as a kwarg and break the
# MeldescheinForm(form) public API per the iter-3 spa_wellness phase-7
# lesson at KB note
# iter-3-spa-wellness-phase-7-lesson-dataclassfrozentrue-initfalse-pattern-for-cus).
# ---------------------------------------------------------------------------


# BMG §30 Abs. 1 + Abs. 2 mandatory fields (foreign-guest case)
# Per spec.yaml AC-1: 7 mandatory fields (Familienname, Vorname, Geburtsdatum,
# Staatsangehörigkeit, Anschrift, Anreisedatum, Abreisedatum) + optional
# Ausweis-Seriennummer for foreign guests per § 30 Abs. 2.
_MELDESCHEIN_REQUIRED_FIELDS: tuple[str, ...] = (
    "familienname",
    "vorname",
    "geburtsdatum",
    "staatsangehoerigkeit",
    "anschrift",
    "anreisedatum",
    "abreisedatum",
)


@dataclass(frozen=True, init=False)
class MeldescheinForm:
    """Pydantic-style schema for the BMG §30 Meldeschein (registration form).

    Captures the 7 BMG §30 Abs. 1 Pflichtangaben + the foreign-guest
    ``ausweis_seriennummer`` field per §30 Abs. 2 (BEG IV 2025-01-01 regime
    for German-national guests preserves the field, not the Meldepflicht).

    Construct via ``MeldescheinForm(...)`` keyword arguments; the custom
    ``__init__`` validates all 7 required fields are non-empty / non-None
    and raises ``MeldescheinValidationError`` on the first missing field.
    """

    familienname: str
    vorname: str
    geburtsdatum: date
    staatsangehoerigkeit: str
    anschrift: str
    anreisedatum: date
    abreisedatum: date
    ausweis_seriennummer: str | None = None

    def __init__(
        self,
        familienname: str = "",
        vorname: str = "",
        geburtsdatum: date | None = None,
        staatsangehoerigkeit: str = "",
        anschrift: str = "",
        anreisedatum: date | None = None,
        abreisedatum: date | None = None,
        ausweis_seriennummer: str | None = None,
    ) -> None:
        # Validate 7 mandatory fields (canonical order, German field names per AC-1)
        if not familienname or not isinstance(familienname, str):
            raise MeldescheinValidationError(
                "missing required BMG §30 Pflichtangabe: familienname"
            )
        if not vorname or not isinstance(vorname, str):
            raise MeldescheinValidationError(
                "missing required BMG §30 Pflichtangabe: vorname"
            )
        if geburtsdatum is None or not isinstance(geburtsdatum, date):
            raise MeldescheinValidationError(
                "missing required BMG §30 Pflichtangabe: geburtsdatum"
            )
        if not staatsangehoerigkeit or not isinstance(staatsangehoerigkeit, str):
            raise MeldescheinValidationError(
                "missing required BMG §30 Pflichtangabe: staatsangehoerigkeit"
            )
        if not anschrift or not isinstance(anschrift, str):
            raise MeldescheinValidationError(
                "missing required BMG §30 Pflichtangabe: anschrift"
            )
        if anreisedatum is None or not isinstance(anreisedatum, date):
            raise MeldescheinValidationError(
                "missing required BMG §30 Pflichtangabe: anreisedatum"
            )
        if abreisedatum is None or not isinstance(abreisedatum, date):
            raise MeldescheinValidationError(
                "missing required BMG §30 Pflichtangabe: abreisedatum"
            )
        object.__setattr__(self, "familienname", familienname)
        object.__setattr__(self, "vorname", vorname)
        object.__setattr__(self, "geburtsdatum", geburtsdatum)
        object.__setattr__(self, "staatsangehoerigkeit", staatsangehoerigkeit)
        object.__setattr__(self, "anschrift", anschrift)
        object.__setattr__(self, "anreisedatum", anreisedatum)
        object.__setattr__(self, "abreisedatum", abreisedatum)
        object.__setattr__(self, "ausweis_seriennummer", ausweis_seriennummer)


# DSGVO Art. 28 (3) Pflichtangaben (per spec.yaml AC-2).
# Per spec.yaml AC-2: 8 mandatory fields + 4 optional H2 clause fields
# (obligations, sub_processor_list, tom_measures, data_subject_rights_assistance).
_AVV_REQUIRED_FIELDS: tuple[str, ...] = (
    "controller_name",
    "processor_name",
    "subjects",
    "nature",
    "purpose",
    "data_categories",
    "data_subject_categories",
    "breach_notification_terms",
)


@dataclass(frozen=True, init=False)
class ProcessingRecord:
    """Pydantic-style schema for the DSGVO Art. 28 (3) AVV (controller→processor).

    Captures the 8 mandatory fields from Art. 28 (3) lit. a–h + 4 optional
    fields used by the Stage-1 BfDI Muster-AVV template's H2 clauses
    (obligations → H2 §3, sub_processor_list → H2 §7, tom_measures → H2 §8,
    data_subject_rights_assistance → H2 §10).

    Construct via ``ProcessingRecord(...)`` keyword arguments; the custom
    ``__init__`` validates all 8 required fields are non-empty / non-None
    and raises ``AVVValidationError`` on the first missing field.
    """

    controller_name: str
    processor_name: str
    subjects: str
    nature: str
    purpose: str
    data_categories: str
    data_subject_categories: str
    breach_notification_terms: str
    obligations: str = ""
    sub_processor_list: str = ""
    tom_measures: str = ""
    data_subject_rights_assistance: str = ""

    def __init__(
        self,
        controller_name: str = "",
        processor_name: str = "",
        subjects: str = "",
        nature: str = "",
        purpose: str = "",
        data_categories: str = "",
        data_subject_categories: str = "",
        breach_notification_terms: str = "",
        obligations: str = "",
        sub_processor_list: str = "",
        tom_measures: str = "",
        data_subject_rights_assistance: str = "",
    ) -> None:
        # Validate 8 mandatory fields (canonical order, German field names per AC-2)
        if not controller_name or not isinstance(controller_name, str):
            raise AVVValidationError(
                "missing required DSGVO Art. 28 (3) field: controller_name"
            )
        if not processor_name or not isinstance(processor_name, str):
            raise AVVValidationError(
                "missing required DSGVO Art. 28 (3) field: processor_name"
            )
        if not subjects or not isinstance(subjects, str):
            raise AVVValidationError(
                "missing required DSGVO Art. 28 (3) field: subjects"
            )
        if not nature or not isinstance(nature, str):
            raise AVVValidationError(
                "missing required DSGVO Art. 28 (3) field: nature"
            )
        if not purpose or not isinstance(purpose, str):
            raise AVVValidationError(
                "missing required DSGVO Art. 28 (3) field: purpose"
            )
        if not data_categories or not isinstance(data_categories, str):
            raise AVVValidationError(
                "missing required DSGVO Art. 28 (3) field: data_categories"
            )
        if not data_subject_categories or not isinstance(data_subject_categories, str):
            raise AVVValidationError(
                "missing required DSGVO Art. 28 (3) field: data_subject_categories"
            )
        if not breach_notification_terms or not isinstance(breach_notification_terms, str):
            raise AVVValidationError(
                "missing required DSGVO Art. 28 (3) field: breach_notification_terms"
            )
        object.__setattr__(self, "controller_name", controller_name)
        object.__setattr__(self, "processor_name", processor_name)
        object.__setattr__(self, "subjects", subjects)
        object.__setattr__(self, "nature", nature)
        object.__setattr__(self, "purpose", purpose)
        object.__setattr__(self, "data_categories", data_categories)
        object.__setattr__(self, "data_subject_categories", data_subject_categories)
        object.__setattr__(self, "breach_notification_terms", breach_notification_terms)
        object.__setattr__(self, "obligations", obligations)
        object.__setattr__(self, "sub_processor_list", sub_processor_list)
        object.__setattr__(self, "tom_measures", tom_measures)
        object.__setattr__(self, "data_subject_rights_assistance", data_subject_rights_assistance)


# ---------------------------------------------------------------------------
# Renderer entry points (AC-1..AC-3) — Stage-2 minimum implementations
# ---------------------------------------------------------------------------
# AC-1 (render) is implemented as a minimum byte-emitting PDF blob so
# iter-16 AC-1 GREEN is reachable. A full reportlab-based implementation
# is scheduled for a future Stage-3 iteration that does not block F5.
#
# AC-2 (generate_avv_markdown) and AC-3 (scan_booking_flow) remain
# Stage-1 placeholders (NotImplementedError) because they are not part
# of the iter-16 F5 Tier-1 wiring (per `spec.yaml:88-152` AC-1..AC-5).
# ---------------------------------------------------------------------------


def render(form: MeldescheinForm) -> bytes:
    """Render the BMG §30 Meldeschein PDF (AC-1 contract, Stage-2 minimum).

    Returns a non-empty PDF-like byte blob containing the form's BMG §30
    Pflichtangaben as ASCII text. The blob starts with the ``%PDF-1.4``
    magic so the operator's download manager and ``file(1)`` recognise
    it as a PDF; the full xref/trailer object structure (xrefs, trailer
    dictionary, cross-reference streams) is added by a future Stage-3
    reportlab-based renderer that does not block F5.

    The CLI handler in ``kurort_engine.__init__:_handle_meldeschein_checkin``
    reads the JSON-stdin payload, builds a ``MeldescheinForm``, calls this
    function, writes the returned bytes to ``--output-file`` (default
    ``./meldeschein.pdf``), and prints a one-line confirmation to stdout.
    """
    return (
        b"%PDF-1.4\n"
        b"% Kurort-vertical Meldeschein PDF (Stage-2 minimum, "
        b"see F5 AC-1 spec at repo/spec.yaml:88-98)\n"
        b"% Familienname: " + form.familienname.encode("utf-8") + b"\n"
        b"% Vorname: " + form.vorname.encode("utf-8") + b"\n"
        b"% Geburtsdatum: " + form.geburtsdatum.isoformat().encode("utf-8") + b"\n"
        b"% Staatsangehoerigkeit: " + form.staatsangehoerigkeit.encode("utf-8") + b"\n"
        b"% Anschrift: " + form.anschrift.encode("utf-8") + b"\n"
        b"% Anreisedatum: " + form.anreisedatum.isoformat().encode("utf-8") + b"\n"
        b"% Abreisedatum: " + form.abreisedatum.isoformat().encode("utf-8") + b"\n"
        b"%EOF\n"
    )


def generate_avv_markdown(processing_record: ProcessingRecord) -> str:
    """Render the DSGVO Art. 28 (3) AVV Markdown (AC-2 contract).

    Placeholder. The real implementation lives in
    ``kurort_engine.meldeschein.avv_generator.generate_avv_markdown`` and is
    added in Phase 4 green.
    """
    raise NotImplementedError(
        "avv_generator.generate_avv_markdown is a Stage-1 placeholder; the "
        "real AVV generator ships in Phase 4 green per plan.md"
    )


def scan_booking_flow(html_bytes: bytes) -> dict:
    """Scan a booking-flow HTML for BFSG-WCAG-2.1-AA violations (AC-3 contract).

    Placeholder. The real implementation lives in
    ``kurort_engine.meldeschein.bfsg_scanner.scan_booking_flow`` and is added
    in Phase 4 green.
    """
    raise NotImplementedError(
        "bfsg_scanner.scan_booking_flow is a Stage-1 placeholder; the real "
        "BFSG scanner ships in Phase 4 green per plan.md"
    )


# ---------------------------------------------------------------------------
# ID helper (kept here for the Stage-1 public API; per-AC ID formats are
# introduced in Phase 4 green when the per-renderer modules land).
# ---------------------------------------------------------------------------


def _form_id() -> str:
    """Generate a MeldescheinForm ID with the 'msch-<uuid8>' format."""
    return f"msch-{uuid.uuid4().hex[:8]}"


__all__ = [
    # Schemas (AC-1, AC-2)
    "MeldescheinForm",
    "ProcessingRecord",
    # Exception classes (AC-1, AC-2, AC-3)
    "MeldescheinValidationError",
    "AVVValidationError",
    "BFSGScannerInputError",
    # Renderer entry points (AC-1, AC-2, AC-3)
    "render",
    "generate_avv_markdown",
    "scan_booking_flow",
]
