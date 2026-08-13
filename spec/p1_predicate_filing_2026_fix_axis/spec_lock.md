# SPEC LOCK — p1_predicate_filing_2026_fix_axis

> **PROTECTED LOCK.** The `## Acceptance Criteria` section below is a
> byte-identical copy of the AC block in
> `repo/spec/p1_predicate_filing_2026_fix_axis/spec.yaml` lines 54–217.
> Any modification to this lock is governed by the SHA-256 hash recorded
> in the footer below — drift from `a7353a96...` means the lock has been
> silently weakened or rewritten, and the cycle MUST be paused for review.
>
> **Iteration:** 12 · **Role:** Developer · **Phase:** 1 (Spec)
> **HEAD:** `d2977566`
> **Source spec.yaml SHA-256:** `7971b4d374b9413974d6e26ebde902857a5d0b7a3b2a0a0820c246f81f6f1c47` (15188 bytes, 311 lines)
> **AC block SHA-256 (canonical):** `a7353a96e4a6b32ce41c9feef0041bc7c1f64612a836bc7b879d0d03716c6158` (7985 bytes)

## Acceptance Criteria

The following YAML block is a verbatim copy of `spec.yaml` lines 54–217.
Per pinned memory #2, the canonical AWK pattern
`awk -v N=N '/^```yaml$/{n++; if(n==N){capture=1; next}} /^```$/ && capture{exit} capture{print}' spec_lock.md | sha256sum`
applied with N=1 MUST yield `a7353a96e4a6b32ce41c9feef0041bc7c1f64612a836bc7b879d0d03716c6158` (7985 bytes).

