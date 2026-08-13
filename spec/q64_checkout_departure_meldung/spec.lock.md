# iter-6 spec_lock.md — q64_checkout_departure_meldung (departure-Meldung mirror) — Phase 1 spec SHIPPED

**Iteration:** 6 of 30+ · **Role:** Developer · **Cycle:** iter-6 Phase 1 (spec)
**Captured:** 2026-07-12 · **Status:** spec SHIPPED · **Confidence:** high
**Anchored by:** iter-5-critic-verdict-choose-q64-checkout-departure-meldung-mirror-as-next-action (CD3 verdict, Tier-2 PRIMARY 20/25, Mix B SAFE, confidence HIGH 0.88)

## PROTECTED — Acceptance Criteria (BYTE-IDENTICAL to spec.yaml AC block)

```yaml
acceptance_criteria:
  - id: AC-1
    ears: "When f5_q64_checkout.checkout(gast_id, today) is invoked for a foreign-guest gast_id (Ausweis-Seriennummer Pflicht per BMG § 30 Abs. 2), the system shall load the SHIPPED MeldescheinForm for gast_id, populate the previously-null Abreisedatum field with today, verify the existing BMG § 30 Pflichtangaben surface, and emit a q64.checkout.completed event carrying (ausweis_seriennummer, abreisedatum, gast_kategorie) for § 30 BMG + § 15 Abs. 3 Kurverwaltung-Bad-Orb discharge."
    test_oracle: tests/test_q64_checkout_departure_meldung.py::test_ac1_foreign_guest_checkout_populates_abreisedatum_and_emits_event
  - id: AC-2
    ears: "When emit_departure_meldung(gast_id, abreisedatum, anreisedatum, kurtaxe_betrag, kurbeitragspflichtige_uebernachtungen_watermark) is called on the Kurverwaltung-Bad-Orb endpoint, the system shall be idempotent for the same (gast_id, abreisedatum) pair (re-emission returns the existing emission_id and is a no-op for state) and shall append a q64.audit_log_entry with idempotency_key = sha256(gast_id + abreisedatum + emission_timestamp).hexdigest() per the SHIPPED kurgaste_retention.auditlog companion-pattern."
    test_oracle: tests/test_q64_checkout_departure_meldung.py::test_ac2_departure_meldung_event_idempotent_and_audit_logged
  - id: AC-3
    ears: "When redeem_gutschein(gast_id, issuer, code) is called at checkout, the system shall validate the code via kurpaket_orchestrator.lookup_gutschein(issuer, code), append one row to gutschein_redemption_ledger with fields (redemption_id, gast_id, code, issuer, redeemed_at, redeemed_value, audit_chain_hash) where audit_chain_hash = sha256(redemption_id + gast_id + code + str(redeemed_value)).hexdigest(), and apply redeemed_value to the checkout-summary PDF total (the SHIPPED checkout_form.total_kurtaxe is reduced by redeemed_value before § 35 KAG Abrechnung)."
    test_oracle: tests/test_q64_checkout_departure_meldung.py::test_ac3_gutschein_redemption_validates_appends_ledger_and_applies_value
  - id: AC-4
    ears: "When compute_commission_split(booking_id, channel) is called for an OTA- or Reisebüro-routed booking routed via the SHIPPED channel_manager_minstay, the system shall return a CommissionSplit whose rate is read from commission_split_table.json per (a) booking_com: 0.15, (b) agoda: 0.12, (c) trivago: 0.0 (lead-gen only), (d) reisebuero_x_negotiated: the negotiated entry in the table (config-only update, no code change), (e) direct: 0.0; and shall emit a q64.commission_split.calculated event with idempotency_key = sha256(booking_id + commission_table_version).hexdigest(); and shall raise ValueError citing the unsupported channel for any channel not present in commission_split_table.json."
    test_oracle: tests/test_q64_checkout_departure_meldung.py::test_ac4_reisebuero_commission_split_per_table_with_idempotency_key
  - id: AC-5
    ears: "When f5_q64_checkout.checkout(gast_id, today) is invoked for a German-guest gast_id (BEG IV 2025-01-01 carve-out — no Meldepflicht per pinned memory [6] / [9]), the system shall NOT require a Meldeschein completion and shall skip the BMG § 30 Pflichtangaben verification surface, but shall still emit emit_departure_meldung per § 15 Abs. 3 Kurverwaltung-Bad-Orb (AC-2 surface) and shall still apply redeem_gutschein (AC-3 surface) and compute_commission_split (AC-4 surface) when those code paths are reached."
    test_oracle: tests/test_q64_checkout_departure_meldung.py::test_ac5_german_guest_beg_iv_carve_out_skips_meldepflicht_but_keeps_ordinance


```

