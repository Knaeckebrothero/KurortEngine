"""AC-* test oracle for kurort_engine.a11y.guest_pwa.bitv20 (Phase 7c-2 RED).

Test oracle paths recorded in
``repo/spec/a11y_guest_pwa_bitv20_disclosure/spec.yaml``:

  AC-1 test_ac1_bitv20_ts_iso8601_constant
  AC-2 test_ac2_get_bitv20_conformance_statement_contains_5_sections
  AC-3 test_ac3_render_bitv20_disclosure_pdf_magic_prefix
  AC-4 test_ac4_apply_bitv20_footer_to_pdf_preserves_pdf_magic
  AC-5 test_ac5_bitv20_symbols_re_exported_from_guest_pwa

Each test starts with ``_require_bitv20_module()`` pre-check; if the
``bitv20`` submodule is missing, the test fails with ``pytest.fail`` raising
an ``AssertionError`` (per iter-15 l13-004 + iter-28 test convention:
AssertionError-not-ImportError verification protocol;
Phase 7c-2 follows the same discipline).

Phase 7c-2 RED NOTE: each test asserts a post-condition that the Phase 4
GREEN implementation must satisfy. Against the iter-3 SHIPPED baseline (no
``bitv20`` submodule yet — `kurort_engine.a11y.guest_pwa` exists, but
``kurort_engine.a11y.guest_pwa.bitv20`` does NOT), the tests fail with
``AssertionError`` (NOT ``ImportError``, NOT ``ModuleNotFoundError``, NOT
``SyntaxError``, NOT ``CollectionError``). This proves the test reaches its
assertion surface — the failure mode is honest.

AC-5 differs: it imports ``kurort_engine.a11y.guest_pwa`` (the SHIPPED
package) directly. The FAIL comes from the ``hasattr(package, name)``
assertion surface evaluating to ``False`` for each missing BITV 2.0 symbol.
This is clean ``AssertionError`` — no pre-check helper needed.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Pre-check helper: AssertionError-not-ImportError protocol (pinned memory [1])
# ---------------------------------------------------------------------------


def _require_bitv20_module() -> None:
    """Fail with AssertionError if the bitv20 submodule is not importable.

    Mirrors the SHIPPED ``_require_a11y_guest_pwa_module`` pattern from
    ``repo/tests/test_a11y_guest_pwa.py:34-51`` (iter-3 Phase 2 RED).
    Per iter-15 l13-004 + iter-28 test convention: AssertionError-not-ImportError.
    We wrap ``find_spec`` in try/except because ``find_spec`` can raise
    ``ModuleNotFoundError`` (not just return ``None``) when a parent namespace
    package is missing — we convert that to ``pytest.fail`` so the failure
    mode is ``AssertionError`` (not ``ModuleNotFoundError``).
    """
    try:
        spec = importlib.util.find_spec("kurort_engine.a11y.guest_pwa.bitv20")
    except (ModuleNotFoundError, ImportError):
        spec = None
    if spec is None:
        pytest.fail(
            "kurort_engine.a11y.guest_pwa.bitv20 submodule not found — "
            "Phase 4 GREEN pre-check failed (RED phase expects this "
            "AssertionError, not ModuleNotFoundError)"
        )


# ---------------------------------------------------------------------------
# AC-1 contract constants (verbatim from spec.yaml:88-97)
# ---------------------------------------------------------------------------
AC1_ISO8601_REGEX: str = (
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
AC1_LEN_MIN: int = 20
AC1_LEN_MAX: int = 35

# ---------------------------------------------------------------------------
# AC-2 contract constants (verbatim from spec.yaml:99-110)
# ---------------------------------------------------------------------------
AC2_REQUIRED_HEADINGS: tuple[str, ...] = (
    "Geltungsbereich",
    "Stand der Vereinbarkeit",
    "Nicht barrierefreie Inhalte",
    "Erstellung dieser Erklärung",
    "Feedback-Mechanismus",
)

# ---------------------------------------------------------------------------
# AC-3 contract constants (verbatim from spec.yaml:112-121)
# ---------------------------------------------------------------------------
AC3_PDF_MAGIC: bytes = b"%PDF-"
AC3_PDF_BODY_MARKER: bytes = b"% Kurort-vertical BITV 2.0"
AC3_PDF_EOF_MARKER: bytes = b"%%EOF\n"

# ---------------------------------------------------------------------------
# AC-4 contract constants (verbatim from spec.yaml:123-133)
# ---------------------------------------------------------------------------
AC4_FOOTER_TEXT: str = "BITV 2.0 Konformitätserklärung Footer"
AC4_INPUT_PDF: bytes = b"%PDF-1.4\n% test\n%%EOF\n"

# ---------------------------------------------------------------------------
# AC-5 contract constants (verbatim from spec.yaml:135-146)
# ---------------------------------------------------------------------------
AC5_NEW_BITV20_SYMBOLS: tuple[str, ...] = (
    "BITV20_TS_ISO8601",
    "BITV20_DISCLOSURE_VERSION",
    "get_bitv20_conformance_statement",
    "render_bitv20_disclosure_pdf",
    "apply_bitv20_footer_to_pdf",
)
AC5_SHIPPED_PRESERVED_SYMBOLS: tuple[str, ...] = (
    "SELF_ATTESTATION_TS",
    "BFSGComplianceError",
    "run_wcag_aa_audit",
)


# ---------------------------------------------------------------------------
# AC-1: BITV20_TS_ISO8601 constant matches ISO-8601 timezone-aware regex
# ---------------------------------------------------------------------------


def test_ac1_bitv20_ts_iso8601_constant() -> None:
    """AC-1: BITV20_TS_ISO8601 exists and matches ISO-8601 regex + length bound.

    EARS (spec.yaml AC-1):
      Where ``kurort_engine.a11y.guest_pwa.bitv20`` is imported, the system
      shall expose a module-level string constant named ``BITV20_TS_ISO8601``
      whose value matches the ISO-8601 timezone-aware regex
      ``^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d+)?(?:Z|[+-]\\d{2}:\\d{2})$``
      and whose length is in the closed interval [20, 35].
    """
    _require_bitv20_module()

    from kurort_engine.a11y.guest_pwa import bitv20  # noqa: PLC0415

    ts = getattr(bitv20, "BITV20_TS_ISO8601", None)
    assert isinstance(ts, str), (
        f"AC-1: BITV20_TS_ISO8601 must be a str, got {type(ts).__name__}"
    )
    assert re.match(AC1_ISO8601_REGEX, ts), (
        f"AC-1: BITV20_TS_ISO8601={ts!r} must match ISO-8601 regex "
        f"{AC1_ISO8601_REGEX!r}"
    )
    assert AC1_LEN_MIN <= len(ts) <= AC1_LEN_MAX, (
        f"AC-1: BITV20_TS_ISO8601 length {len(ts)} must be in "
        f"[{AC1_LEN_MIN}, {AC1_LEN_MAX}]"
    )


# ---------------------------------------------------------------------------
# AC-2: get_bitv20_conformance_statement contains the 5 BFSG-mandated sections
# ---------------------------------------------------------------------------


def test_ac2_get_bitv20_conformance_statement_contains_5_sections() -> None:
    """AC-2: get_bitv20_conformance_statement returns the 5-section statement.

    EARS (spec.yaml AC-2):
      When ``get_bitv20_conformance_statement()`` is called with no
      arguments, the system shall return a non-empty ``str`` that contains
      (each as a substring or quoted section heading) the 5 BFSG-mandated
      section headings in canonical German: ``"Geltungsbereich"``,
      ``"Stand der Vereinbarkeit"``, ``"Nicht barrierefreie Inhalte"``,
      ``"Erstellung dieser Erklärung"``, ``"Feedback-Mechanismus"`` — in
      the order specified above; the function shall be a pure deterministic
      transformation (no I/O, no global mutable state read).
    """
    _require_bitv20_module()

    from kurort_engine.a11y.guest_pwa.bitv20 import (  # noqa: PLC0415
        get_bitv20_conformance_statement,
    )

    result = get_bitv20_conformance_statement()

    # Post-condition 1: result is a non-empty str (no I/O, no global state).
    assert isinstance(result, str), (
        f"AC-2: get_bitv20_conformance_statement() must return str, "
        f"got {type(result).__name__}"
    )
    assert result.strip() != "", (
        "AC-2: get_bitv20_conformance_statement() must return non-empty str"
    )

    # Post-condition 2: each of the 5 BFSG-mandated headings appears as a
    # substring, in the canonical German order (later index ≥ earlier index).
    pos = 0
    for heading in AC2_REQUIRED_HEADINGS:
        assert heading in result, (
            f"AC-2: result must contain heading {heading!r} in canonical "
            f"order (missing)"
        )
        idx = result.index(heading)
        assert idx >= pos, (
            f"AC-2: heading {heading!r} at index {idx} must appear at or "
            f"after index {pos} (canonical order violation)"
        )
        pos = idx


# ---------------------------------------------------------------------------
# AC-3: render_bitv20_disclosure_pdf writes a valid PDF byte stream
# ---------------------------------------------------------------------------


def test_ac3_render_bitv20_disclosure_pdf_magic_prefix(tmp_path: Path) -> None:
    """AC-3: render_bitv20_disclosure_pdf writes a PDF with %PDF- magic prefix.

    EARS (spec.yaml AC-3):
      When ``render_bitv20_disclosure_pdf(out_path)`` is called with a
      ``pathlib.Path`` argument, the system shall write a non-empty byte
      file whose first 4 bytes equal the literal ASCII bytes ``b"%PDF-"``
      (PDF 1.7 magic) and whose body includes the substring
      ``b"% Kurort-vertical BITV 2.0"`` and the marker ``b"%%EOF\\n"``;
      the function shall return the same ``out_path`` value passed in.
    """
    _require_bitv20_module()

    from kurort_engine.a11y.guest_pwa.bitv20 import (  # noqa: PLC0415
        render_bitv20_disclosure_pdf,
    )

    out = tmp_path / "out.pdf"
    returned = render_bitv20_disclosure_pdf(out)

    # Post-condition 1: function returns the same out_path passed in.
    assert returned == out, (
        f"AC-3: render_bitv20_disclosure_pdf must return the same out_path, "
        f"got {returned!r} expected {out!r}"
    )

    # Post-condition 2: file exists on disk and is non-empty.
    assert out.exists(), f"AC-3: {out} must exist after render"
    assert out.stat().st_size > 0, (
        f"AC-3: {out} must be non-empty, got {out.stat().st_size} bytes"
    )

    body = out.read_bytes()

    # Post-condition 3: PDF 1.7 magic prefix (5-byte ASCII b"%PDF-").
    assert body[:5] == AC3_PDF_MAGIC, (
        f"AC-3: first 5 bytes must be {AC3_PDF_MAGIC!r}, got {body[:5]!r}"
    )

    # Post-condition 4: BITV 2.0 body marker substring.
    assert AC3_PDF_BODY_MARKER in body, (
        f"AC-3: PDF body must include substring {AC3_PDF_BODY_MARKER!r}"
    )

    # Post-condition 5: PDF %%EOF terminator marker.
    assert AC3_PDF_EOF_MARKER in body, (
        f"AC-3: PDF body must include terminator {AC3_PDF_EOF_MARKER!r}"
    )


# ---------------------------------------------------------------------------
# AC-4: apply_bitv20_footer_to_pdf preserves PDF magic + appends footer
# ---------------------------------------------------------------------------


def test_ac4_apply_bitv20_footer_to_pdf_preserves_pdf_magic() -> None:
    """AC-4: apply_bitv20_footer_to_pdf preserves %PDF- prefix + appends footer.

    EARS (spec.yaml AC-4):
      While ``apply_bitv20_footer_to_pdf(existing_pdf, footer)`` is called
      with ``bytes`` whose first 4 bytes equal ``b"%PDF-"``, the system
      shall return new ``bytes`` that also start with the literal bytes
      ``b"%PDF-"`` (prefix preserved byte-identical, NOT rewritten) and
      contain ``footer.encode("utf-8")`` as an ASCII substring within the
      output; the original ``existing_pdf`` shall not be mutated (function
      shall return a new ``bytes`` object — not modify in place).
    """
    _require_bitv20_module()

    from kurort_engine.a11y.guest_pwa.bitv20 import (  # noqa: PLC0415
        apply_bitv20_footer_to_pdf,
    )

    inp = AC4_INPUT_PDF
    out = apply_bitv20_footer_to_pdf(inp, AC4_FOOTER_TEXT)

    # Post-condition 1: PDF magic prefix preserved byte-identical (5-byte slice).
    assert out[:5] == AC3_PDF_MAGIC, (
        f"AC-4: output[:5] must be {AC3_PDF_MAGIC!r}, got {out[:5]!r} "
        f"(PDF magic prefix must be preserved byte-identical)"
    )

    # Post-condition 2: footer text appears as UTF-8 bytes in output.
    footer_bytes = AC4_FOOTER_TEXT.encode("utf-8")
    assert footer_bytes in out, (
        f"AC-4: output must contain footer bytes {footer_bytes!r}"
    )

    # Post-condition 3: original input was NOT mutated (pure function).
    assert inp == AC4_INPUT_PDF, (
        f"AC-4: input must not be mutated, got {inp!r} (expected "
        f"{AC4_INPUT_PDF!r}) — function must return new bytes, not modify "
        f"in place"
    )


# ---------------------------------------------------------------------------
# AC-5: 5 BITV 2.0 symbols re-exported from kurort_engine.a11y.guest_pwa
# ---------------------------------------------------------------------------


def test_ac5_bitv20_symbols_re_exported_from_guest_pwa() -> None:
    """AC-5: 5 BITV 2.0 symbols re-exported; 3 SHIPPED symbols still reachable.

    EARS (spec.yaml AC-5):
      When ``import kurort_engine.a11y.guest_pwa`` is executed, the system
      shall expose the 5 BITV 2.0 symbols ``{BITV20_TS_ISO8601,
      BITV20_DISCLOSURE_VERSION, get_bitv20_conformance_statement,
      render_bitv20_disclosure_pdf, apply_bitv20_footer_to_pdf}`` as
      importable attributes (each accessible via ``hasattr(package, name)``)
      — and the existing iter-3 SHIPPED symbols ``SELF_ATTESTATION_TS``,
      ``BFSGComplianceError``, ``run_wcag_aa_audit`` shall remain reachable
      at the same binding (ADDITIVE re-exports only, no rewrites).
    """
    import kurort_engine.a11y.guest_pwa as gpwa  # noqa: PLC0415

    # Post-condition 1: 5 new BITV 2.0 symbols are importable from the
    # SHIPPED package (ADDITIVE re-exports — pinned memory [2]).
    for sym in AC5_NEW_BITV20_SYMBOLS:
        assert hasattr(gpwa, sym), (
            f"AC-5: kurort_engine.a11y.guest_pwa must expose {sym!r} "
            f"as an importable attribute (ADDITIVE re-export missing)"
        )

    # Post-condition 2: existing iter-3 SHIPPED symbols remain reachable
    # at the same binding (anti-drift — pinned memory [10]).
    for sym in AC5_SHIPPED_PRESERVED_SYMBOLS:
        assert hasattr(gpwa, sym), (
            f"AC-5: pre-existing symbol {sym!r} must remain reachable on "
            f"kurort_engine.a11y.guest_pwa (anti-drift: ADDITIVE only)"
        )
