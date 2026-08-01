# spec_lock.md — bfsg-eaa-guest-pwa-accessibility
# Kurort-vertical BFSG-EAA / EN 301 549 V3.2.1 / WCAG 2.1 AA self-attestation
# tenant for the Hotel Rheinland Bad Orb guest PWA booking flow.
# iteration 3 · Owner: Developer

**Feature:** `bfsg-eaa-guest-pwa-accessibility` · **Iteration:** 3 · **Owner:** Developer
**Locked at:** 2026-07-10T00:00:00Z
**Locked spec SHA-256:** `9306bbf41aaa44a3cf344856fe097444e2c791911adf2102e063499289671ff9`
**AC block byte length:** 4708 bytes · **AC block SHA-256:** `dfb08058f0e5bf4b2812b38d5b0a90e573cb8d9138f5233c9d3eac338a57e4db`

**Predecessor verdict (the binding contract):** iter-2 Critic verdict (job ab05a8f7)
APPROVED A1 `bfsg-eaa-guest-pwa-accessibility` (composite 21/21, NO risk-flag,
Tier-1 PICK-FIRST) as iter-3 Developer action. 5 verification commands ship in
the verdict §4 (VC-1..VC-5); 7-point Developer brief ships in the Critic handoff
§3 (Action 1..Action 7). Mix B SAFE (NO Lawyer dependency). Pattern F
chain-extension on 4 SHIPPED modules (audit + kurkarte_wallet + meldeschein + f5_t2
dispatcher).

5 EARS-format ACs implement the BFSG-EAA self-attestation tenant. Module surface:
CREATE `a11y/__init__.py` + `a11y/guest_pwa/<6 modules>.py` (8 NEW files, ~250 src LOC)
+ EDIT `pyproject.toml` (1 ADDITIVE line for `[project.scripts]`) + EDIT
`kurort_engine/__init__.py` (ADDITIVE only — new a11y re-exports appended) + EDIT
`README.md` (~15 APPEND lines) + CREATE `tests/test_a11y_guest_pwa.py` (5 tests, ~120 LOC).
~390 total LOC = 95% of the <=410 envelope. Anti-drift discipline: 6 SHAs + 4 iter-33
predicate_filing SHAs + 12 SHIPPED modules' public APIs + `kurort_engine/__init__.py`
existing 9+13+8+12+5+8+4+3+3 = 65-symbol re-export list all preserved byte-identical at
iter-3 close. `git diff HEAD~1 --stat` MUST NOT show changes to any of the 22 protected
files; ONLY `a11y/__init__.py` (NEW) + `a11y/guest_pwa/*` (NEW) + `kurort_engine/__init__.py`
(ADDITIVE) + `pyproject.toml` (1 ADD line) + `README.md` (APPEND) + `tests/test_a11y_guest_pwa.py`
(NEW) modified.

---

## Warning PROTECTED Acceptance Criteria Warning

> **DO NOT EDIT THIS SECTION MID-ITERATION.**
>
> The 5 acceptance criteria below are the binding contract for iteration 3.
> They are copied verbatim from `spec.yaml` and hashed at lock time. If a
> criterion turns out to be wrong, contradictory, or impossible, the correct
> response is to emit `BLOCKED: <reason>` or `ABORT: <reason>` and surface it
> to the strategic phase -- NOT to weaken the AC.
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

The 5 EARS-format ACs below are copied verbatim from `spec.yaml` `acceptance_criteria:`.

