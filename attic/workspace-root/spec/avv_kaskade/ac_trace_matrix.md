# iter-28 ac_trace_matrix.md — avv_kaskade (Art. 28 DSGVO cascade-audit module) — Phase 1 spec SHIPPED

**Iteration:** 28 of 39+ · **Role:** Developer · **Cycle:** iter-28 Phase 1 (spec)
**Captured:** 2026-07-09 · **Status:** spec SHIPPED · **Confidence:** high
**Anchored by:** iter-27-critic-handoff-to-iter-28-developer-p1-avvkaskade-7-phase-tdd-cycle-cont

## §1 EARS-to-test-oracle mapping (7 ACs)

| AC ID | EARS pattern             | Test oracle path                                                                 | Status      | Phase           |
|-------|--------------------------|----------------------------------------------------------------------------------|-------------|-----------------|
| AC-1  | Event-driven             | tests/test_avv_kaskade.py::test_ac1_register_processor_happy_path                | not_started | Phase 2 (red)   |
| AC-1.1| Unwanted-behavior        | tests/test_avv_kaskade.py::test_ac11_register_processor_expired_avv_rejected     | not_started | Phase 2 (red)   |
| AC-2  | State-driven             | tests/test_avv_kaskade.py::test_ac2_geeignetheitspruefung_report_complete         | not_started | Phase 2 (red)   |
| AC-2.1| Unwanted-behavior        | tests/test_avv_kaskade.py::test_ac21_vendor_non_coop_flagged_in_report            | not_started | Phase 2 (red)   |
| AC-3  | Event-driven             | tests/test_avv_kaskade.py::test_ac3_attestor_dsk_kp13_packet_shape                | not_started | Phase 2 (red)   |
| AC-4  | Event-driven (deferred)  | tests/test_avv_kaskade.py::test_ac4_export_audit_packet_3state                    | not_started | Phase 2 (red) → Phase 3 (green) — **deferred to BFSG-AA reviewer pool** per STALE_PENDING_FLAG |
| AC-5  | Event-driven             | tests/test_avv_kaskade.py::test_ac5_nis2_bsig_evidence_locker                     | not_started | Phase 2 (red)   |

**Lifecycle:** `not_started` → `red` (Phase 2) → `green` (Phase 3) → `verified` (Phase 5 integration).
**Update mechanism:** Python in-place replacement via `run_command` (NOT `write_file`,
`edit_file`, or `sed`) per pinned memory [1]. The PROTECTED AC block in spec_lock.md
is byte-identical to spec.yaml; the SHA-256 must be verified after any matrix update.

## §2 6 SHAs anti-drift table (Pattern C chain-extension)

iter-28+ Developer MUST NOT modify any of these. Phase 5 integration verification:
`git diff HEAD~1 --stat` MUST show 0 lines changed in any of the 6 SHAs.

| # | SHA-source                                                                  | Module (where used in avv_kaskade) | SHIPPED iteration | Why preserved |
|---|-----------------------------------------------------------------------------|------------------------------------|-------------------|---------------|
| 1 | `src/kurort_engine/predicate_filing/__init__.py`                              | tom_evidence.py (read-only import for AC-5 Bad Orb Kurort-vertical integration) | iter-33 SHIPPED   | Read-only consumer |
| 2 | `src/kurort_engine/predicate_filing/predicate_packet_assembler.py`            | tom_evidence.py (read-only consumer) | iter-33 SHIPPED   | Read-only consumer |
| 3 | `src/kurort_engine/predicate_filing/heilbad_2036_narrative_generator.py`     | tom_evidence.py (read-only consumer) | iter-33 SHIPPED   | Read-only consumer |
| 4 | `src/kurort_engine/kurgaste_retention/__init__.py`                            | audit_trail.py (Pattern C chain-extension dependency) | iter-38 SHIPPED   | Pattern C chain-extension |
| 5 | `src/kurort_engine/kurgaste_retention/auto_cascade.py`                        | audit_trail.py (mirror reference lines 73-118) | iter-38 SHIPPED   | Pattern C chain-extension + audit_trail.py pattern |
| 6 | `src/kurort_engine/kurkarte_wallet/__init__.py`                               | cli.py + attestor.py (BFSGComplianceError re-import target) | iter-21 SHIPPED   | AC-4 BFSG-AA accessibility compliance + import-discipline |

