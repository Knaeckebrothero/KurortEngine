# =============================================================================
# spec.lock.md — iter-12 P1 predicate_filing 2026 regression-lock cycle
# LOCK METADATA — frozen at Phase 1 close (2026-07-14)
# =============================================================================
# This file is the PROTECTED spec lock for iter-12 Phase 1 (spec).
# The fenced "## Acceptance Criteria" block below is byte-identical to
# the `acceptance_criteria:` block in `spec.yaml` (lines 51..221).
# Any drift between the two blocks is an AC integrity violation.
# =============================================================================

job: f0a2964a-a1fe-4fbb-acf5-5754a562a7b4
iteration: 12
branch: job/f0a2964a
head_entry: 7a5da641
feature: p1-predicate-filing-2026-regression-lock
phase_locked: 1 (spec)
locked_at: 2026-07-14
locked_by: Developer
# Frozen hash echo marker — preserved from iter-11 frozen spec.yaml
frozen_hash_echo: __DONE_a634cebc1bf7__
# SHA-256 of the FULL spec.yaml file (sha256sum spec.yaml)
spec_yaml_sha256: a6bd732c7be717e553532e35bf53cb71453626a7fccea29aa3a9b1deb918b166
# SHA-256 of the AC block content (lines 51..221 of spec.yaml, byte-identical to fenced block below)
spec_yaml_ac_block_sha256: ca797ada3ba35922257c540ff86214bc83a516f370caf809d0a91f7dc2e0032d
# AC block byte length + line count (must reconcile with sha256 re-verify)
spec_yaml_ac_block_bytes: 7852
spec_yaml_ac_block_lines: 171
spec_yaml_ac_block_line_range: "51..221"
# AC count
acceptance_criteria_count: 7

# =============================================================================
# PROTECTED -- Acceptance Criteria
# =============================================================================
# Below is the canonical 7-AC block, copied byte-identical from
# `spec.yaml` lines 51..221 (acceptance_criteria section).
# SHA-256 = ca797ada3ba35922257c540ff86214bc83a516f370caf809d0a91f7dc2e0032d
# Bytes = 7852
# Lines = 171
# DO NOT EDIT this block in this file; if the ACs need to change, edit
# spec.yaml and re-verify the SHA matches.
# =============================================================================

```yaml
acceptance_criteria:

  - id: AC-1
    bug: CF-PF-2026-2 (HIGH)
    ears: >-
      Where a Beglaubigung attestation clause contains unescaped
      embedded quotes ("Kurarzt" attest with embedded "Beihilfe"
      quote), the
      kurort_engine.predicate_filing.2026_validate.extract_2026_satzung_schema
      function shall extract the clause without silent drop, returning
      the unquoted clause text in the resulting schema dict's
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
      When
      kurort_engine.predicate_filing.2026_validate.load_2026_profile
      is called with a profile whose period or
      reprdikatisierung_window attribute is a string (rather than the
      expected tuple/list of date strings), the function shall NOT
      bypass type validation; it shall raise a BFSGComplianceError
      with diagnostic "period must be a tuple of ISO date strings,
      not str" rather than silently coercing the string into a
      1-element tuple and continuing.
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
      TRAILING-ZERO preservation (e.g., 199.0 -> "199.00"), preserving
      full Decimal precision rather than collapsing trailing zeros.
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
      Where
      kurort_engine.predicate_filing.2026_attestation.compute_anti_drift_sha
      raises a BFSGComplianceError due to a chain-extension module SHA
      drift, the raised exception's diagnostic message shall be
      trimmed (<=200 chars) and shall NOT include the full
      chain-extension module names — only the short module identifier
      (the last path segment) and the SHA — so that the error message
      is BFSG-AA-compliant and not overwhelming for screen readers.
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
    bug: structural-full-green-suite-baseline
    ears: >-
      The full pytest suite `cd repo && PYTHONPATH=src .venv/bin/python
      -m pytest tests/ -q --override-ini="addopts=--tb=line"` shall
      exit 0 with all tests passing (163 expected / 0 failed / 0
      skipped after AC-6 + AC-7 fixes ship), and the 6 SHA-preserved
      modules + 4 iter-33 SHIPPED predicate_filing modules + the
      predicate_filing __init__ re-export surface shall all remain
      byte-identical to their HEAD state.
    test_oracle: >-
      repo/tests/test_predicate_filing_2026.py::test_ac5_full_test_suite_green
    spec_phase: spec
    tdd_phase_origin: green-verification-only
    locked_status: not_started
    notes: >-
      Structural baseline preservation. The 6 SHA modules are
      kurort_engine.esg.__init__ (b00acc9e),
      kurort_engine.esg.report.__init__ (d29f01c6),
      kurort_engine.kurpaket_orchestrator (baa2e0ed),
      kurort_engine.kurkarte_wallet.__init__ (1b4c3f80),
      kurort_engine.spa_wellness.__init__ (28dc45e8),
      kurort_engine.ev_charging.__init__ (e6b33f86). The 4 iter-33
      SHIPPED predicate_filing modules are
      predicate_packet_assembler, kurgaste_health_data_aggregator,
      heilbad_2036_narrative_generator, predicate_filing_export.

  - id: AC-6
    bug: regression-pre-existing-on-main-4b682ddb
    ears: >-
      Where the kurort_engine.audit.AuditLog class receives an
      AuditLogEntry whose source module is
      `kurort_engine.a11y.guest_pwa` emitting a self-attestation event
      with a dict-shaped payload (e.g.,
      {"attested": true, "schema": "BFSG-EAA-1.0"}), the AuditLog's
      __iter__ / entries snapshot iteration shall return each entry
      with its payload field preserved as the dict (not coerced to
      str), and the AuditLog's record_sgb_v_event path shall NOT
      pre-emptively filter dict-payload entries from prior tests, so
      that AC-7's payload-shape test passes without AttributeError on
      .replace().
    test_oracle: >-
      repo/tests/test_audit.py::test_ac7_audit_log_appends_entry_and_preserves_order
    spec_phase: spec
    tdd_phase_origin: red-new-repro-output-repros-005
    locked_status: not_started
    notes: >-
      The AC-6 contract is: AuditLog accepts dict payloads from
      record_sgb_v_event without breaking iteration; AuditLog's
      entries snapshot returns dict-payload entries with the dict
      preserved. The corresponding src fix is in
      repo/src/kurort_engine/audit.py (~5-10 LOC surgical). A new
      pytest repro is added at
      output/repros/005_audit_shared_state_pollution.py to verify
      the contract. The repo/tests/test_audit.py file is NOT
      modified (per NI-8: tests are OBJECTIVE TRUTH).

  - id: AC-7
    bug: regression-pre-existing-on-main-4b682ddb
    ears: >-
      Where kurort_engine.kurpaket_compliance.code_path_AC9 iterates
      the shared AuditLog to verify that an SGB V paragraph 23 audit
      event was written, and encounters an entry whose payload is a
      dict (e.g., from kurort_engine.a11y.guest_pwa
      self-attestation), the code path shall coerce the dict payload
      to a JSON string (via json.dumps) BEFORE calling .replace(),
      so that the test
      test_ac9_sgb_v_23_audit_event_written_to_kurort_audit_log
      passes without AttributeError on the dict payload.
    test_oracle: >-
      repo/tests/test_kurpaket_compliance.py::test_ac9_sgb_v_23_audit_event_written_to_kurort_audit_log
    spec_phase: spec
    tdd_phase_origin: red-new-repro-output-repros-006
    locked_status: not_started
    notes: >-
      The AC-7 contract is: kurpaket_compliance code-path AC9
      coerces dict payloads to str before .replace() calls. The
      corresponding src fix is in
      repo/src/kurort_engine/kurpaket_compliance.py (~3-5 LOC
      surgical). A new pytest repro is added at
      output/repros/006_kurpaket_compliance_dict_payload_replace.py
      to verify the contract. The repo/tests/test_kurpaket_compliance.py
      file is NOT modified (per NI-8: tests are OBJECTIVE TRUTH).
```