```yaml
acceptance_criteria:
  - id: AC-1
    ears: >-
      When `import kurort_engine.a11y.guest_pwa` is executed for the first
      time in a Python interpreter session, the system shall append exactly
      one `AuditEntry` to the SHIPPED `kurort_engine.audit.AuditLog` whose
      `actor` equals the string `"a11y.guest_pwa"`, whose canonical-JSON
      `payload` decodes to `{"event": "self_attestation", "ts": "<SELF_ATTESTATION_TS>",
      "claim": "..."}` for a non-empty claim string referencing BFSG-EAA §3(1)
      and EN 301 549 V3.2.1 / WCAG 2.1 AA, and whose `content_hash` is the
      SHA-256 hex of the canonical-JSON (sort_keys=True, separators=(",", ":"))
      of `recorded_at` / `actor` / `payload`; and a module-level constant
      `SELF_ATTESTATION_TS` shall be exported as a non-empty ISO-8601 date
      string (YYYY-MM-DD).
    test_oracle: >-
      repo/tests/test_a11y_guest_pwa.py::test_ac1_self_attestation_ts_constant_and_audit_log_event

  - id: AC-2
    ears: >-
      The system shall expose a public function `run_wcag_aa_audit(html_or_url)` in
      `kurort_engine.a11y.guest_pwa` that (a) attempts to invoke the axe-core CLI
      via `subprocess.run(["npx", "@axe-core/cli", <target>], capture_output=True,
      text=True, timeout=120)` if `shutil.which("npx")` returns a non-None path,
      (b) on `FileNotFoundError` or `shutil.which("npx") is None` falls back to a
      manual-audit branch that returns a `dict` with keys `{"method": "manual",
      "wcag_level": "AA", "en_standard": "EN 301 549 V3.2.1", "violations": [],
      "scope": "kurort_engine.a11y.guest_pwa"}` and appends one
      `AuditEntry` with `actor="a11y.guest_pwa"` and `payload` containing
      `"event": "wcag_aa_audit"` to the SHIPPED AuditLog, and (c) on any other
      unhandled exception raises `BFSGComplianceError` with a message that
      includes the substring `"axe-core subprocess failed"` and the captured
      stderr.
    test_oracle: >-
      repo/tests/test_a11y_guest_pwa.py::test_ac2_wcag_aa_audit_infra_with_manual_fallback

  - id: AC-3
    ears: >-
      While a Python 3.11+ interpreter is active, `python -m kurort_engine.a11y.guest_pwa`
      (PEP 338 entry point) shall print the string `"kurort_engine.a11y.guest_pwa
      <SELF_ATTESTATION_TS> (WCAG 2.1 AA, EN 301 549 V3.2.1, BFSG-EAA §3(1)
      self-attestation tenant)"` to stdout, append exactly one new
      `AuditEntry` with `actor="a11y.guest_pwa.cli"` and `payload` containing
      `"event": "cli_invocation"` to the SHIPPED AuditLog, and exit 0; and
      `repo/pyproject.toml [project.scripts]` shall contain the line
      `guest-pwa = "kurort_engine.a11y.guest_pwa.__main__:main"` so
      `pip install -e .[dev]` followed by `guest-pwa --version` (or `--help`)
      yields the same usage text as `python -m kurort_engine.a11y.guest_pwa
      --help`; and `grep -rnE "(webpack|vite|react|svelte)" repo/src/kurort_engine/a11y/`
      shall return zero matches.
    test_oracle: >-
      repo/tests/test_a11y_guest_pwa.py::test_ac3_cli_subcommand_via_pyproject_entry_points

  - id: AC-4
    ears: >-
      The module `kurort_engine.a11y.guest_pwa` shall Pattern F chain-extend
      4 SHIPPED modules by exposing a module-level constant
      `CHAIN_EXTENSION_ANCHORS` whose value is a `tuple` of length 4 containing
      the strings `"kurort_engine.audit.AuditLog"`,
      `"kurort_engine.kurkarte_wallet"`,
      `"kurort_engine.meldeschein"`, and `"kurort_engine.f5_t2"`; and
      `kurort_engine.a11y.guest_pwa.__init__` shall contain exactly 4
      `from kurort_engine.X import Y` (or equivalent top-level `import`) lines
      whose X names match the 4 anchors in CHAIN_EXTENSION_ANCHORS; and NO
      source line in `kurort_engine.a11y/guest_pwa/` shall verbatim copy any
      line of source from any of the 4 anchor modules (anti-drift discipline).
    test_oracle: >-
      repo/tests/test_a11y_guest_pwa.py::test_ac4_pattern_f_chain_extension_on_4_shipped_modules

  - id: AC-5
    ears: >-
      The module `kurort_engine.a11y.guest_pwa` shall expose a module-level
      constant `RESAVIO_BFSG_AA_PARITY_2026_Q4` whose value is the literal
      Python `False`, AND a sibling string constant
      `RESAVIO_BFSG_AA_PARITY_RATIONALE` whose value is a non-empty string
      citing Resavio 2026-Q4 lack of full BFSG-AA parity per the
      `iter-19-evidence-anchor-resavio-2026-q42027-q1-sanity-re-check-no-change-since-i`
      KB learning note (which preserves the iter-27 sanity-check finding
      that Resavio does NOT ship full BFSG-AA Barrierefreiheitserklärung).
    test_oracle: >-
      repo/tests/test_a11y_guest_pwa.py::test_ac5_resavio_2026_q4_bfsg_aa_parity_negative_test

```

---

## Traceability Matrix

| AC ID | Test Oracle | Status | Phase |
|-------|-------------|--------|-------|
| AC-1  | repo/tests/test_a11y_guest_pwa.py::test_ac1_self_attestation_ts_constant_and_audit_log_event | green | Phase 7b |
| AC-2  | repo/tests/test_a11y_guest_pwa.py::test_ac2_wcag_aa_audit_infra_with_manual_fallback | green | Phase 7b |
| AC-3  | repo/tests/test_a11y_guest_pwa.py::test_ac3_cli_subcommand_via_pyproject_entry_points | green | Phase 7b |
| AC-4  | repo/tests/test_a11y_guest_pwa.py::test_ac4_pattern_f_chain_extension_on_4_shipped_modules | green | Phase 7b |
| AC-5  | repo/tests/test_a11y_guest_pwa.py::test_ac5_resavio_2026_q4_bfsg_aa_parity_negative_test | green | Phase 7b |

All 5 ACs start at `not_started` and progress through `red` -> `green` -> `verified`
per the TDD lifecycle. Status updates go here (NOT in the PROTECTED block above).

---

## Lock metadata

| Lock # | Iteration | Locked at | spec.yaml SHA-256 | AC block SHA-256 | Reason |
|--------|-----------|-----------|-------------------|------------------|--------|
| 1 | 3 | 2026-07-10T00:00:00Z | `9306bbf41aaa44a3cf344856fe097444e2c791911adf2102e063499289671ff9` | `dfb08058f0e5bf4b2812b38d5b0a90e573cb8d9138f5233c9d3eac338a57e4db` | Initial lock: bfsg-eaa-guest-pwa-accessibility spec for iter-3 Developer. |
| 2 | 3 | 2026-07-10T00:00:00Z | `9306bbf41aaa44a3cf344856fe097444e2c791911adf2102e063499289671ff9` | `dfb08058f0e5bf4b2812b38d5b0a90e573cb8d9138f5233c9d3eac338a57e4db` | Phase 7b GREEN: AC traceability matrix updated red->green. AC block SHA unchanged (byte-identical). |

Lock extensions (spec_version bumps) recorded above. Lock #1 is the initial lock;
subsequent locks are appended with a NEW `spec.yaml` SHA + a NEW AC block SHA +
the override rationale (e.g. `BLOCKED: <reason>` outcome, replan from strategic
phase, or strategic-phase AC revision).
