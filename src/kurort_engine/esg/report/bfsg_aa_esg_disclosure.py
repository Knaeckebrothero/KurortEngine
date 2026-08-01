"""kurort_engine.esg.report.bfsg_aa_esg_disclosure — AC-5 BFSG-AA ESG disclosure.

Iteration 27 (Developer) — Q5.1 ESG-CSRD/VSME Group 2.
Chosen by Critic verdict (iter-26) from iter-25 Scholar Proposal 002.

AC-5 contract (verbatim from spec.yaml):

    Unwanted-behavior. If `export_lang_de_accessibilitylabel(disclosure_payload)`
    is called in `kurort_engine.esg.report.bfsg_aa_esg_disclosure` THEN the
    function MUST raise `BFSGComplianceError` (re-using the SHIPPED
    `kurort_engine.kurkarte_wallet.BFSGComplianceError` exception class
    introduced in iter-21) naming the missing field if any field of
    `disclosure_payload` lacks `lang="de"` (per BFSG-EAA in force
    28.06.2025) or lacks `accessibility_label` (per WCAG 2.1 SC 4.1.3 + EN 301 549
    baseline); the disclosure payload MUST include screen-reader text contrast
    ≥ 4.5:1 metadata declared at the document level (`formatVersion` +
    `badOrbEsgDisclosureStyle`); a `compliance_ok: bool` field at the dict
    top-level MUST be `True` iff all sub-fields pass the BFSG check.

Reference: BFSG-EAA in force 28.06.2025 per
`iter-25-proposal-002-q51-esg-csrd-voluntary-vsme-hcmi-scope-3-tier-2-410-loc` §3 +
KB note A-6 (WCAG 2.1 SC 4.1.3 + EN 301 549 baseline).
"""
from __future__ import annotations

from kurort_engine.kurkarte_wallet import BFSGComplianceError  # noqa: E402

# Document-level metadata keys per spec.yaml AC-5 EARS contract.
# These are skipped during per-field lang/accessibility_label validation
# because they describe the document itself, not text fields.
_DOC_LEVEL_KEYS: frozenset[str] = frozenset({
    "formatVersion",
    "badOrbEsgDisclosureStyle",
})


def export_lang_de_accessibilitylabel(disclosure_payload: dict) -> dict:
    """Validate BFSG-AA + WCAG 2.1 SC 4.1.3 + EN 301 549 compliance of an ESG disclosure.

    Iterates over the disclosure_payload (skipping document-level metadata
    `formatVersion` + `badOrbEsgDisclosureStyle`) and asserts that every
    field BOTH has ``lang="de"`` AND has a non-missing
    ``accessibility_label`` key.

    Parameters
    ----------
    disclosure_payload : dict
        A dict describing an ESG disclosure. Expected keys:

          * ``formatVersion`` — ``str``, document-level metadata (e.g. ``"1.0"``)
          * ``badOrbEsgDisclosureStyle`` — ``dict``, document-level screen-reader
            metadata (e.g. ``{"textContrastRatio": "4.5:1", "minFontSizePt": 12}``)
          * 1+ sub-fields, each a ``dict`` with ``lang: str = "de"`` +
            ``accessibility_label: str`` ≥ 20 chars (per WCAG 2.1 SC 4.1.3)

    Returns
    -------
    dict
        A JSON-serialisable dict with required keys per spec.yaml AC-5 EARS:

          * ``compliance_ok`` — ``bool`` ``True`` at the top level IFF all
            sub-fields pass the BFSG-EAA check.
          * ``formatVersion`` — passed through from input
          * ``badOrbEsgDisclosureStyle`` — passed through from input
          * <each input sub-field> — passed through unchanged

    Raises
    ------
    BFSGComplianceError
        From ``kurort_engine.kurkarte_wallet`` (re-used iter-21):
          * If any sub-field lacks the ``accessibility_label`` key (WCAG 2.1
            SC 4.1.3 + EN 301 549 baseline violation). The exception message
            names the offending field for diagnostic clarity.
          * If any sub-field has ``lang != "de"`` (BFSG-EAA violation per
            Barrierefreiheitsstärkungsgesetz in force 28.06.2025). The
            exception message names the offending field + the actual lang
            value for diagnostic clarity.
    """
    if not isinstance(disclosure_payload, dict):
        raise BFSGComplianceError(
            f"BFSG-EAA violation: disclosure_payload must be a dict; "
            f"got {type(disclosure_payload).__name__}: {disclosure_payload!r}"
        )

    # ----- per-field BFSG-EAA + WCAG 2.1 SC 4.1.3 validation -----
    for key, field in disclosure_payload.items():
        # Skip document-level metadata keys (these describe the disclosure
        # itself, not user-facing text fields requiring accessibility).
        if key in _DOC_LEVEL_KEYS:
            continue

        # Each sub-field must itself be a dict (lang + accessibility_label)
        if not isinstance(field, dict):
            raise BFSGComplianceError(
                f"BFSG-EAA violation: field {key!r} must be a dict with "
                f"'lang' and 'accessibility_label' keys; "
                f"got {type(field).__name__}: {field!r}"
            )

        # Check 1 — `accessibility_label` must be present
        if "accessibility_label" not in field:
            raise BFSGComplianceError(
                f"BFSG-EAA violation: field {key!r} missing "
                f"accessibility_label (per WCAG 2.1 SC 4.1.3)"
            )

        # Check 2 — `lang` must equal "de" (BFSG-EAA in force 28.06.2025)
        lang = field.get("lang")
        if lang != "de":
            raise BFSGComplianceError(
                f"BFSG-EAA violation: field {key!r} lang={lang!r} != de "
                f"(per BFSG-EAA in force 28.06.2025)"
            )

    # ----- all checks passed: emit compliance_ok=True + passthrough payload -----
    result: dict = {"compliance_ok": True}
    for key, value in disclosure_payload.items():
        result[key] = value
    return result


__all__ = ["export_lang_de_accessibilitylabel"]