```yaml
acceptance_criteria:

  - id: AC-1
    bug: CF-PF-2026-2 (HIGH)
    ears: >-
      Where a Beglaubigung attestation clause contains unescaped embedded
      quotes ("Kurarzt" attest with embedded "Beihilfe" quote), the
      kurort_engine.predicate_filing.2026_validate.extract_2026_satzung_schema
      function shall extract the clause without silent drop, returning the
      unquoted clause text in the resulting schema dict's
      beglaubigung_attestation_clauses list, and shall raise a
      BFSGComplianceError with diagnostic mentioning "unquoted clause
      extraction" if extraction fails.
    test_oracle: >-
      output/repros/002_beglaubigung_silent_drop_unescaped_clauses.py::test_repro_002a
    spec_phase: spec
    tdd_phase_origin: red
    locked_status: not_started
    notes: >-
      Verifies the iter-11 SHIPPED fix at
      repo/src/kurort_engine/predicate_filing/2026_validate.py:102-108
      (regex accepts both quoted + unquoted Beglaubigung clauses).

  - id: AC-2
    bug: CF-PF-2026-4 (HIGH)
    ears: >-
      When kurort_engine.predicate_filing.2026_validate.load_2026_profile
      is called with a profile whose period or reprdikatisierung_window
      attribute is a string (rather than the expected tuple/list of date
      strings), the function shall NOT bypass type validation; it shall
      raise a BFSGComplianceError with diagnostic "period must be a tuple
      of ISO date strings, not str" rather than silently coercing the
      string into a 1-element tuple and continuing.
    test_oracle: >-
      output/repros/004_load_2026_profile_period_string_bypass.py::test_repro_004
    spec_phase: spec
    tdd_phase_origin: red
    locked_status: not_started
    notes: >-
      Verifies the iter-11 SHIPPED fix at
      repo/src/kurort_engine/predicate_filing/2026_validate.py:204-230
      (full type-check on period + reprdikatisierung_window).

  - id: AC-3
    bug: CF-PF-2026-1 (HIGH)
    ears: >-
      Where a 2026 attestation template references an adult rate (EUR
      amount) that is a Python float, the
      kurort_engine.predicate_filing.2026_attestation.apply_2026_attestation_template
      function shall format the rate as a 2-decimal-place string with
      TRAILING-ZERO preservation (e.g., 199.0 → "199.00"), preserving full
      Decimal precision rather than collapsing trailing zeros.
    test_oracle: >-
      output/repros/001_adult_rate_float_precision_loss.py::test_repro_001a
    spec_phase: spec
    tdd_phase_origin: red
    locked_status: not_started
    notes: >-
      Verifies the iter-11 SHIPPED fix at
      repo/src/kurort_engine/predicate_filing/2026_attestation.py:90
      (returns f"{Decimal(str(rate)):.2f}" rather than the prior
      f"{rate:.2f}" that collapsed trailing zeros).

  - id: AC-4
    bug: CF-PF-2026-3 (MEDIUM)
    ears: >-
      Where kurort_engine.predicate_filing.2026_attestation.compute_anti_drift_sha
      raises a BFSGComplianceError due to a chain-extension module SHA
      drift, the raised exception's diagnostic message shall be trimmed
      (≤200 chars) and shall NOT include the full chain-extension module
      names — only the short module identifier (the last path segment)
      and the SHA — so that the error message is BFSG-AA-compliant and
      not overwhelming for screen readers.
    test_oracle: >-
      output/repros/003_anti_drift_sha_misleading_diagnostic.py::test_repro_003
    spec_phase: spec
    tdd_phase_origin: red
    locked_status: not_started
    notes: >-
      Verifies the iter-11 SHIPPED fix at
      repo/src/kurort_engine/predicate_filing/2026_attestation.py:280-289
      (BFSGComplianceError message trims to iter-33 chain-extension
      modules last-segment only).

  - id: AC-5
    bug: "(structural — full-green-suite baseline)"
    ears: >-
      The full pytest suite
      `cd repo && PYTHONPATH=src .venv/bin/python -m pytest tests/ -q
      --override-ini="addopts=--tb=line"` shall exit 0 with all tests
      passing (163 expected / 0 failed / 0 skipped after AC-6 + AC-7 fixes
      ship), and the 6 SHA-preserved modules + 4 iter-33 SHIPPED
      predicate_filing modules + the predicate_filing __init__ re-export
      surface shall all remain byte-identical to their HEAD state.
    test_oracle: >-
      repo/tests/test_predicate_filing_2026.py::test_ac5_full_test_suite_green
    spec_phase: spec
    tdd_phase_origin: "(green — verification-only)"
    locked_status: not_started
    notes: >-
      Structural baseline preservation. The 6 SHA modules are
      kurort_engine.esg.__init__ (b00acc9e),
      kurort_engine.esg.report.__init__ (d29f01c6),
      kurort_engine.kurpaket_orchestrator (baa2e0ed),
      kurort_engine.kurkarte_wallet.__init__ (1b4c3f80),
      kurort_engine.spa_wellness.__init__ (28dc45e8),
      kurort_engine.ev_charging.__init__ (e6b33f86). The 4 iter-33 SHIPPED
      predicate_filing modules are predicate_packet_assembler,
      kurgaste_health_data_aggregator, heilbad_2036_narrative_generator,
      predicate_filing_export.

  - id: AC-6
    bug: "(regression — pre-existing on main HEAD 4b682ddb)"
    ears: >-
      Where the kurort_engine.audit.AuditLog class receives an
      AuditLogEntry whose source module is
      `kurort_engine.a11y.guest_pwa` emitting a self-attestation event
      with a dict-shaped payload (e.g.,
      {"attested": true, "schema": "BFSG-EAA-1.0"}), the AuditLog's
      __iter__ / entries snapshot iteration shall return each entry with
      its payload field preserved as the dict (not coerced to str), and
      the AuditLog's record_sgb_v_event path shall NOT pre-emptively
      filter dict-payload entries from prior tests, so that AC-7's
      payload-shape test passes without AttributeError on .replace().
    test_oracle: >-
      repo/tests/test_audit.py::test_ac7_audit_log_appends_entry_and_preserves_order
    spec_phase: spec
    tdd_phase_origin: "(red — new repro: output/repros/005_audit_shared_state_pollution.py::test_repro_005a)"
    locked_status: not_started
    notes: >-
      The AC-6 contract is: AuditLog accepts dict payloads from
      record_sgb_v_event without breaking iteration; AuditLog's entries
      snapshot returns dict-payload entries with the dict preserved.
      The corresponding src fix is in
      repo/src/kurort_engine/audit.py (≈5–10 LOC surgical).
      A new pytest repro is added at
      output/repros/005_audit_shared_state_pollution.py to verify the
      contract. The repo/tests/ test_audit.py file is NOT modified
      (per NI-8: tests are OBJECTIVE TRUTH).

  - id: AC-7
    bug: "(regression — pre-existing on main HEAD 4b682ddb)"
    ears: >-
      Where kurort_engine.kurpaket_compliance.code_path_AC9 iterates the
      shared AuditLog to verify that an SGB V §23 audit event was written,
      and encounters an entry whose payload is a dict (e.g., from
      kurort_engine.a11y.guest_pwa self-attestation), the code path
      shall coerce the dict payload to a JSON string (via json.dumps)
      BEFORE calling .replace(), so that the test
      test_ac9_sgb_v_23_audit_event_written_to_kurort_audit_log passes
      without AttributeError on the dict payload.
    test_oracle: >-
      repo/tests/test_kurpaket_compliance.py::test_ac9_sgb_v_23_audit_event_written_to_kurort_audit_log
    spec_phase: spec
    tdd_phase_origin: "(red — new repro: output/repros/006_kurpaket_compliance_dict_payload_replace.py::test_repro_006a)"
    locked_status: not_started
    notes: >-
      The AC-7 contract is: kurpaket_compliance code-path AC9 coerces
      dict payloads to str before .replace() calls. The corresponding
      src fix is in repo/src/kurort_engine/kurpaket_compliance.py
      (≈3–5 LOC surgical). A new pytest repro is added at
      output/repros/006_kurpaket_compliance_dict_payload_replace.py to
      verify the contract. The repo/tests/ test_kurpaket_compliance.py
      file is NOT modified (per NI-8: tests are OBJECTIVE TRUTH).
```

