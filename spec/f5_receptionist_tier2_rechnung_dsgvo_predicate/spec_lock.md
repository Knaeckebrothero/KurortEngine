# iter-24 spec_lock.md — F5 receptionist-subcommands Tier-2 (rechnung / dsgvo / predicate) — Phase 1 spec SHIPPED

**Iteration:** 24 of 34+ · **Role:** Developer · **Cycle:** iter-24 Phase 1 (spec)
**Captured:** 2026-07-13 · **Status:** spec SHIPPED · **Confidence:** high
**Anchored by:** `project:iter-23-critic-verdict-choose-f5-receptionist-subcommands-tier-2-carry-forward-r` (composite 18 raw / 13.77 risk-adjusted; both-kind-triage rank-1; Pattern F chain-extension of iter-16 SHIPPED Tier-1 wiring)

## PROTECTED — Acceptance Criteria (BYTE-IDENTICAL to spec.yaml AC block)

```yaml
acceptance_criteria:
  - id: AC-1
    ears: "When the user invokes `python -m kurort_engine rechnung issue` with a valid JSON payload supplied either via stdin or via `--input-file <path.json>`, the system shall parse monetary fields as `Decimal(string_value)` (no raw float), validate the payload schema, and emit a GoBD §10 retention-compliant text-only output on stdout; and the system shall exit 0 on success or exit non-zero with a structured error message on schema violation."
    test_oracle: tests/test_f5_receptionist_subcommands_tier2.py::test_ac1_rechnung_issue_subcommand_emits_gobd_text
  - id: AC-2
    ears: "If the user invokes `python -m kurort_engine dsgvo cascade` with a `guest_id` argument, then the system shall execute the in-house retention cascade via `kurort_engine.kurgaste_retention.auto_cascade.run_cascade(guest_id)`, restrict the cascade to the in-house data inventory (no cross-border subprocessor work), and report the planned retention actions to stdout as a JSON object with at minimum the keys `guest_id`, `actions_planned`, and `actions_count`."
    test_oracle: tests/test_f5_receptionist_subcommands_tier2.py::test_ac2_dsgvo_cascade_subcommand_reports_in_house_actions
  - id: AC-3
    ears: "When the user invokes `python -m kurort_engine predicate file` with a `year` argument (integer) and a `heilbad_code` argument (string), then the system shall dispatch to `kurort_engine.predicate_filing.run(year, heilbad_code)`, persist the predicate artifact to the configured output directory, and emit a success line on stdout containing the year, the heilbad_code, and the persisted artifact path."
    test_oracle: tests/test_f5_receptionist_subcommands_tier2.py::test_ac3_predicate_file_subcommand_persists_artifact
```

**PROTECTED block integrity:**
- SHA-256 of AC block: `ba4fa092c99d087bfde3a6a669016e889931f3bd39fcf4593fc34678ffb9fbba`
- Byte count of AC block: 1754
- The block above MUST be byte-identical to the `acceptance_criteria:` block in `repo/spec/f5_receptionist_tier2_rechnung_dsgvo_predicate/spec.yaml`. Any drift → re-stamp the SHA and document the revision in the retrospective.

## spec.yaml SHA-256 (locked at Phase 1 spec SHIPPED)

```
afbee62dbf41bb458100d1b9c979406c758a48b340c00433856372aa32b6af0b  spec/f5_receptionist_tier2_rechnung_dsgvo_predicate/spec.yaml
```

**Verification command:** `shasum -a 256 repo/spec/f5_receptionist_tier2_rechnung_dsgvo_predicate/spec.yaml`
must return `afbee62dbf41bb458100d1b9c979406c758a48b340c00433856372aa32b6af0b`.
Any drift → re-stamp the SHA and document the revision in the retrospective.

## STALE_PENDING_FLAG

`<!-- STALE_PENDING_FLAG: not set — all 3 ACs ship in this cycle (no deferred review paths). -->`

**Current value:** CLEAR (3 ACs all ship in the same iter-24 cycle; no manual-review deferral).

## 7 SHAs to preserve verbatim (Pattern C chain-extension anti-drift)

