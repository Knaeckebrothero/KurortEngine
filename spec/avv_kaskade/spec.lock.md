# iter-28 spec_lock.md — avv_kaskade (Art. 28 DSGVO cascade-audit module) — Phase 1 spec SHIPPED

**Iteration:** 28 of 39+ · **Role:** Developer · **Cycle:** iter-28 Phase 1 (spec)
**Captured:** 2026-07-09 · **Status:** spec SHIPPED · **Confidence:** high
**Anchored by:** iter-27-critic-handoff-to-iter-28-developer-p1-avvkaskade-7-phase-tdd-cycle-cont

## PROTECTED — Acceptance Criteria (BYTE-IDENTICAL to spec.yaml AC block)

```yaml
acceptance_criteria:
  - id: AC-1
    ears: "When register_processor(processor) is called with a Processor dataclass whose avv_signed_date < avv_expiry_date, the system shall compute avv_hash = sha256(avv_pdf_bytes).hexdigest() and append the processor to an append-only registry; and the system shall reject processors whose avv_signed_date >= avv_expiry_date with a ValueError."
    test_oracle: tests/test_avv_kaskade.py::test_ac1_register_processor_happy_path
  - id: AC-1.1
    ears: "If register_processor(processor) is called with a Processor whose avv_signed_date >= avv_expiry_date, then the system shall raise ValueError citing the date constraint and shall NOT append the processor to the registry."
    test_oracle: tests/test_avv_kaskade.py::test_ac11_register_processor_expired_avv_rejected
  - id: AC-2
    ears: "While a processor is registered in the avv_kaskade registry, the system shall expose run_geeignetheitspruefung(processor_id) which returns a GeeignetheitspruefungReport containing (a) ISO 27001 control coverage >= 0.80 of the mandatory control set, (b) sub_processor_disclosure_completeness == 1.0, (c) avv_signature_verified == True, and (d) a tom_evidence_index for each data_category of every sub_processor."
    test_oracle: tests/test_avv_kaskade.py::test_ac2_geeignetheitspruefung_report_complete
  - id: AC-2.1
    ears: "If a registered processor has a sub_processor with vendor_non_cooperation == True, then the system shall produce a GeeignetheitspruefungReport with vendor_non_coop_complete < 1.0 and flag the sub_processor in the report's gaps list."
    test_oracle: tests/test_avv_kaskade.py::test_ac21_vendor_non_coop_flagged_in_report
  - id: AC-3
    ears: "When attest_chain(format=\"dsk-kp13\") is called, the system shall emit a JSON packet whose top-level keys are verantwortlicher, auftragsverarbeiter, toms, sub_processors, and avv_hash_chain, and whose verantwortlicher block contains controller_name + controller_address + attestation_date; and the avv_hash_chain shall be a list of SHA-256 hex strings matching the avv_hash of each registered processor in registration order."
    test_oracle: tests/test_avv_kaskade.py::test_ac3_attestor_dsk_kp13_packet_shape
  - id: AC-4
    ears: "When export_audit_packet(processor_id, format) is called with format in {\"lfa-baylda\", \"lfdi-bw\", \"hbdi-he\"}, the system shall return a packet object whose payload bytes start with b\"%PDF-\" and whose metadata[\"state_format\"] equals the requested format; and the system shall raise ValueError for any format not in the three supported state formats. NOTE (manual-review deferral, per binding contract mitigation 1): if no internal privacy-experienced reviewer is available to verify the 3 state-format PDF byte-shapes against the DSK-aligned reference templates (BayLDA, LfDI BW, HBDI Hessen), then AC-4 acceptance MAY be deferred to the BFSG-AA reviewer pool. In that case the spec_lock.md STALE_PENDING_FLAG shall be flipped to SET, and the deferred-AC-4 marker shall be recorded in the retrospective."
    test_oracle: tests/test_avv_kaskade.py::test_ac4_export_audit_packet_3state
  - id: AC-5
    ears: "When build_tom_evidence_index(processor_id, control_set=\"bsi-grundschutz-2026\") is called, the system shall return a TomEvidenceIndex whose control_set == \"bsi-grundschutz-2026\", whose entries list one TOM-evidence record per ISO 27001 Annex A control mapped to the BSI Grundschutz 2026 Bausteine, and whose evidence_chain_hash is a SHA-256 hex of the canonical-JSON serialization of the entries in registry-registration order."
    test_oracle: tests/test_avv_kaskade.py::test_ac5_nis2_bsig_evidence_locker
```

## spec.yaml SHA-256 (locked at Phase 1 spec SHIPPED)

```
d9e6c5520ca8bec03a179a232bf20333653be976aaf403ce8d776dbc03f28666  spec/avv_kaskade/spec.yaml
```

**Verification command:** `shasum -a 256 repo/spec/avv_kaskade/spec.yaml`
must return `d9e6c5520ca8bec03a179a232bf20333653be976aaf403ce8d776dbc03f28666`.
Any drift → re-stamp the SHA and document the revision in the retrospective.

