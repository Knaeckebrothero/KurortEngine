# spec_lock.md - a11y-guest-pwa-bitv20-disclosure
# Kurort-vertical BITV 2.0 disclosure for the Hotel Rheinland Bad Orb guest PWA booking flow.
# Phase 7c-2 | Owner: Developer

**Feature:** `a11y-guest-pwa-bitv20-disclosure` **Iteration:** 7c-2 **Owner:** Developer
**Locked at:** 2026-07-12T00:00:00Z
**Locked spec SHA-256:** `f2ab069c7ff26b65b719ee91a7b019d6825ac76054cf30c7db9020dbd527211d`
**AC block byte length:** 3433 bytes **AC block SHA-256:** `48d5fe7fb2ab1f37a7c705f5049c4cfe6a98553c87405b90b8338073fadb18ca`

**Predecessor (Phase 7c-2 of D5 deltas - the binding contract):**
iter-3 SHIPPED `bfsg-eaa-guest-pwa-accessibility` (commit `416aa5d1`, HEAD
`5ec785edd9cebd80f5c0474ef0b2af915f4a74dd`, `repo/spec/a11y_guest_pwa/spec.lock.md`
SHA-256 `525868a460c5bdc40c387dfec6f2f75c4d009fe8b6a321d7f4546d62117217ff`).
Phase 7c-2 picks the smallest concrete follow-up from the 4 Critic D5 deltas:
BITV 2.0 standardized-text + PDF + footer-stamping helpers that mirror the
SHIPPED `wcag_aa.py + self_attest.py` 3-module pattern. Mix B SAFE (no Lawyer
dependency - BITV 2.0 paragraph text is BFSG-mandated verbatim). Pattern F
chain-extension: ADDITIVE re-export onto the SHIPPED `a11y/guest_pwa/__init__.py`
only - `kurort_engine/__init__.py` is byte-identical preserved.

Module surface (Phase 7c-2 GREEN additive - no SHIPPED module edits):
CREATE `repo/src/kurort_engine/a11y/guest_pwa/bitv20.py` (NEW - 5 public symbols)
+ EDIT `repo/src/kurort_engine/a11y/guest_pwa/__init__.py` (ADDITIVE re-exports
of the 5 BITV 2.0 symbols beside existing `SELF_ATTESTATION_TS`,
`BFSGComplianceError`, `run_wcag_aa_audit`) + CREATE `repo/tests/test_a11y_guest_pwa_bitv20.py`
(NEW - 5 tests, 1 per AC) + EDIT `repo/README.md` (APPEND - BITV 2.0 disclosure
section). Anti-drift discipline: 14 PROTECTED files (10 SHAs + spec.lock.md SHA
+ iter-3 SHIPPED test file + pyproject.toml deps + kurort_engine/__init__.py
65-symbol byte-identical re-export list) at iter-3 close all preserved
byte-identical. `git diff HEAD~1 --stat` MUST NOT show changes to any of the 14
protected files. ONLY `bitv20.py` (NEW) + `__init__.py` (ADDITIVE re-exports)
+ test file (NEW) + README.md (APPEND) modified.

---

## Warning PROTECTED Acceptance Criteria Warning

> **DO NOT EDIT THIS SECTION MID-ITERATION.**
>
> The 5 acceptance criteria below are the binding contract for iteration 7c-2.
> They are copied verbatim from `spec.yaml` and hashed at lock time. If a
> criterion turns out to be wrong, contradictory, or impossible, the correct
> response is to emit `BLOCKED: <reason>` or `ABORT: <reason>` and surface it
> to the strategic phase - NOT to weaken the AC.
>
> Permitted edits to this file are limited to:
> 1. The `## Traceability Matrix` section (status updates per red/green phase).
> 2. The `## Lock metadata` section (lock extensions / spec_version bumps).
>
> Any edit to this PROTECTED section requires a new `spec.yaml` SHA and a
> new entry in the `## Lock metadata` section recording the override
> rationale.

---

## Acceptance Criteria

The 5 EARS-format ACs below are copied verbatim from `spec.yaml`
`acceptance_criteria:` (3433 bytes, SHA-256 `48d5fe7fb2ab1f37a7c705f5049c4cfe6a98553c87405b90b8338073fadb18ca`) - the
byte-identical AC block MUST round-trip through this fence without any
rstrip/strip (per pinned memory [1] iter-3 phase-1 lesson).

