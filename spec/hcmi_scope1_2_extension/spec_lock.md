# iter-30 spec_lock.md — hcmi_scope1_2_extension — Phase 1 spec SHIPPED

**Iteration:** 30 of 34+ · **Role:** Developer · **Cycle:** iter-30 Phase 1 (spec)
**Captured:** 2026-07-13 (per Phase 1 spec timing) · **Status:** spec SHIPPED · **Confidence:** HIGH
**Anchored by:** `output/reviews/029_critic_verdict_iter29_pool3_tier1_triage.md` §11 binding contract (5 AC EARS verbatim)

> ⚠️ **PROTECTED BLOCK — DO NOT EDIT** ⚠️
> The `## Acceptance Criteria` block below is byte-identical to the `acceptance_criteria:`
> block in `repo/spec/hcmi_scope1_2_extension/spec.yaml`. Any drift between this block and
> spec.yaml is FAIL by verify-before-done skill. If an AC must change, the AC block must be
> revised through a strategic-phase spec revision (NOT by editing this file directly),
> per pinned memory [1] "the locked spec SHA-256 must never be rewritten to match what landed".

## PROTECTED — Acceptance Criteria (BYTE-IDENTICAL to spec.yaml AC block)

```yaml
acceptance_criteria:
  - id: AC-1
    ears: "Ubiquitous: The system shall expose calculate_scope_1(heating_kwh_annual, refrigeration_kwh_annual) which returns a dict whose keys are heating_tco2e (Toskana heating 0.05 kg CO2e/kWh, re-use of SHIPPED scope1_heating_thermal_spring_emissions), refrigeration_tco2e (HCMI 0.15 kg CO2e/kWh), and total_scope1_tco2e (heating + refrigeration); and the system shall raise ValueError when either argument is < 0; and the module docstring SHALL cite 'Sustainable Hospitality Alliance (SHA) HCMI methodology' as the canonical reference."
    test_oracle: tests/test_hcmi_scope1_2.py::test_ac1_calculate_scope_1_emits_hcmi_scope_1_dict
  - id: AC-2
    ears: "Event-driven: When calculate_scope_2(purchased_electricity_kwh_annual, green_electricity_contract: bool) is called and green_electricity_contract is False, the system shall compute grid_tco2e using DE Strommix 2026 0.42 kg CO2e/kWh; and when green_electricity_contract is True, the system shall compute green_electricity_tco2e using OK Lab certified-green 0.02 kg CO2e/kWh; and the returned dict shall contain both grid_tco2e and green_electricity_tco2e keys plus total_scope2_tco2e; and the system shall raise ValueError when purchased_electricity_kwh_annual < 0."
    test_oracle: tests/test_hcmi_scope1_2.py::test_ac2_calculate_scope_2_green_contract_param_selects_factor
  - id: AC-3
    ears: "Event-driven: When calculate_scope_1_2(heating_kwh_annual, refrigeration_kwh_annual, purchased_electricity_kwh_annual, green_electricity_contract: bool) is called, the system shall return a dict with keys scope1 (verbatim AC-1 result dict), scope2 (verbatim AC-2 result dict), and total_scope1_2_tco2e (sum of AC-1 total + AC-2 total); and the returned dict shall be JSON-serializable via json.dumps(result, default=str)."
    test_oracle: tests/test_hcmi_scope1_2.py::test_ac3_calculate_scope_1_2_emits_unified_hcmi_dict
  - id: AC-4
    ears: "Event-driven: When generate_heilbad_2036_esg_narrative(heating_kwh_annual, refrigeration_kwh_annual, purchased_electricity_kwh_annual, green_electricity_contract: bool) is called, the system shall return a dict whose predicate_label == 'Heilbad Bad Orb (Hessischer Heilbäderverband)' and whose narrative_de (>= 300 chars) and narrative_en (>= 300 chars) both reference the 6 canonical Kurort-vertical anchors (Spessart Bike Tage, R3 Kinzigtal, WaldErfahren, E-Bike charging, Toskana Therme, thermal-spring NiedrigEnergie); and whose representative_period == (date(2036, 1, 1), date(2036, 12, 31)); and whose lang == 'de'; and whose accessibility_label length is >= 20 chars."
    test_oracle: tests/test_hcmi_scope1_2.py::test_ac4_generate_heilbad_2036_esg_narrative_emits_repraedikatisierung_dict
  - id: AC-5
    ears: "Unwanted-behavior: When export_scope1_2_bfsg_aa(disclosure_payload) is called with a payload whose lang is not 'de' or whose accessibility_label is missing or empty, the system shall raise BFSGComplianceError (re-use of SHIPPED iter-21 kurort_engine.kurkarte_wallet.BFSGComplianceError); and when the payload is BFSG-compliant, the system shall return a dict whose compliance_ok == True and whose footer includes the verbatim non-affirmation clause 'This ESG disclosure is voluntary and is provided as ESG-readiness positioning for Bad Orb Heilbad 2036 Reprädikatisierung planning window; it is NOT a regulatory compliance attestation' AND the SHA methodology citation 'Sustainable Hospitality Alliance (SHA) HCMI methodology'; and the returned dict metadata shall include screen-reader text contrast >= 4.5:1."
    test_oracle: tests/test_hcmi_scope1_2.py::test_ac5_export_scope1_2_bfsg_aa_enforces_lang_de_and_non_affirmation_footer

```