## STALE_PENDING_FLAG

`<!-- STALE_PENDING_FLAG: AC-4 manual review availability (per iter-27-critic-handoff binding contract mitigation 2) -->`

**Current value:** SET (no internal privacy-experienced reviewer confirmed as of 2026-07-09).
**Flipped by:** the strategic-review phase (Phase 6) when (a) a privacy-experienced reviewer
is confirmed available, OR (b) the deferred-AC-4 acceptance path to BFSG-AA reviewer pool
is ratified. Flipping this flag requires a `kb_update` on the
`iter-28-spec-input-avv-kaskade-dsgvo-art-28-cascade-audit-spec-contract-5-ears-a` note
and an entry in the Phase 6 retrospective.

## IMPORT_DISCIPLINE

`<!-- IMPORT_DISCIPLINE: iter-38 kurgaste_retention/auto_cascade.py line 73-118 is the audit_trail.py dependency; avv_kaskade IMPORTS append-only audit log pattern from iter-38, does NOT MODIFY any of the 6 SHAs (per iter-27-critic-handoff binding contract mitigation 4) -->`

## 6 SHAs to preserve verbatim (Pattern C chain-extension anti-drift)

iter-28+ Developer MUST NOT modify any of these. Phase 5 integration verification:
`git diff HEAD~1 --stat` MUST show 0 lines changed in any of the 6 SHAs.

| # | SHA-source                                                                  | SHIPPED iteration | Why preserved |
|---|-----------------------------------------------------------------------------|-------------------|---------------|
| 1 | `src/kurort_engine/predicate_filing/__init__.py`                              | iter-33 SHIPPED   | Read-only consumer for AC-5 Bad Orb Kurort-vertical integration |
| 2 | `src/kurort_engine/predicate_filing/predicate_packet_assembler.py`            | iter-33 SHIPPED   | Read-only consumer |
| 3 | `src/kurort_engine/predicate_filing/heilbad_2036_narrative_generator.py`     | iter-33 SHIPPED   | Read-only consumer |
| 4 | `src/kurort_engine/kurgaste_retention/__init__.py`                            | iter-38 SHIPPED   | Pattern C chain-extension dependency |
| 5 | `src/kurort_engine/kurgaste_retention/auto_cascade.py`                        | iter-38 SHIPPED   | Pattern C chain-extension + audit_trail.py mirror reference (lines 73-118) |
| 6 | `src/kurort_engine/kurkarte_wallet/__init__.py`                               | iter-21 SHIPPED   | AC-4 BFSG-AA accessibility compliance + import-discipline (BFSGComplianceError) |

## Traceability matrix (initialized at Phase 1 spec SHIPPED)

| AC ID | Test oracle path                                          | Status      | Phase           |
|-------|-----------------------------------------------------------|-------------|-----------------|
| AC-1  | tests/test_avv_kaskade.py::test_ac1_register_processor_happy_path | not_started | Phase 2 (red)   |
| AC-1.1| tests/test_avv_kaskade.py::test_ac11_register_processor_expired_avv_rejected | not_started | Phase 2 (red)   |
| AC-2  | tests/test_avv_kaskade.py::test_ac2_geeignetheitspruefung_report_complete | not_started | Phase 2 (red)   |
| AC-2.1| tests/test_avv_kaskade.py::test_ac21_vendor_non_coop_flagged_in_report | not_started | Phase 2 (red)   |
| AC-3  | tests/test_avv_kaskade.py::test_ac3_attestor_dsk_kp13_packet_shape | not_started | Phase 2 (red)   |
| AC-4  | tests/test_avv_kaskade.py::test_ac4_export_audit_packet_3state | not_started | Phase 2 (red) → Phase 3 (green) — **deferred to BFSG-AA reviewer pool** per STALE_PENDING_FLAG |
| AC-5  | tests/test_avv_kaskade.py::test_ac5_nis2_bsig_evidence_locker | not_started | Phase 2 (red)   |

**Lifecycle:** `not_started` → `red` (Phase 2) → `green` (Phase 3) → `verified` (Phase 5 integration).
**Update mechanism:** Python in-place replacement via `run_command` (NOT `write_file`,
`edit_file`, or `sed`) per pinned memory [2]. The PROTECTED AC block above is byte-identical
to `spec.yaml` acceptance_criteria block; SHA-256 of the block is preserved across matrix updates.

## Verification commands (mirrored from spec.yaml done_when)