## Traceability Matrix (initialized)

| AC    | Bug / Origin                              | Status       | Test Oracle                                                                                                    | SHA-preserved note                                                            |
|-------|-------------------------------------------|--------------|----------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| AC-1  | CF-PF-2026-2 (HIGH) — iter-11 SHIPPED     | not_started  | `output/repros/002_beglaubigung_silent_drop_unescaped_clauses.py::test_repro_002a`                              | Verifies 2026_validate.py:102-108 (regex accepts both quoted + unquoted)       |
| AC-2  | CF-PF-2026-4 (HIGH) — iter-11 SHIPPED     | not_started  | `output/repros/004_load_2026_profile_period_string_bypass.py::test_repro_004`                                   | Verifies 2026_validate.py:204-230 (full type-check on period + window)         |
| AC-3  | CF-PF-2026-1 (HIGH) — iter-11 SHIPPED     | not_started  | `output/repros/001_adult_rate_float_precision_loss.py::test_repro_001a`                                         | Verifies 2026_attestation.py:90 (Decimal preservation, not float collapse)     |
| AC-4  | CF-PF-2026-3 (MEDIUM) — iter-11 SHIPPED   | not_started  | `output/repros/003_anti_drift_sha_misleading_diagnostic.py::test_repro_003`                                     | Verifies 2026_attestation.py:280-289 (BFSG-AA compliant trim)                 |
| AC-5  | Structural full-green-suite baseline      | not_started  | `repo/tests/test_predicate_filing_2026.py::test_ac5_full_test_suite_green`                                     | 6 SHA modules + 4 iter-33 modules + __init__ re-exports all 0-line diff        |
| AC-6  | Regression — audit shared-state pollution | red  | `repo/tests/test_audit.py::test_ac7_audit_log_appends_entry_and_preserves_order` (regression repro: `output/repros/005_audit_shared_state_pollution.py::test_repro_005a`) | src fix in audit.py ≈5–10 LOC; NI-8 forbids edits to test_audit.py            |
| AC-7  | Regression — kurpaket dict-payload .replace() | red | `repo/tests/test_kurpaket_compliance.py::test_ac9_sgb_v_23_audit_event_written_to_kurort_audit_log` (regression repro: `output/repros/006_kurpaket_compliance_dict_payload_replace.py::test_repro_006a`) | src fix in kurpaket_compliance.py ≈3–5 LOC; NI-8 forbids edits to test_kurpaket_compliance.py |