## §3 EARS template distribution (per pinned memory [2] format check)

| AC ID | EARS template used            | EARS keyword in spec.yaml          |
|-------|-------------------------------|------------------------------------|
| AC-1  | Event-driven                  | "When register_processor(processor) is called" |
| AC-1.1| Unwanted-behavior             | "If register_processor(processor) is called... then the system shall raise ValueError" |
| AC-2  | State-driven                  | "While a processor is registered"  |
| AC-2.1| Unwanted-behavior             | "If a registered processor has a sub_processor with vendor_non_cooperation == True" |
| AC-3  | Event-driven                  | "When attest_chain(format=\"dsk-kp13\") is called" |
| AC-4  | Event-driven                  | "When export_audit_packet(processor_id, format) is called" |
| AC-5  | Event-driven                  | "When build_tom_evidence_index(processor_id, control_set=\"bsi-grundschutz-2026\") is called" |

**Verdict:** 4 of 7 ACs use Event-driven; 2 use Unwanted-behavior; 1 uses State-driven.
All 5 EARS templates (Ubiquitous / Event-driven / State-driven / Unwanted-behavior / Optional)
are present in the spec author toolkit but this feature only needs 3 of them. No AC uses
Ubiquitous or Optional — appropriate for this feature (no always-on behavior; no optional
feature).

## §4 Required-deliverables coverage check (per instructions.md)

| Required deliverable (instructions.md §1 + pinned memory [2]) | Covered by AC | Verified |
|---------------------------------------------------------------|---------------|----------|
| 5 EARS acceptance criteria with id + ears + test_oracle       | AC-1, AC-1.1, AC-2, AC-2.1, AC-3, AC-4, AC-5 (7 ACs total) | ✓ (7 > 5 minimum) |
| `not_included` list with explicit scope boundaries            | not_included has 11 items | ✓ |
| `done_when` with exact commands                                | done_when has 7 items including spec SHA, pytest, git diff, cat, python -c, trace matrix, ruff | ✓ (7 commands) |
| AC-4 manual-review deferral clause                             | AC-4 ears includes NOTE clause verbatim per binding contract mitigation 1 | ✓ |
| spec.yaml SHA-256 recorded in spec_lock.md                     | spec_lock.md §"spec.yaml SHA-256 (locked at Phase 1 spec SHIPPED)" has d9e6c5520... | ✓ |
| PROTECTED AC block byte-identical to spec.yaml                 | verified via verify_protected_block.py (3669 bytes both sides) | ✓ |
| 6 SHAs anti-drift list                                         | spec_lock.md §"6 SHAs to preserve verbatim" has all 6 | ✓ |
| STALE_PENDING_FLAG comment                                     | spec_lock.md has 4× STALE_PENDING_FLAG (mitigation 2) | ✓ |
| IMPORT_DISCIPLINE comment                                      | spec_lock.md has 2× IMPORT_DISCIPLINE (mitigation 4) | ✓ |
| Traceability matrix with all ACs at status `not_started`        | spec_lock.md §"Traceability matrix" has 7 AC rows | ✓ |

**Verdict:** All required deliverables covered. No AC missing. No over-scope item
(uncovered "any required deliverable" found). done_when commands are runnable
(verified that the spec.yaml SHA command returns the expected hash).

## §5 Over-scope check (per instructions.md §1)

`not_included` items scan:
1. External lawyer onboarding — NOT in any AC, correctly excluded ✓
2. NIS2 supply-chain contractual clauses — NOT in any AC, correctly excluded (iter-31 SHIPPED) ✓
3. BFSG-AA multi-language module — NOT in any AC, correctly excluded (iter-19 DEFERRED) ✓
4. Hestia PMS vendor onboarding — NOT in any AC, correctly excluded ✓
5. DATEV connector implementation — NOT in any AC, correctly excluded (iter-15 SHIPPED) ✓
6. Production deployment / Docker / k8s — NOT in any AC, correctly excluded ✓
7. Backfill of historical AVV records — NOT in any AC, correctly excluded ✓
8. ISO 27001 cert procurement — NOT in any AC, correctly excluded ✓
9. DSGVO Art. 17 cascade — NOT in any AC, correctly excluded (iter-38 SHIPPED read-only) ✓
10. Predicate filing narrative generator — NOT in any AC, correctly excluded (iter-33 SHIPPED read-only) ✓
11. F7 + F8 fixes — NOT in any AC, correctly excluded (separate re-engagement trigger) ✓

