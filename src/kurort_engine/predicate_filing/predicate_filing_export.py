"""kurort_engine.predicate_filing.predicate_filing_export — AC-4.

Iter-33 Developer. Tier-2 chain-extension.

Provides ``export_predicate_filing_bfsg_aa(predicate_packet, narrative,
lang="de", accessibility_label="")`` which returns a JSON-serializable
dict describing the BFSG-AA compliant predicate filing disclosure.

Per AC-4 (Unwanted-behavior): the function MUST raise
:class:`kurort_engine.kurkarte_wallet.BFSGComplianceError` (re-used from
SHIPPED iter-21) naming the missing field if ``lang != "de"`` (per BFSG-EAA
in force 28.06.2025) OR if ``len(accessibility_label) < 20`` (per WCAG 2.1
SC 4.1.3 + EN 301 549 baseline).

On the happy path the function MUST return a dict with required keys:
  * ``predicate_packet: dict`` (verbatim input)
  * ``narrative: dict`` (verbatim input)
  * ``lang: str = "de"``
  * ``accessibility_label: str`` ≥ 20 chars
  * ``screen_reader_contrast: str = "4.5:1"`` (WCAG 2.1 AA)
  * ``compliance_ok: bool = True`` (iff all sub-fields pass the BFSG check)
  * ``non_affirmation_footer: str`` containing the verbatim clause "This ESG
    and Heilbad 2036 predicate filing is voluntary and is provided as
    ESG-readiness and predicate-renewal positioning for Bad Orb Kur GmbH;
    it is NOT a regulatory compliance attestation"
"""
from __future__ import annotations

from typing import Any

# Re-use the SHIPPED iter-21 BFSGComplianceError exception class so callers
# can catch either ``kurort_engine.kurkarte_wallet.BFSGComplianceError`` or
# this module's re-export.
from kurort_engine.kurkarte_wallet import BFSGComplianceError  # noqa: E402,F401

# Constants — verbatim clause per spec.yaml A-4 + AC-4 verbatim.
_NON_AFFIRMATION_FOOTER: str = (
    "This ESG and Heilbad 2036 predicate filing is voluntary and is provided "
    "as ESG-readiness and predicate-renewal positioning for Bad Orb Kur GmbH; "
    "it is NOT a regulatory compliance attestation"
)

# BFSG-EAA primary language (AC-4 verbatim: lang MUST be "de").
_DEFAULT_LANG: str = "de"

# Minimum accessibility_label length per WCAG 2.1 SC 4.1.3 + EN 301 549.
_MIN_ACCESSIBILITY_LABEL_CHARS: int = 20

# Screen-reader text contrast ≥ 4.5:1 metadata (WCAG 2.1 AA).
_SCREEN_READER_CONTRAST: str = "4.5:1"


def export_predicate_filing_bfsg_aa(
    predicate_packet: dict[str, Any],
    narrative: dict[str, Any],
    lang: str = _DEFAULT_LANG,
    accessibility_label: str = "",
) -> dict[str, Any]:
    """Export the BFSG-AA compliant predicate filing disclosure.

    Per AC-4 (Unwanted-behavior): raises
    :class:`BFSGComplianceError` (re-used from SHIPPED iter-21
    ``kurort_engine.kurkarte_wallet``) naming the missing field if
    ``lang != "de"`` OR if ``len(accessibility_label) < 20``.

    On the happy path the function MUST return a dict with required keys
    including the verbatim ``non_affirmation_footer`` clause.
    """
    # BFSG-EAA primary language check (AC-4 verbatim)
    if lang != _DEFAULT_LANG:
        raise BFSGComplianceError(
            f"BFSG-EAA compliance violation: lang={lang!r} is not 'de' "
            f"(per BFSG-EAA in force 28.06.2025); the 'lang' field must be "
            f"'de' for the predicate filing disclosure."
        )

    # WCAG 2.1 SC 4.1.3 + EN 301 549 accessibility_label length check (AC-4)
    if len(accessibility_label) < _MIN_ACCESSIBILITY_LABEL_CHARS:
        raise BFSGComplianceError(
            f"BFSG-EAA compliance violation: accessibility_label length "
            f"{len(accessibility_label)} is less than the "
            f"{_MIN_ACCESSIBILITY_LABEL_CHARS}-char minimum required by "
            f"WCAG 2.1 SC 4.1.3 + EN 301 549 baseline; the "
            f"'accessibility_label' field must be at least "
            f"{_MIN_ACCESSIBILITY_LABEL_CHARS} characters for screen-reader "
            f"compatibility."
        )

    return {
        "predicate_packet": dict(predicate_packet),
        "narrative": dict(narrative),
        "lang": lang,
        "accessibility_label": accessibility_label,
        "screen_reader_contrast": _SCREEN_READER_CONTRAST,
        "compliance_ok": True,
        "non_affirmation_footer": _NON_AFFIRMATION_FOOTER,
    }