## Lock metadata

| Field | Value |
|---|---|
| spec.yaml SHA-256 | `a28800eaf43ff090056af23e3bb9560e4243e9280f7a91201d321235ddfc5b53` |
| AC block SHA-256 | `2f7a6830969b7ca9dbb7033b1335a2d164cf8dbbc4250ccff021e5f99bfc5f5b` |
| spec.yaml size | 9354 bytes |
| AC block size | 3701 bytes |
| AC count | 5 |
| Feature | hcmi-scope-12-extension |
| Phase | iter-30 Phase 1 (spec) — SHIPPED |
| Status | lock-frozen; red phase may now begin |

**Verification commands** (mirror spec.yaml `done_when` #1 and #6):

```bash
# 1. spec.yaml SHA verification
shasum -a 256 repo/spec/hcmi_scope1_2_extension/spec.yaml
# Expected: cf0915d028cc5d218f64f1f562906e14a971f190626b8214a151dc9ac11a4e78

# 2. PROTECTED AC block byte-identity check (must print "PROTECTED block byte-identity: VERIFIED")
python3 -c "
import re
spec = open('repo/spec/hcmi_scope1_2_extension/spec.yaml','rb').read()
m = re.search(rb'acceptance_criteria:.*?(?=\nnot_included:|\ndone_when:|\nassumptions:)', spec, re.DOTALL)
lock = open('repo/spec/hcmi_scope1_2_extension/spec_lock.md','rb').read()
idx = lock.find(b'```yaml\n') + len(b'```yaml\n')
end = lock.find(b'```\n', idx)
assert spec[m.start():m.end()] == lock[idx:end], 'PROTECTED block drift: spec.yaml != spec_lock.md'
print('PROTECTED block byte-identity: VERIFIED')
"
```

## 5 SHAs to preserve verbatim (Pattern C chain-extension anti-drift surface)

The 5 SHIPPED Q5.1 src files are read-only consumers of `hcmi_scope1_2_calculator.py` and
`heilbad_predicate_2036_reprädikatisierung.py`. iter-30+ Developer MUST NOT modify the bodies
of any of these files; only `src/kurort_engine/esg/report/__init__.py` may receive additive-only
re-export entries for the 4 NEW symbols (Pattern C chain-extension).

| # | File | READ-ONLY role | File HEAD SHA-256 |
|---|---|---|---|
| 1 | `src/kurort_engine/esg/__init__.py` | Q5.1 SHIPPED base package re-export | `b00acc9e51af8ca7d5cdccde5d8a83624a0655fc2e1aff8473f3f095024becac` |
| 2 | `src/kurort_engine/esg/report/__init__.py` | Q5.1 SHIPPED report package re-export (additive-only re-export permitted) | `d29f01c66ab05a14eb01cc1ac27b925d7e8cbd933a001d710c0c90e62025efbc` |
| 3 | `src/kurort_engine/esg/report/vsme_collector.py` | Q5.1 SHIPPED VSME collector (read-only) | `9242121fe1b24ed8581e7b8368d50d5b7dac4b4b2910d1733ec903f74d598837` |
| 4 | `src/kurort_engine/esg/report/hcmi_scope3_calculator.py` | Q5.1 SHIPPED HCMI Scope 3 calculator (read-only) | `210eef3494696f2af99b3093bc178e18417b319cb59d4ec0d9c02803215e0c1e` |
| 5 | `src/kurort_engine/esg/report/scope1_heating_thermal_spring.py` | Q5.1 SHIPPED Toskana heating/thermal-spring emissions (read-only; reused for AC-1) | `a41fe19a444422d68d45da541e27c9b002ddba6367ae81977b991fac621dd816` |



**Anti-drift verification command (Phase 5 integration check)**

```bash
cd repo && git diff HEAD~1 --stat
# Expected: 0 lines changed in any of the 5 files listed above;
# ONLY the 2 NEW src files (hcmi_scope1_2_calculator.py + heilbad_predicate_2036_reprädikatisierung.py)
# plus the additive-only __init__.py re-export; plus 1 NEW tests/test_hcmi_scope1_2.py file.
```

## Traceability matrix (initialized at Phase 1 spec SHIPPED)

| AC ID | Test oracle path | Status | Phase |
|-------|------------------|--------|-------|
| AC-1 | tests/test_hcmi_scope1_2.py::test_ac1_calculate_scope_1_emits_hcmi_scope_1_dict | not_started | Phase 2 (red) |
| AC-2 | tests/test_hcmi_scope1_2.py::test_ac2_calculate_scope_2_green_contract_param_selects_factor | not_started | Phase 2 (red) |
| AC-3 | tests/test_hcmi_scope1_2.py::test_ac3_calculate_scope_1_2_emits_unified_hcmi_dict | not_started | Phase 2 (red) |
| AC-4 | tests/test_hcmi_scope1_2.py::test_ac4_generate_heilbad_2036_esg_narrative_emits_repraedikatisierung_dict | not_started | Phase 2 (red) |
| AC-5 | tests/test_hcmi_scope1_2.py::test_ac5_export_scope1_2_bfsg_aa_enforces_lang_de_and_non_affirmation_footer | not_started | Phase 2 (red) |

**Lifecycle:** `not_started` → `red` (Phase 2) → `green` (Phase 3) → `verified` (Phase 5 integration).
**Update mechanism:** Python in-place replacement via `run_command` (NOT write_file or sed) per
pinned memory [2]. The PROTECTED AC block above is byte-identical to `spec.yaml` `acceptance_criteria:`
block; SHA-256 of the block is preserved across matrix updates.

## Cross-references

- `repo/spec/hcmi_scope1_2_extension/spec.yaml` — spec source (SHA-256 `{spec_sha}`)
- `output/reviews/029_critic_verdict_iter29_pool3_tier1_triage.md` §11 — binding contract (5 ACs)
- `iter-30-spec-input-synthesis-hcmi-scope-12-extension-chosen-action-distillation` — KB spec-input synthesis
- `iter-30-red-input-synthesis-hcmi-scope-12-red-test-conventions-5-ac-ears-verbati` — KB red-input synthesis
- `iter-30-developer-pinned-tdd-rules-hcmi-scope-12-extension` — TDD discipline + 5 SHAs anchor
- `repo/spec/avv_kaskade/spec.lock.md` — file layout precedent (iter-28 SHIPPED)
- `iter-27-deliverable-summary-q51-esg-csrdvsme-hcmi-scope-3-bfsg-aa-esg-disclosure` — Q5.1 SHIPPED foundation (Pattern C chain-extension target)

## Phase boundary tag (convention per pinned memory [8])

- Phase 1 spec SHIPPED tag: `iter30-phase-1-spec-complete`
- Apply at Phase 1 spec SHIPPED (after this file is written + matrix initialized).
- Authoritative merge status: per `retros/` (created at Phase 5).
