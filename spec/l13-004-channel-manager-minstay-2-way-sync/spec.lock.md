# iter-15 spec_lock.md — l13-004_channel_manager_minstay_2-way_sync — Phase 1 spec SHIPPED

**Iteration:** 15 of 34+ · **Role:** Developer · **Cycle:** iter-15 Phase 1 (spec)
**Captured:** 2026-07-13 · **Status:** spec SHIPPED · **Confidence:** high
**Anchored by:** verdict-iteration-14-choose-loop-13-proposal-004-channel-manager-minstay-2-way-sync-b (iter-14 Critic chose L13-004 as iter-15+ Developer deliverable)
**Coverage handoff:** iter-14-coverage-handoff-critic-iter-14-complete-l13-004-chosen-as-iter-15-devel

## PROTECTED — Acceptance Criteria (BYTE-IDENTICAL to spec.yaml AC block)

```yaml
acceptance_criteria:
  - id: AC-1
    ears: >-
      The channel_manager_minstay package shall expose a
      `load_minlos_profile(bundesland: str, kurort: str) -> MinLosProfile`
      function that loads a YAML profile from
      `repo/src/channel_manager_minstay/profiles/<bundesland>_<kurort>_minlos.yaml`
      and returns a `MinLosProfile` whose `rules` tuple contains exactly the
      five canonical DHV Saison entries — `easter`, `whitsun`, `summer`,
      `christmas`, plus one default `shoulder` rule — with each rule carrying
      a `date_range: ("YYYY-MM-DD", "YYYY-MM-DD")` tuple, a `minlos: int`
      nights count, and an `applies_to_ota: bool` flag, parsed via `PyYAML`'s
      `safe_load` (NOT `yaml.load`) so that an untrusted profile cannot
      execute arbitrary Python.
    test_oracle: >-
      repo/tests/test_channel_manager_minstay.py::test_ac1_minlos_profile_loader_returns_5_dhv_saison_rules

  - id: AC-2
    ears: >-
      When `BookingComConnector.exchange_token(client_id, client_secret)` is
      invoked, the connector shall POST to the
      `/connectivity/token-based-authentication/exchange` endpoint with
      `application/x-www-form-urlencoded` body containing `client_id` +
      `client_secret` and a `User-Agent: kurort_engine/<version>` header,
      shall cache the returned bearer access token for the duration of the
      process, and shall attach `Authorization: Bearer <token>` to every
      subsequent Connectivity API call; if the HTTP transport is a stub that
      returns a pre-canned `{"access_token": "fake-...", "expires_in": 3600}`
      JSON body, the connector shall use the stubbed value verbatim (so the
      test can assert the round-trip without real Booking.com credentials).
    test_oracle: >-
      repo/tests/test_channel_manager_minstay.py::test_ac2_booking_com_oauth2_token_exchange_and_authorization_header

  - id: AC-3
    ears: >-
      When `BookingComConnector.build_availnotif_envelope(minlos_rule,
      rate_plan_codes: tuple[str, ...], inv_type_codes: tuple[str, ...])`
      is invoked with a single MinLOS rule (e.g. `minlos=5`,
      `date_range=("2026-04-03","2026-04-12")`), the connector shall return a
      well-formed `OTA_HotelAvailNotif` XML envelope (parseable by
      `xml.etree.ElementTree.fromstring`) that contains one
      `<AvailStatusMessages>` block per RatePlan×InvType, one
      `<LengthsOfStay>/<LengthOfStay>` element per rule with child elements
      `<Time>{minlos}</Time>`, `<TimeUnit>Day</TimeUnit>`,
      `<ArrivalDateBased>0</ArrivalDateBased>`,
      `<MinMaxMessageType>SetMinLOS</MinMaxMessageType>`, and
      `<RestrictionStatus>Active</RestrictionStatus>`, exactly matching the
      OTA_HotelAvailNotif schema documented at
      `developers.booking.com/connectivity/docs/ota-hotelavailnotif` (Source 1862).
    test_oracle: >-
      repo/tests/test_channel_manager_minstay.py::test_ac3_booking_com_availnotif_xml_envelope_structure

  - id: AC-4
    ears: >-
      While `HrsCmConnector.push_minlos(profile, rate_plans)` is invoked
      with a `MinLosProfile`, the connector shall emit OTA-style XML pushes
      ONLY for rate types in the `RateTypeFilter` (default =
      `frozenset({"Special", "Hot deal", "Trade show"})`), shall silently skip
      Weekend Rate and Seasonal Rate entries per Source 1863 (SmartHOTEL
      connectguide) which documents that those rate types do NOT support
      MinLOS push via channel manager; the connector shall additionally
      attach an audit-trail record carrying `actor="hrs"`, the rate-type
      list that was sent, and a `latency_estimate="next-update-cycle"`
      marker per Source 1848 (Beds24 wiki) which documents that HRS
      MinLOS pushes are queued, not real-time.
    test_oracle: >-
      repo/tests/test_channel_manager_minstay.py::test_ac4_hrs_cm_connector_filters_rate_types_and_records_audit_latency

  - id: AC-5
    ears: >-
      When `MinLosValidator.validate(profile, existing_reservations)` is
      invoked with a `MinLosProfile` and a list of `kurort_engine.Reservation`
      objects, the validator shall return a `MinLosValidationReport` whose
      `violations` tuple lists one entry per (reservation, rule) pair where
      the reservation's `length_of_stay = (departure - arrival).days` is
      LESS than the matching profile rule's `minlos` for any date that
      overlaps the rule's `date_range`, and whose `conflicts` tuple is empty
      when no reservations violate; the validator shall compute
      `length_of_stay` using the same `(departure - arrival).days` formula
      that `kurort_engine.calculator` uses for Kurtaxe day-count, ensuring
      consistency between the validator and the existing rate engine.
    test_oracle: >-
      repo/tests/test_channel_manager_minstay.py::test_ac5_minlos_validator_flags_reservations_below_proposed_minlos

  - id: AC-6
    ears: >-
      When `MinLosScheduler.push(profile, dry_run=True)` is invoked with
      `dry_run=True`, the scheduler shall execute the full MinLOS-push
      pipeline (load profile → build Booking.com envelope → build HRS
      envelope → filter rate types → record audit entries) WITHOUT
      performing any network IO (the connector HTTP transport is replaced
      by a `DryRunTransport` that captures payloads in memory), shall
      return a `DryRunResult` carrying the captured Booking.com XML
      envelope, the captured HRS XML envelope, and a summary of the
      audit-log entries that WOULD have been written, and shall NOT call
      `urllib.request.urlopen` or any other network primitive (verified via
      a `DryRunTransport` sentinel that raises if any network call is
      attempted).
    test_oracle: >-
      repo/tests/test_channel_manager_minstay.py::test_ac6_minlos_scheduler_dry_run_emits_xml_without_network_io

  - id: AC-7
    ears: >-
      When `python -m channel_manager_minstay push --profile hessen_bad_orb
      --dry-run` is invoked from the repository root (with `PYTHONPATH=src`
      set so the package is importable), the CLI entry point shall exit 0
      silently (no stdout/stderr from the library code), shall write the
      captured Booking.com OTA_HotelAvailNotif XML envelope to stdout
      (one XML document per RatePlan×InvType combination), and shall exit 1
      with a structured error message on `--execute` mode if no
      Booking.com machine-account credentials are configured (so the user
      never accidentally pushes to a live OTA in CI).
    test_oracle: >-
      repo/tests/test_channel_manager_minstay.py::test_ac7_cli_push_dry_run_exit_zero_emits_booking_com_xml_envelope

# -----------------------------------------------------------------------------
# not_included — explicit scope boundaries (per pinned rule + iter-14 coverage
# handoff + 4 carry-forwards CF1-CF4)
# -----------------------------------------------------------------------------

```