```bash
# 1. spec SHA-256 lock verification
shasum -a 256 repo/spec/avv_kaskade/spec.yaml
# Expected: d9e6c5520ca8bec03a179a232bf20333653be976aaf403ce8d776dbc03f28666

# 2. 5+ ACs GREEN at Phase 3
cd repo && PYTHONPATH=src .venv/bin/python -m pytest tests/test_avv_kaskade.py -v --override-ini="addopts=--tb=short"
# Expected: 7 passed, 0 failed (7 tests covering AC-1, AC-1.1, AC-2, AC-2.1, AC-3, AC-4, AC-5)

# 3. 6 SHAs anti-drift
cd repo && git diff HEAD~1 --stat
# Expected: 0 lines changed in any of predicate_filing/, kurgaste_retention/, kurkarte_wallet/

# 4. Mix-B lawyer-budget gate re-verification
cat knowledge/lawyer-budget-gate-state-of-project-crossed-5-iteration-threshold-at-iter-26-was.md | head -50
# Expected: STATE-OF-PROJECT = NO Lawyer

# 5. Bad Orb Kurverwaltung processor chain integration
cd repo && PYTHONPATH=src python -c "
from kurort_engine.avv_kaskade import (
    register_processor, run_geeignetheitspruefung, attest_chain, export_audit_packet, build_tom_evidence_index,
)
chain = ['cm-booking-com', 'pms-kurortengine', 'kb-datev', 'kv-bad-orb-kurverwaltung', 'ms-kurverwaltung', 'hkka-rp-kassel']
for pid in chain:
    report = run_geeignetheitspruefung(pid)
    assert report.sub_processor_disclosure_completeness >= 0.95, f'{pid}: AC-2 fails'
print('BAD ORB KURVERWALTUNG PROCESSOR CHAIN INTEGRATION: 6/6 sub-processors PASS')
"
# Expected: exits 0 with the print line

# 6. ruff lint
cd repo && ruff check src/kurort_engine/avv_kaskade/
# Expected: All checks passed!

# 7. PROTECTED block byte-identity verification (after any matrix update)
python3 -c "
import hashlib
with open('repo/spec/avv_kaskade/spec.yaml','rb') as f:
    spec_yaml_bytes = f.read()
import re
m = re.search(rb'acceptance_criteria:.*?(?=\nnot_included:|\ndone_when:|\nassumptions:)', spec_yaml_bytes, re.DOTALL)
assert m, 'AC block not found in spec.yaml'
spec_ac_block = m.group(0) + b'\n'
with open('repo/spec/avv_kaskade/spec.lock.md','rb') as f:
    lock_md_bytes = f.read()
lock_ac_marker = b'acceptance_criteria:\n'
lock_idx = lock_md_bytes.find(lock_ac_marker)
assert lock_idx != -1, 'AC block not found in spec.lock.md'
end_marker = b'\n```\n'
lock_end = lock_md_bytes.find(end_marker, lock_idx)
lock_ac_block = lock_md_bytes[lock_idx:lock_end]
assert spec_ac_block == lock_ac_block, f'PROTECTED block drift: spec.yaml != spec.lock.md'
print('PROTECTED block byte-identity: VERIFIED')
"
# Expected: PROTECTED block byte-identity: VERIFIED
```

## Cross-references

- `repo/spec/avv_kaskade/spec.yaml` — the spec source (SHA-256 d9e6c5520...)
- `iter-27-critic-handoff-to-iter-28-developer-p1-avvkaskade-7-phase-tdd-cycle-cont` — binding contract
- `iter-27-critic-verdict-choose-proposal-p1-avvkaskade-art-28-dsgvo-cascade-audit-` — D5 verdict
- `iter-39-proposal-001-avvkaskade-art-28-dsgvo-cascade-audit-module-tier-1-primary` — Scholar pick-first #1
- `iter-28-spec-input-avv-kaskade-dsgvo-art-28-cascade-audit-spec-contract-5-ears-a` — spec-input synthesis
- `iter-28-kurortengine-repository-map-test-framework-sourcetest-layout-lint-baseli` — repo map
- `iter-28-developer-pinned-rules-tdd-discipline-forbidden-test-patterns-spec-first` — TDD discipline
- `iter-28-developer-delivery-expectations-prs-branches-commits-kb-handoff` — delivery expectations
- `iter-28-developer-required-deliverables-exact-paths-and-formats` — required deliverables
- `iter-28-developer-initial-state-current-job-objective-ac-progress-tracker` — initial state
- `lawyer-budget-gate-state-of-project-crossed-5-iteration-threshold-at-iter-26-was` — Mix-B gate
- `iter-15-red-phase-fresh-package-importlibfindspec-guard-pattern-iter-15-l13-004-contribu` — red-phase guard pattern
- `dsgvo-art-17-5-step-atomic-cascade-pattern-kurgasteretentionautocascade` — Pattern C reference

## Phase boundary tag (convention per pinned memory [8])

- Phase 1 spec SHIPPED tag: `iter28-phase-1-spec-complete`
- Apply at Phase 1 spec SHIPPED (i.e., after this file is written + matrix initialized).
- Authoritative merge status: per `retros/` (this is the first iter-28 retro; will be created at Phase 5).