# =============================================================================
# Traceability Matrix
# =============================================================================
# 7 rows, one per AC. Status is `not_started` at Phase 1 close; will be
# updated to `red` / `green` / `verified` as Phase 2 (red) and Phase 3
# (green) proceed.
# =============================================================================

| AC ID | Bug | Test Oracle | Status |
|-------|-----|-------------|--------|
| AC-1 | CF-PF-2026-2 (HIGH) | `output/repros/002_beglaubigung_silent_drop_unescaped_clauses.py::test_repro_002a` | `not_started` |
| AC-2 | CF-PF-2026-4 (HIGH) | `output/repros/004_load_2026_profile_period_string_bypass.py::test_repro_004` | `not_started` |
| AC-3 | CF-PF-2026-1 (HIGH) | `output/repros/001_adult_rate_float_precision_loss.py::test_repro_001a` | `not_started` |
| AC-4 | CF-PF-2026-3 (MEDIUM) | `output/repros/003_anti_drift_sha_misleading_diagnostic.py::test_repro_003` | `not_started` |
| AC-5 | structural-full-green-suite-baseline | `repo/tests/test_predicate_filing_2026.py::test_ac5_full_test_suite_green` | `not_started` |
| AC-6 | regression-pre-existing-on-main-4b682ddb | `repo/tests/test_audit.py::test_ac7_audit_log_appends_entry_and_preserves_order` | `not_started` |
| AC-7 | regression-pre-existing-on-main-4b682ddb | `repo/tests/test_kurpaket_compliance.py::test_ac9_sgb_v_23_audit_event_written_to_kurort_audit_log` | `not_started` |
# =============================================================================
# Phase 1 close checklist
# =============================================================================
# [x] AC block extracted from spec.yaml (lines 51..221, 171 lines)
# [x] AC block SHA-256 computed: ca797ada3ba35922257c540ff86214bc83a516f370caf809d0a91f7dc2e0032d
# [x] spec.yaml SHA-256 computed: a6bd732c7be717e553532e35bf53cb71453626a7fccea29aa3a9b1deb918b166
# [x] PROTECTED block written byte-identical to spec.yaml AC block
# [x] Traceability matrix initialized with 7 rows, all not_started
# [x] Frozen hash echo marker preserved: __DONE_a634cebc1bf7__
# [x] Lock metadata header recorded (job, branch, head, feature, phase)
# [ ] TODO: Phase 2 (red) — flip AC-6 / AC-7 to `red` after repros 005/006 FAIL
# [ ] TODO: Phase 3 (green) — flip AC-1..AC-7 to `green` after src fixes land
# [ ] TODO: Phase 4 (integration) — flip AC-5 (full-green-suite) to `verified`