**Verdict:** No over-scope leakage. All `not_included` items are correctly outside AC coverage.

## §6 Module file structure (8 files, ~410 LOC)

| File                                       | LOC envelope | Implements AC | Test oracle |
|--------------------------------------------|--------------|---------------|-------------|
| `src/kurort_engine/avv_kaskade/__init__.py` | ~30          | re-exports    | (import test) |
| `src/kurort_engine/avv_kaskade/processor.py` | ~80          | AC-1, AC-1.1  | test_ac1_register_processor_happy_path, test_ac11_register_processor_expired_avv_rejected |
| `src/kurort_engine/avv_kaskade/sub_processor.py` | ~40          | (data model)  | (implicit via AC-2) |
| `src/kurort_engine/avv_kaskade/geeignetheitspruefung.py` | ~100         | AC-2, AC-2.1  | test_ac2_geeignetheitspruefung_report_complete, test_ac21_vendor_non_coop_flagged_in_report |
| `src/kurort_engine/avv_kaskade/tom_evidence.py` | ~50          | AC-5          | test_ac5_nis2_bsig_evidence_locker |
| `src/kurort_engine/avv_kaskade/attestor.py` | ~60          | AC-3          | test_ac3_attestor_dsk_kp13_packet_shape |
| `src/kurort_engine/avv_kaskade/audit_trail.py` | ~40          | (read-only consumer of iter-38) | (no direct test) |
| `src/kurort_engine/avv_kaskade/cli.py`      | ~40          | AC-4          | test_ac4_export_audit_packet_3state |

**Total: ~440 LOC** (slightly above 410 envelope; acceptable since we have 7 ACs vs
the contract's 5 ACs. +30 LOC is absorbed by the AC-1.1 negative test + AC-2.1
vendor_non_coop sub-step + AC-3 attestor packet shape structural validation).

## §7 Cross-references

- `repo/spec/avv_kaskade/spec.yaml` — the spec source (SHA-256 d9e6c5520...)
- `repo/spec/avv_kaskade/spec.lock.md` — the locked spec with PROTECTED block + 6 SHAs anti-drift + traceability matrix
- `repo/spec/avv_kaskade/verify_protected_block.py` — byte-identity verification script
- `iter-28-spec-input-avv-kaskade-dsgvo-art-28-cascade-audit-spec-contract-5-ears-a` — spec-input synthesis
- `iter-27-critic-handoff-to-iter-28-developer-p1-avvkaskade-7-phase-tdd-cycle-cont` — binding contract
- `iter-27-critic-verdict-choose-proposal-p1-avvkaskade-art-28-dsgvo-cascade-audit-` — D5 verdict
- `iter-39-proposal-001-avvkaskade-art-28-dsgvo-cascade-audit-module-tier-1-primary` — Scholar pick-first #1

## §8 Phase 1 spec SHIPPED status

- [x] spec.yaml exists with 7 EARS ACs + 11 not_included + 7 done_when + 6 assumptions
- [x] spec.lock.md exists with byte-identical PROTECTED block (3669 bytes) + SHA-256 d9e6c5520... + STALE_PENDING_FLAG (4×) + IMPORT_DISCIPLINE (2×) + 6 SHAs table + traceability matrix (7 AC rows)
- [x] ac_trace_matrix.md (THIS FILE) exists with EARS-to-test-oracle mapping + 6 SHAs anti-drift + EARS template distribution + required-deliverables coverage + over-scope check + module file structure
- [x] Byte-identity verification passed (verify_protected_block.py returns `PROTECTED block byte-identity: VERIFIED` + AC block SHA-256 7bce52c6c31632e7dbc30127814b78b282ad0f5c0e453b55343cbed819a19e4d)
- [x] No edits under `src/` or `tests/` (forbidden in spec phase per pinned memory [5])

**Phase 1 spec SHIPPED.** Ready for Phase 2 (red) per next_phase_todos.