iter-24 Developer MUST NOT modify any of these. Phase 5 integration verification:
`git diff HEAD~1 --stat` MUST show 0 lines changed in any of the 7 SHAs.

| # | SHA-source                                                            | SHIPPED iteration    | Why preserved |
|---|-----------------------------------------------------------------------|----------------------|---------------|
| 1 | `src/kurort_engine/rechnung.py`                                         | iter-15 SHIPPED      | Tier-2 wiring source for `rechnung issue` subcommand (AC-1) |
| 2 | `src/kurort_engine/kurgaste_retention/auto_cascade.py`                  | iter-38 SHIPPED      | Tier-2 wiring source for `dsgvo cascade` subcommand (AC-2) |
| 3 | `src/kurort_engine/predicate_filing/__init__.py`                        | iter-33 SHIPPED      | Tier-2 wiring source for `predicate file` subcommand (AC-3) |
| 4 | `src/kurort_engine/__main__.py` (Tier-1 lines 50-149 only)             | iter-16 SHIPPED      | Tier-1 4-of-6 wiring baseline; Tier-2 subparsers ADD under existing `add_subparsers(dest="subcommand")` |
| 5 | `src/kurort_engine/__init__.py:parse_subcommand` (Tier-1 dispatcher)   | iter-16 SHIPPED      | Tier-1 4-of-6 dispatch baseline; Tier-2 handlers ADD |
| 6 | `src/kurort_engine/meldeschein.py`                                      | iter-15 SHIPPED      | Tier-1 read-only consumer; regression-locked |
| 7 | `src/kurort_engine/kurtaxe.py`                                          | iter-15 SHIPPED      | Tier-1 read-only consumer; regression-locked |

## Traceability matrix (initialized at Phase 1 spec SHIPPED)

| AC ID | Test oracle path                                                                              | Status      | Phase           |
|-------|-----------------------------------------------------------------------------------------------|-------------|-----------------|
| AC-1  | tests/test_f5_receptionist_subcommands_tier2.py::test_ac1_rechnung_issue_subcommand_emits_gobd_text | green       | Phase 3 (green) |
| AC-2  | tests/test_f5_receptionist_subcommands_tier2.py::test_ac2_dsgvo_cascade_subcommand_reports_in_house_actions | green       | Phase 3 (green) |
| AC-3  | tests/test_f5_receptionist_subcommands_tier2.py::test_ac3_predicate_file_subcommand_persists_artifact | green       | Phase 3 (green) |

**Lifecycle:** `not_started` → `red` (Phase 2) → `green` (Phase 3) → `verified` (Phase 5 integration).
**Update mechanism:** Python in-place replacement via `run_command` (NOT `write_file`,
`edit_file`, or `sed`) per pinned memory [2]. The PROTECTED AC block above is byte-identical
to `spec.yaml` acceptance_criteria block; SHA-256 of the block is preserved across matrix updates.

## Verification commands (mirrored from spec.yaml done_when)

```bash
# 1. spec SHA-256 lock verification
shasum -a 256 repo/spec/f5_receptionist_tier2_rechnung_dsgvo_predicate/spec.yaml
# Expected: afbee62dbf41bb458100d1b9c979406c758a48b340c00433856372aa32b6af0b

# 2. AC block byte-identity (spec.yaml vs spec_lock.md)
python3 -c "
import hashlib, pathlib, re
spec = pathlib.Path('repo/spec/f5_receptionist_tier2_rechnung_dsgvo_predicate/spec.yaml').read_text()
lock = pathlib.Path('repo/spec/f5_receptionist_tier2_rechnung_dsgvo_predicate/spec.lock.md').read_text()
m_spec = re.search(r'\n(acceptance_criteria:\n(?:  [^\n]*\n)+)', spec)
ac_spec = m_spec.group(1).rstrip('\n')
# Extract AC block from spec_lock.md between the ```yaml fences
m_lock = re.search(r'```yaml\n(acceptance_criteria:\n(?:  [^\n]*\n)+)```', lock)
ac_lock = m_lock.group(1).rstrip('\n')
assert ac_spec == ac_lock, 'PROTECTED block drift: spec.yaml != spec_lock.md'
print('PROTECTED block byte-identity: VERIFIED')
print('AC block sha256 =', hashlib.sha256(ac_spec.encode()).hexdigest())
print('AC block byte_count =', len(ac_spec.encode()))
"
# Expected: PROTECTED block byte-identity: VERIFIED