## spec.yaml SHA-256 (locked at Phase 1 spec SHIPPED)

```
1be892763360db881db470a9599f07c093db1c3418efafee3deba1dc46ed762d  spec/l13-004-channel-manager-minstay-2-way-sync/spec.yaml
```

**Verification command:** `shasum -a 256 spec/l13-004-channel-manager-minstay-2-way-sync/spec.yaml`
must return `1be892763360db881db470a9599f07c093db1c3418efafee3deba1dc46ed762d`.
Any drift → re-stamp the SHA and document the revision in the retrospective.

## STALE_PENDING_FLAG

`<!-- STALE_PENDING_FLAG: not currently triggered; iter-15 l13-004-channel-manager-minstay is REGRESSION-LOCK cycle (the 7-AC test surface is SHIPPED at HEAD per Phase 1 verification, 7/7 tests pass); Pattern F stale-kickoff risk is LOW because L13-004 is the chosen action and the existing test_oracle surface is canonical -->`

**Current value:** CLEAR. No stale-kickoff risk; the iter-14 critic coverage handoff is active and the 7 test_oracle paths match the spec.yaml AC block verbatim.

**Flipped by:** the strategic-review phase (Phase 6) if the spec.yaml SHA drifts or any of the 6 Pattern F anchors (kurort_engine primitives) is modified by a channel_manager_minstay change.