## spec.yaml SHA-256 (locked at Phase 1 spec SHIPPED)

```
987ff5cb49655576f61a9ed5481f888cde1f3be210091fbdf3fc8cd17b609020  spec/q64_checkout_departure_meldung/spec.yaml
```

**Verification command:** `shasum -a 256 repo/spec/q64_checkout_departure_meldung/spec.yaml`
must return `987ff5cb49655576f61a9ed5481f888cde1f3be210091fbdf3fc8cd17b609020`.
Any drift → re-stamp the SHA and document the revision in the retrospective.

## STALE_PENDING_FLAG

`<!-- STALE_PENDING_FLAG: not currently triggered; iter-6 q64_checkout Pattern F instantiation is FRESH, all design records are status=active (not RATIFIED-COMPLETED), per pinned memory [2] iter-27 stale-kickoff post-iter-39 Scholar seal -->`

**Current value:** CLEAR. No stale-kickoff risk; q64 design records are `status=active` (not RATIFIED-COMPLETED).

**Flipped by:** the strategic-review phase (Phase 6) if the spec.yaml SHA drifts or any of the 6 Pattern F anchors is modified.

## IMPORT_DISCIPLINE

`<!-- IMPORT_DISCIPLINE: q64_checkout EXTENDS the 6 SHIPPED Pattern F anchor modules; NO modification to any of the 6 anchors is permitted per iter-6-pinned-rules §3.1 Pattern F strict discipline -->`

## 6 SHAs to preserve verbatim (Pattern F chain-extension anti-drift)

iter-6 Developer MUST NOT modify any of these. Phase 5 integration verification:
`git diff HEAD~1 --stat` MUST show 0 lines changed in any of the 6 SHAs.

| # | SHA-source                                                                  | SHIPPED iteration | Why preserved |
|---|-----------------------------------------------------------------------------|-------------------|---------------|
| 1 | `src/kurort_engine/meldeschein/__init__.py`                                  | iter-6 SHIPPED    | PRIMARY extension target — q64 checkout_form EXTENDS MeldescheinForm non-destructively |
| 2 | `src/kurort_engine/kurverwaltung/__init__.py`                                | iter-36 SHIPPED   | 4-tier Satzung 2026 verbatim (Kurtaxe Abrechnung compute) |
| 3 | `src/kurort_engine/kurkarte_wallet/__init__.py`                              | iter-21 SHIPPED   | PKPass issuer — read-only consumer |
| 4 | `src/kurort_engine/kurpaket_orchestrator/__init__.py`                        | iter-18 SHIPPED   | Gutschein-code issuance — read-only consumer (lookup_gutschein) |
| 5 | `src/kurort_engine/channel_manager_minstay/__init__.py`                      | iter-15 SHIPPED   | OTA/Reisebüro routing layer — read-only consumer |
| 6 | `src/kurort_engine/kurgaste_retention/__init__.py`                           | iter-38 SHIPPED   | DSGVO Art. 30 VVT audit-log companion-pattern |

## Traceability matrix (initialized at Phase 1 spec SHIPPED)