# 3. VC1 — Tier-2 subparsers wired in __main__.py
grep -nE 'rechnung|dsgvo|predicate' repo/src/kurort_engine/__main__.py
# Expected: ≥3 matches (each Tier-2 subcommand added under add_subparsers(dest="subcommand"))

# 4. VC2 — CLI surface lists 7 subcommands
PYTHONPATH=repo/src ./.venv/bin/python -m kurort_engine --help
# Expected: subcommands include meldeschein, kurtaxe, remittance, arrival, rechnung, dsgvo, predicate

# 5. VC3 — Tier-2 handlers in __init__.py:parse_subcommand dispatcher
grep -nE 'def _cmd_rechnung|def _cmd_dsgvo|def _cmd_predicate|def _handle_rechnung|def _handle_dsgvo|def _handle_predicate' repo/src/kurort_engine/__init__.py
# Expected: ≥3 handler functions or subcommand dispatchers

# 6. VC4 — Library-module existence (no regression)
file_exists repo/src/kurort_engine/rechnung.py
file_exists repo/src/kurort_engine/kurgaste_retention/auto_cascade.py
file_exists repo/src/kurort_engine/predicate_filing/__init__.py
# Expected: all 3 exist

# 7. VC5 — pytest regression (Tier-2 wiring does not break Tier-1)
cd repo && PYTHONPATH=src ./.venv/bin/pytest tests/ -x --tb=short
# Expected: ≥137 PASS (iter-16 baseline) + Tier-2 new tests; 0 FAIL

# 8. 7 SHAs anti-drift
cd repo && git diff HEAD~1 --stat
# Expected: 0 lines changed in rechnung.py, kurgaste_retention/auto_cascade.py,
#   predicate_filing/__init__.py, __main__.py Tier-1 lines 50-149, __init__.py:parse_subcommand Tier-1,
#   meldeschein.py, kurtaxe.py

# 9. ruff lint on Tier-2 wiring files
cd repo && ruff check src/kurort_engine/__main__.py src/kurort_engine/__init__.py
# Expected: All checks passed!
```

## Cross-references

- `repo/spec/f5_receptionist_tier2_rechnung_dsgvo_predicate/spec.yaml` — spec source (SHA-256 `afbee62dbf41bb458100d1b9c979406c758a48b340c00433856372aa32b6af0b`)
- `project:iter-23-critic-verdict-choose-f5-receptionist-subcommands-tier-2-carry-forward-r` — binding verdict (composite 18 raw / 13.77 risk-adjusted)
- `project:iter-23-critic-handoff-to-iter-24-developer-f5-receptionist-subcommands-tier-2-c` — Critic handoff
- `project:iter-24-developer-spec-input-f5-tier-2-rechnungdsgvopredicate` — spec-input synthesis (R1-R6 risk register + 5 VCs)
- `project:iter-17-developer-handoff-f5-tier-2-follow-ups-rechnung-dsgvo-predicate` — handoff for AC-1 stdin/--input-file ergonomics (R6) and Decimal round-trip (R5)
- `project:iter-16-spec-shipped-f5-receptionist-subcommands-t1-locked` — Tier-1 spec precedent (format precedent)
- `repo/spec/avv_kaskade/spec.yaml` — Pattern C chain-extension format precedent
- `repo/spec/avv_kaskade/spec.lock.md` — Pattern C chain-extension format precedent (locked-block format)
- `lawyer-budget-gate-state-of-project-crossed-5-iteration-threshold-at-iter-26-was` — Mix-B gate (dsgvo cascade is in-house only per R4)

## Phase boundary tag (convention per pinned memory [8])

- Phase 1 spec SHIPPED tag: `iter24-phase-1-spec-complete`
- Apply at Phase 1 spec SHIPPED (i.e., after this file is written + matrix initialized).
- Authoritative merge status: per `retros/024-developer-*.md` (to be created at Phase 5 integration).