```yaml
acceptance_criteria:
  - id: AC-1
    ears: >-
      Where `kurort_engine.a11y.guest_pwa.bitv20` is imported, the system
      shall expose a module-level string constant named
      `BITV20_TS_ISO8601` whose value matches the ISO-8601 timezone-aware
      regex `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$`
      and whose length is in the closed interval [20, 35] (covering the
      canonical `2025-12-31T23:59:59Z` form plus per-locale ±HH:MM offsets).
    test_oracle: >-
      repo/tests/test_a11y_guest_pwa_bitv20.py::test_ac1_bitv20_ts_iso8601_constant

  - id: AC-2
    ears: >-
      When `get_bitv20_conformance_statement()` is called with no
      arguments, the system shall return a non-empty `str` that contains
      (each as a substring or quoted section heading) the 5 BFSG-mandated
      section headings in canonical German: `"Geltungsbereich"`,
      `"Stand der Vereinbarkeit"`, `"Nicht barrierefreie Inhalte"`,
      `"Erstellung dieser Erklärung"`, `"Feedback-Mechanismus"` — in
      the order specified above; the function shall be a pure deterministic
      transformation (no I/O, no global mutable state read).
    test_oracle: >-
      repo/tests/test_a11y_guest_pwa_bitv20.py::test_ac2_get_bitv20_conformance_statement_contains_5_sections

  - id: AC-3
    ears: >-
      When `render_bitv20_disclosure_pdf(out_path)` is called with a
      `pathlib.Path` argument, the system shall write a non-empty byte
      file whose first 4 bytes equal the literal ASCII bytes `b"%PDF-"`
      (PDF 1.7 magic) and whose body includes the substring
      `b"% Kurort-vertical BITV 2.0"` and the marker `b"%%EOF\n"`; the
      function shall return the same `out_path` value passed in.
    test_oracle: >-
      repo/tests/test_a11y_guest_pwa_bitv20.py::test_ac3_render_bitv20_disclosure_pdf_magic_prefix

  - id: AC-4
    ears: >-
      While `apply_bitv20_footer_to_pdf(existing_pdf, footer)` is called
      with `bytes` whose first 4 bytes equal `b"%PDF-"`, the system
      shall return new `bytes` that also start with the literal bytes
      `b"%PDF-"` (prefix preserved byte-identical, NOT rewritten) and
      contain `footer.encode("utf-8")` as an ASCII substring within the
      output; the original `existing_pdf` shall not be mutated (function
      shall return a new `bytes` object — not modify in place).
    test_oracle: >-
      repo/tests/test_a11y_guest_pwa_bitv20.py::test_ac4_apply_bitv20_footer_to_pdf_preserves_pdf_magic

  - id: AC-5
    ears: >-
      When `import kurort_engine.a11y.guest_pwa` is executed, the system
      shall expose the 5 BITV 2.0 symbols `{BITV20_TS_ISO8601,
      BITV20_DISCLOSURE_VERSION, get_bitv20_conformance_statement,
      render_bitv20_disclosure_pdf, apply_bitv20_footer_to_pdf}` as
      importable attributes (each accessible via `hasattr(package, name)`)
      — and the existing iter-3 SHIPPED symbols `SELF_ATTESTATION_TS`,
      `BFSGComplianceError`, `run_wcag_aa_audit` shall remain reachable at
      the same binding (ADDITIVE re-exports only, no rewrites).
    test_oracle: >-
      repo/tests/test_a11y_guest_pwa_bitv20.py::test_ac5_bitv20_symbols_re_exported_from_guest_pwa

# -----------------------------------------------------------------------------
# not_included — explicit scope boundaries (anti-drift + scope-disc)
# -----------------------------------------------------------------------------

```

---

## Traceability Matrix

| AC   | brief                              | status      | phase       | test_oracle                                                                                  |
|------|------------------------------------|-------------|-------------|----------------------------------------------------------------------------------------------|
| AC-1 | BITV20_TS_ISO8601 constant          | spec_complete | spec        | `repo/tests/test_a11y_guest_pwa_bitv20.py::test_ac1_bitv20_ts_iso8601_constant`               |
| AC-2 | 5-section Konformitetserklaerung    | spec_complete | spec        | `repo/tests/test_a11y_guest_pwa_bitv20.py::test_ac2_get_bitv20_conformance_statement_contains_5_sections` |
| AC-3 | render BitV 2.0 disclosure PDF      | spec_complete | spec        | `repo/tests/test_a11y_guest_pwa_bitv20.py::test_ac3_render_bitv20_disclosure_pdf_magic_prefix` |
| AC-4 | apply BitV 2.0 footer preserves prefix | spec_complete | spec        | `repo/tests/test_a11y_guest_pwa_bitv20.py::test_ac4_apply_bitv20_footer_to_pdf_preserves_pdf_magic` |
| AC-5 | re-export 5 symbols from guest_pwa | spec_complete | spec        | `repo/tests/test_a11y_guest_pwa_bitv20.py::test_ac5_bitv20_symbols_re_exported_from_guest_pwa` |

---

## Lock metadata

| field                  | value                                                                                  |
|------------------------|----------------------------------------------------------------------------------------|
| feature                | `a11y-guest-pwa-bitv20-disclosure`                                                     |
| iteration              | `7c-2`                                                                                 |
| owner                  | developer                                                                              |
| locked_at              | `2026-07-12T00:00:00Z`                                                                  |
| spec_yaml_path         | `repo/spec/a11y_guest_pwa_bitv20_disclosure/spec.yaml`                                  |
| spec_sha256            | `725cfd94f57115294330dedb5494eda5187780c4f8dfe2e225fde8e5bb780bcf`                                                                           |
| ac_block_byte_length   | 3433 bytes                                                                   |
| ac_block_sha256        | `48d5fe7fb2ab1f37a7c705f5049c4cfe6a98553c87405b90b8338073fadb18ca`                                                                       |
| predecessor            | iter-3 SHIPPED `bfsg-eaa-guest-pwa-accessibility` (commit `416aa5d1`)                  |
| protected_files_count  | 14                                                                                     |
| tdd_phase              | spec                                                                                   |
| next_phase             | red (5 failing tests, 1 per AC; must FAIL with AssertionError, NOT ImportError)         |