**Total: 7 ACs** (AC-1..AC-7). Status column will transition `not_started → red → green` as the cycle progresses through Phase 2 (RED) and Phase 3 (GREEN). Per pinned memory #1, the lock must NEVER be rewritten to match landed code — if an AC is wrong, surface it via BLOCKED and revise in a strategic phase.

## Lock SHA-256 Footer (canonical, MUST be re-verified after any plan.md edit)

| Item                                                  | SHA-256 (hex)                                                            | Byte count |
|-------------------------------------------------------|--------------------------------------------------------------------------|------------|
| Source `spec.yaml` (full file)                        | `7971b4d374b9413974d6e26ebde902857a5d0b7a3b2a0a0820c246f81f6f1c47`       | 15188      |
| AC block in `spec.yaml` (lines 53–220)                | `a7353a96e4a6b32ce41c9feef0041bc7c1f64612a836bc7b879d0d03716c6158`       | 7985       |
| PROTECTED AC block in THIS `spec_lock.md` (N=1 yaml)  | **MUST equal `a7353a96e4a6b32ce41c9feef0041bc7c1f64612a836bc7b879d0d03716c6158`** | **MUST equal 7985** |

**Re-verification command** (per pinned memory #2, `exit` BEFORE `print` discipline):

```bash
awk -v N=1 '/^```yaml$/{n++; if(n==N){capture=1; next}} /^```$/ && capture{exit} capture{print}' \
  repo/spec/p1_predicate_filing_2026_fix_axis/spec_lock.md | sha256sum
```

**Expected output:**
```
a7353a96e4a6b32ce41c9feef0041bc7c1f64612a836bc7b879d0d03716c6158  -
```

**Expected byte count:**
```bash
awk -v N=1 '/^```yaml$/{n++; if(n==N){capture=1; next}} /^```$/ && capture{exit} capture{print}' \
  repo/spec/p1_predicate_filing_2026_fix_axis/spec_lock.md | wc -c
```
Expected: `7985`.

## Phase 1 (Spec) sign-off

- [x] `spec.yaml` exists at `repo/spec/p1_predicate_filing_2026_fix_axis/spec.yaml` (312 lines, 15292 bytes, SHA `e8811c3f…`)
- [x] 7 ACs (AC-1..AC-7) are documented in EARS form (Ubiquitous + State-driven + Unwanted-behavior + Event-driven templates)
- [x] All 7 ACs have `test_oracle` paths matching this repo's layout (`output/repros/NNN_*.py::test_repro_*` + `repo/tests/test_*.py::test_ac*`)
- [x] `not_included` (NI-1..NI-8) and `done_when` (DW-1..DW-5) sections present in `spec.yaml`
- [x] This `spec_lock.md` written with verbatim AC block in fenced YAML
- [x] Traceability matrix table initialized with 7 rows at `status=not_started`
- [x] SHA-256 footer recorded; AWK re-verification protocol documented
- [ ] **PENDING todo_4**: AWK SHA re-verification PASS (must equal `a7353a96…`)
- [ ] **PENDING todo_5**: Phase 1 retrospective written

**End of Phase 1 (Spec) lock. Cycle pauses for todo_4 AWK verification before Phase 2 (RED) begins.**