| AC ID | Test oracle path                                                                                  | Status      | Phase           |
|-------|---------------------------------------------------------------------------------------------------|-------------|-----------------|
| AC-1  | tests/test_q64_checkout_departure_meldung.py::test_ac1_foreign_guest_checkout_populates_abreisedatum_and_emits_event | red         | Phase 2 (red)   |
| AC-2  | tests/test_q64_checkout_departure_meldung.py::test_ac2_departure_meldung_event_idempotent_and_audit_logged | red         | Phase 2 (red)   |
| AC-3  | tests/test_q64_checkout_departure_meldung.py::test_ac3_gutschein_redemption_validates_appends_ledger_and_applies_value | red         | Phase 2 (red)   |
| AC-4  | tests/test_q64_checkout_departure_meldung.py::test_ac4_reisebuero_commission_split_per_table_with_idempotency_key | red         | Phase 2 (red)   |
| AC-5  | tests/test_q64_checkout_departure_meldung.py::test_ac5_german_guest_beg_iv_carve_out_skips_meldepflicht_but_keeps_ordinance | red         | Phase 2 (red)   |

**Lifecycle:** `not_started` → `red` (Phase 2) → `green` (Phase 3) → `verified` (Phase 5 integration).
**Update mechanism:** Python in-place replacement via `run_command` (NOT `write_file`,
`edit_file`, or `sed`) per pinned memory [2]. The PROTECTED AC block above is byte-identical
to `spec.yaml` acceptance_criteria block; SHA-256 of the block is preserved across matrix updates.

## Verification commands (mirrored from spec.yaml done_when)

```bash
# 1. spec SHA-256 lock verification
shasum -a 256 repo/spec/q64_checkout_departure_meldung/spec.yaml
# Expected: 987ff5cb49655576f61a9ed5481f888cde1f3be210091fbdf3fc8cd17b609020

# 2. 5 ACs GREEN at Phase 3
cd repo && PYTHONPATH=src python3 -m pytest tests/test_q64_checkout_departure_meldung.py -v --override-ini="addopts=--tb=short"
# Expected: 5 passed, 0 failed (one test per AC-1..AC-5)

# 3. 118 PASS baseline preservation (REGRESS-SHIP TEST)
cd repo && PYTHONPATH=src python3 -m pytest tests/ -q | tail -5
# Expected: >=118 passed (118 PASS baseline per iter-38 must be preserved; 118 + 5 NEW = 123 at Phase 3 GREEN end-state)

# 4. file_exists checks
file_exists repo/src/kurort_engine/q64_checkout/__init__.py  # Expected: Exists (file)
file_exists repo/src/kurort_engine/q64_checkout/checkout_form.py  # Expected: Exists (file)

# 5. ruff lint
cd repo && ruff check src/kurort_engine/q64_checkout/
# Expected: All checks passed!

# 6. PROTECTED block byte-identity verification
python3 -c "
import hashlib, re
with open('repo/spec/q64_checkout_departure_meldung/spec.yaml','rb') as f:
    spec_yaml_bytes = f.read()
m = re.search(rb'acceptance_criteria:.*?(?=\nnot_included:|\ndone_when:|\nassumptions:)', spec_yaml_bytes, re.DOTALL)
assert m, 'AC block not found in spec.yaml'
spec_ac_block = m.group(0) + b'\n'
with open('repo/spec/q64_checkout_departure_meldung/spec.lock.md','rb') as f:
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

- `repo/spec/q64_checkout_departure_meldung/spec.yaml` — the spec source (SHA-256 above)
- `iter-5-critic-verdict-choose-q64-checkout-departure-meldung-mirror-as-next-action` — CD3 verdict
- `q64checkout-departure-meldung-mirror-extending-kurort-vertical-meldeschein-to-cl` — Scholar pick-first #2 (iter-4 Proposal-002)
- `iter-6-developer-pinned-rules-q64checkout-departure-meldung-mirror-tdd-disciplin` — TDD discipline + forbidden patterns
- `repo-map-kurortengine-python-pytest-ruff-iter-6-q64checkout-context` — repo map
- `verdict-iter-5-choose-q64checkout-departure-meldung-mirror-as-the-next-action-ov` — verification commands V1-V6
- `repo/spec/avv_kaskade/spec.lock.md` — reference template for PROTECTED block shape

## Phase boundary tag (convention per pinned memory [8])

- Phase 1 spec SHIPPED tag: `<branch>-q64-checkout-phase-1-spec-complete`
- Apply at Phase 1 spec SHIPPED (i.e., after this file is written + matrix initialized).
