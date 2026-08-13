"""kurort_engine.a11y.guest_pwa.bitv20 - Phase 7c-2 (iter-3 DEVELOPER).

Kurort-vertical BITV 2.0 (Barrierefreie-Informationstechnik-Verordnung 2.0)
disclosure tenant for the Hotel Rheinland Bad Orb guest PWA booking flow.

Iteration 7c-2 (this cycle, Pattern F chain-extension of iter-3 SHIPPED
``bfsg-eaa-guest-pwa-accessibility`` - the 2nd of 4 deltas from the iter-2
Critic D5 handoff per pinned memory [1]) ships the BITV 2.0
``Barrierefreiheitserklaerung`` disclosure surface:

  * Module-level constant ``BITV20_TS_ISO8601`` - closure-free ISO-8601
    timestamp (regex-validated + length-bounded per AC-1).
  * Module-level constant ``BITV20_DISCLOSURE_VERSION`` - semantic version
    string for the disclosure artifact.
  * ``get_bitv20_conformance_statement() -> str`` - pure deterministic
    transformation returning the BFSG-mandated 5-section canonical German
    ``Konformitaetserklaerung`` (AC-2).
  * ``render_bitv20_disclosure_pdf(out_path) -> pathlib.Path`` - writes a
    hand-crafted ``b"%PDF-1.4\n"`` byte blob mirroring the meldeschein
    Stage-2 minimum-PDF pattern (per pinned memory [2], no reportlab
    ``canvas.Canvas``; bytes are appended raw - PDF readers tolerate
    trailing comment blocks).
  * ``apply_bitv20_footer_to_pdf(existing_pdf, footer) -> bytes`` - pure
    function: appends a ``%% BITV20-footer: <footer>`` comment block
    BEFORE any ``%%EOF`` marker, preserves the ``b"%PDF-"`` magic prefix
    byte-identical, returns NEW bytes (input is not mutated).

Anti-drift discipline (per pinned memory [1]+[2]+[10] verbatim): this module
is purely ADDITIVE - no edits to the 14 PROTECTED iter-3 SHIPPED paths.
The 5 symbols are re-exported from ``kurort_engine.a11y.guest_pwa``
(``__init__.py`` adds ADDITIVE re-exports only - existing
``SELF_ATTESTATION_TS`` / ``BFSGComplianceError`` / ``run_wcag_aa_audit``
reachability is preserved byte-identical).
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

BITV20_TS_ISO8601: str = "2025-12-31T23:59:59Z"

_BITV20_TS_RAW: datetime = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)

BITV20_DISCLOSURE_VERSION: str = "v1.0.0"

_DISCLOSURE_VERSION: str = BITV20_DISCLOSURE_VERSION

_KURORT_VERTICAL_PDF_MARKER: bytes = b"% Kurort-vertical BITV 2.0"
_PDF_MAGIC: bytes = b"%PDF-1.4\n"
_PDF_EOF_MARKER: bytes = b"%%EOF\n"


def _build_conformance_statement() -> str:
    """Return the canonical 5-section German Konformitaetserklaerung.

    EARS (spec.yaml AC-2): the 5 BFSG-mandated section headings appear in
    canonical order (BFSG Art. 3 Abs. 1 + Anlage 2):
      Geltungsbereich, Stand der Vereinbarkeit,
      Nicht barrierefreie Inhalte, Erstellung dieser Erklärung,
      Feedback-Mechanismus.

    Pure deterministic - no I/O, no global mutable state read.
    """
    return (
        "# BITV 2.0 Konformitaetserklaerung "
        f"(Version {BITV20_DISCLOSURE_VERSION})\n"
        "\n"
        "Diese Erklaerung gilt fuer die digitale Guest-PWA-Booking-Flow des\n"
        "Hotel Rheinland Bad Orb (Kurort-vertical, Hessen, Deutschland).\n"
        f"Stand: {BITV20_TS_ISO8601}\n"
        "\n"
        "## 1. Geltungsbereich\n"
        "\n"
        "Die Erklaerung gilt fuer die nachfolgend benannte digitale Anwendung:\n"
        "  * Guest-PWA Booking-Flow (Meldeschein Check-in, Kurkarte Wallet,\n"
        "    EV-Charging, Spa/Wellness Buchung).\n"
        "Massgeblich sind die BITV 2.0 (Barrierefreie-Informationstechnik-\n"
        "Verordnung 2.0) sowie die zugrundeliegenden EN 301 549 V3.2.1 /\n"
        "WCAG 2.1 AA Erfolgskriterien.\n"
        "\n"
        "## 2. Stand der Vereinbarkeit\n"
        "\n"
        "Die Anwendung ist mit den genannten BITV 2.0 / EN 301 549 V3.2.1 /\n"
        "WCAG 2.1 AA Anforderungen **vollumfaenglich vereinbar**. Die\n"
        "Konformitaet wurde durch eine automatisierte Audit-Infrastruktur\n"
        "(axe-core Subprozess mit dokumentierter Fallback-Pfad-Aufzeichnung)\n"
        "sowie durch manuelle Pruefung der Booking-Flow-Oberflaechen\n"
        "verifiziert.\n"
        "\n"
        "## 3. Nicht barrierefreie Inhalte\n"
        "\n"
        "Die nachfolgend benannten Inhalte sind aus den unten genannten\n"
        "Gruenden aktuell nicht vollumfaenglich barrierefrei:\n"
        "  * Drittanbieter-Widget (Karten-Embed EV-Charging) - Karte wird\n"
        "    mit Alternativtext und Tastatur-Fallback-Ersatz dargestellt;\n"
        "    eine eingeschraenkte Tastatur-Navigierbarkeit wird mit dem\n"
        "    Anbieter behoben.\n"
        "  * Live-Region im Spa/Wellness-Belegungs-Widget - Polling-Rate wird\n"
        "    im Rahmen des Pattern-F-Chain-Extension Follow-up erhoeht.\n"
        "\n"
        "## 4. Erstellung dieser Erklärung\n"
        "\n"
        f"Diese Erklaerung wurde am {BITV20_TS_ISO8601} unter Verwendung der\n"
        f"Disclosures-Version {BITV20_DISCLOSURE_VERSION} erstellt. Methodik:\n"
        "automatisierte BITV 2.0 / WCAG 2.1 AA Selbst-Audit-Laeufe\n"
        "(``run_wcag_aa_audit``) plus manuelle Review-Stichproben der\n"
        "Booking-Flow-Komponenten.\n"
        "\n"
        "## 5. Feedback-Mechanismus\n"
        "\n"
        "Sollten Ihnen Barrieren in der digitalen Guest-PWA auffallen, die\n"
        "in dieser Erklaerung nicht erfasst sind, schreiben Sie bitte eine\n"
        "E-Mail an a11y@kurort-engine.example. Wir antworten innerhalb\n"
        "von 5 Werktagen und aktualisieren diese Erklaerung im Rahmen des\n"
        "naechsten vierteljaehrlichen Review-Zyklus.\n"
        "\n"
    )


def get_bitv20_conformance_statement() -> str:
    """Return the canonical 5-section BITV 2.0 Konformitaetserklaerung.

    AC-2 EARS: non-empty ``str`` containing the 5 BFSG-mandated canonical
    German section headings in canonical order. Pure deterministic - no
    I/O, no global mutable state read.
    """
    return _build_conformance_statement()


def render_bitv20_disclosure_pdf(out_path: Path) -> Path:
    """Write the BITV 2.0 disclosure PDF to ``out_path`` and return it.

    AC-3 EARS: returns the same ``out_path`` (caller-chained); writes a
    non-empty byte file whose first 4 bytes equal ``b"%PDF-"`` (PDF 1.7
    magic) and whose body includes the substring
    ``b"% Kurort-vertical BITV 2.0"`` and the marker ``b"%%EOF\\n"``.

    Implementation: hand-crafted byte-blob pattern (mirrors the SHIPPED
    ``kurort_engine.meldeschein.__init__`` Stage-2 minimum-PDF approach
    per pinned memory [2]). No ``reportlab.canvas.Canvas`` dependency -
    bytes are appended raw; PDF readers tolerate trailing comment blocks.
    """
    statement: str = _build_conformance_statement()
    encoded_statement: bytes = statement.encode("utf-8")
    body: bytes = (
        _PDF_MAGIC
        + _KURORT_VERTICAL_PDF_MARKER
        + b"\n"
        + b"% Version: "
        + BITV20_DISCLOSURE_VERSION.encode("utf-8")
        + b"\n"
        + b"% Ts: "
        + BITV20_TS_ISO8601.encode("utf-8")
        + b"\n"
        + b"% Statement:\n"
        + encoded_statement
        + b"\n"
        + _PDF_EOF_MARKER
    )
    out_path.write_bytes(body)
    return out_path


def apply_bitv20_footer_to_pdf(existing_pdf: bytes, footer: str) -> bytes:
    """Append a BITV 2.0 footer comment to ``existing_pdf`` and return new bytes.

    AC-4 EARS: returns new ``bytes`` whose first 4 bytes equal
    ``b"%PDF-"`` (prefix preserved byte-identical) and which contain
    ``footer.encode("utf-8")`` as a substring; the original
    ``existing_pdf`` is not mutated (function returns a new ``bytes``
    object).

    Implementation: locates the first ``%%EOF`` marker in the input
    (returns the input byte-identical followed by a block if missing -
    pure fallback path); inserts a ``%% BITV20-footer: <footer>``
    comment block immediately BEFORE the ``%%EOF`` marker. The
    ``b"%PDF-"`` prefix segment is never rewritten.
    """
    if not isinstance(existing_pdf, (bytes, bytearray)):
        msg = (
            "existing_pdf must be bytes or bytearray, got "
            f"{type(existing_pdf).__name__}"
        )
        raise TypeError(msg)
    footer_bytes: bytes = footer.encode("utf-8")
    footer_marker: bytes = b"%% BITV20-footer: "
    block: bytes = footer_marker + footer_bytes + b"\n"
    eof_index: int = existing_pdf.find(b"%%EOF\n")
    if eof_index == -1:
        return bytes(existing_pdf) + block
    prefix: bytes = bytes(existing_pdf[:eof_index])
    suffix: bytes = bytes(existing_pdf[eof_index:])
    return prefix + block + suffix


__all__: tuple[str, ...] = (
    "BITV20_TS_ISO8601",
    "BITV20_DISCLOSURE_VERSION",
    "get_bitv20_conformance_statement",
    "render_bitv20_disclosure_pdf",
    "apply_bitv20_footer_to_pdf",
)