## IMPORT_DISCIPLINE

`<!-- IMPORT_DISCIPLINE: channel_manager_minstay EXTENDS the SHIPPED L7-003 MinStay primitive (kurort_engine.rates.RateBand.min_stay + kurort_engine.rates.load_profile) via parity-convention, NEVER re-implements; Pattern F strict chain-extension discipline applies — the 6 SHIPPED Pattern F anchors below are read-only consumers, NOT modification targets -->`

## 6 SHAs to preserve verbatim (Pattern F chain-extension anti-drift)

iter-15 Developer MUST NOT modify any of these. Phase 5 integration verification:
`git diff HEAD~1 --stat` MUST show 0 lines changed in any of the 6 SHAs.

| # | SHA-source                                                       | SHIPPED iteration | Why preserved |
|---|------------------------------------------------------------------|-------------------|---------------|
| 1 | `src/kurort_engine/__init__.py` (kurort_engine AC-6 public API)  | iter-3 SHIPPED    | Public API namespace + __version__ parity for User-Agent header |
| 2 | `src/kurort_engine/rates.py` (L7-003 MinStay primitive)          | iter-9 SHIPPED    | PRIMARY extension target — RateBand.min_stay + load_profile parity |
| 3 | `src/kurort_engine/calculator.py` (Kurtaxe day-count)             | iter-3 SHIPPED    | validator._days_stay parity reference |
| 4 | `src/kurort_engine/audit.py` (AuditEntry + AuditLog)              | iter-3 SHIPPED    | audit_log: list[dict] parameter parity |
| 5 | `src/kurort_engine/exemptions.py` (Exemption dataclass)          | iter-3 SHIPPED    | Read-only consumer for type system |
| 6 | `src/kurort_engine/profiles/__init__.py` (Profile package init)  | iter-3 SHIPPED    | load_profile search-path pattern reference |

## Traceability matrix (initialized at Phase 1 spec SHIPPED)

| AC ID | Test oracle path                                                              | Status      | Phase           |
|-------|-------------------------------------------------------------------------------|-------------|-----------------|
| AC-1  | tests/test_channel_manager_minstay.py::test_ac1_minlos_profile_loader_returns_5_dhv_saison_rules | not_started | Phase 2 (red) — **already GREEN at HEAD** per regression-lock |
| AC-2  | tests/test_channel_manager_minstay.py::test_ac2_booking_com_oauth2_token_exchange_and_authorization_header | not_started | Phase 2 (red) — **already GREEN at HEAD** per regression-lock |
| AC-3  | tests/test_channel_manager_minstay.py::test_ac3_booking_com_availnotif_xml_envelope_structure | not_started | Phase 2 (red) — **already GREEN at HEAD** per regression-lock |
| AC-4  | tests/test_channel_manager_minstay.py::test_ac4_hrs_cm_connector_filters_rate_types_and_records_audit_latency | not_started | Phase 2 (red) — **already GREEN at HEAD** per regression-lock |
| AC-5  | tests/test_channel_manager_minstay.py::test_ac5_minlos_validator_flags_reservations_below_proposed_minlos | not_started | Phase 2 (red) — **already GREEN at HEAD** per regression-lock |
| AC-6  | tests/test_channel_manager_minstay.py::test_ac6_minlos_scheduler_dry_run_emits_xml_without_network_io | not_started | Phase 2 (red) — **already GREEN at HEAD** per regression-lock |
| AC-7  | tests/test_channel_manager_minstay.py::test_ac7_cli_push_dry_run_exit_zero_emits_booking_com_xml_envelope | not_started | Phase 2 (red) — **already GREEN at HEAD** per regression-lock |

**Lifecycle:** `not_started` → `red` (Phase 2) → `green` (Phase 3) → `verified` (Phase 5 integration).
**Update mechanism:** Python in-place replacement via `run_command` (NOT `write_file`, `edit_file`, or `sed`) per pinned memory [2]. The PROTECTED AC block above is byte-identical to `spec.yaml` acceptance_criteria block; SHA-256 of the block is preserved across matrix updates.

## Verification commands (mirrored from spec.yaml done_when)

```bash
# 1. spec SHA-256 lock verification
shasum -a 256 spec/l13-004-channel-manager-minstay-2-way-sync/spec.yaml
# Expected: 1be892763360db881db470a9599f07c093db1c3418efafee3deba1dc46ed762d

# 2. 7 ACs GREEN at Phase 3
cd repo && PYTHONPATH=src .venv/bin/python -m pytest tests/test_channel_manager_minstay.py -v --override-ini="addopts=--tb=short"
# Expected: 7 passed, 0 failed (7 tests covering AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7)

# 3. Baseline preservation + 7 NEW = 155 PASS
cd repo && PYTHONPATH=src .venv/bin/python -m pytest tests/ -q --override-ini="addopts=--tb=line"
# Expected: 155 passed, 0 failed (148 baseline + 7 channel_manager_minstay AC tests)
# NOTE: pre-existing 4 bitv20/audit failures are NOT caused by this iter and remain at 0 (no regressions introduced)

# 4. 6 SHAs anti-drift
cd repo && git diff HEAD --stat
# Expected: 0 lines changed in any of kurort_engine/__init__.py + rates.py + calculator.py + audit.py + exemptions.py + profiles/__init__.py

# 5. ruff lint
cd repo && .venv/bin/python -m ruff check src/channel_manager_minstay/
# Expected: All checks passed!

# 6. CLI dry-run exit 0
cd repo && PYTHONPATH=src .venv/bin/python -m channel_manager_minstay push --profile hessen_bad_orb --dry-run
# Expected: exit 0 + OTA_HotelAvailNotif envelope on stdout

# 7. PROTECTED block byte-identity verification (after any matrix update)
python3 -c "
import hashlib
with open('repo/spec/l13-004-channel-manager-minstay-2-way-sync/spec.yaml','rb') as f:
    spec_yaml_bytes = f.read()
import re
m = re.search(rb'acceptance_criteria:.*?(?=\nnot_included:|\ndone_when:|\nassumptions:)', spec_yaml_bytes, re.DOTALL)
assert m, 'AC block not found in spec.yaml'
spec_ac_block = m.group(0) + b'\n'
with open('repo/spec/l13-004-channel-manager-minstay-2-way-sync/spec.lock.md','rb') as f:
    lock_md_bytes = f.read()
lock_ac_marker = b'acceptance_criteria:\n'
lock_idx = lock_md_bytes.find(lock_ac_marker)
assert lock_idx != -1, 'AC block not found in spec.lock.md'
# Extract from spec.lock.md the AC block (between ```yaml and ```)
lock_yaml_start = lock_md_bytes.find(b'\`\`\`yaml\n') + len(b'\`\`\`yaml\n')
lock_yaml_end = lock_md_bytes.find(b'\n\`\`\`', lock_yaml_start)
lock_ac_block = lock_md_bytes[lock_yaml_start:lock_yaml_end] + b'\n'
assert spec_ac_block == lock_ac_block, f'AC block byte-identity FAILED: spec.yaml len={len(spec_ac_block)} lock.md len={len(lock_ac_block)}'
print('PROTECTED AC block byte-identity: PASS (both =', len(spec_ac_block), 'bytes)')
"
# Expected: PROTECTED AC block byte-identity: PASS (both = <N> bytes)

# 8. SHA-256 lock verification on spec.yaml
cd repo && shasum -a 256 spec/l13-004-channel-manager-minstay-2-way-sync/spec.yaml
# Expected: 1be892763360db881db470a9599f07c093db1c3418efafee3deba1dc46ed762d
```

## CF-1..CF-4 carry-forwards (per iter-14 coverage handoff)

These are EXTERNAL blockers, NOT spec gaps. They are tracked here for the
next-iteration Developer handoff:

| CF | Description | Status | Blocker | Unblock action |
|----|-------------|--------|---------|----------------|
| CF1 | Booking.com Connectivity Partner program onboarding | BLOCKED | External (~1-2 wk approval) | Apply via https://connect.booking.com/ |
| CF2 | HRS Channel Manager agreement via Beds24/SmartHOTEL reseller | BLOCKED | External (~1-2 wk contract) | Reach out to Beds24 or SmartHOTEL |
| CF3 | HRS-specific XML element names for production push | DEFERRED | CF2 prerequisite | Cannot test real HRS XML without CF2 partner credentials |
| CF4 | Direct call to Kurverwaltung Bad Orb (+49 6052 83-0) for 2027 peak-week calendar | DEFERRED | Operational (next iter) | Reach out to Kurverwaltung Bad Orb |

CF1+CF2 gate the production push path (real network IO). The dry-run path
(AC-6 + AC-7) is the GREEN-gate for this cycle — no partner credentials
required.