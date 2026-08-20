# spec_lock.md — reception-cockpit-e2e-coverage-follow-up
# Reception-Cockpit Playwright/Chromium coverage extension — companion
# spec for the published PR #4 deliverables. This job EXTENDS the PR #4
# test suite with 6 new test functions; it does NOT mutate the PR #4
# spec lock, demo HTML, or sibling test files.
# iteration 1 · Owner: Developer

**Feature:** `reception-cockpit-e2e-coverage-follow-up` · **Iteration:** 1 · **Owner:** Developer
**Locked at:** 2026-08-20T22:00:00Z
**Locked spec SHA-256:** `2325c7d3fd1d661dfb73d4c7fcad99c651418bee62c715c31fb5b11c1420410c`
**AC block byte length:** 4732 bytes
**AC block SHA-256:** `96e65c62a32dfdc5d412efe1bc43926a839b81279b0b172138681dd87bc1cd3f`

**Predecessor contract:** PR #4 candidate at head `bea4c6d148f7dd4ad7b9fd0016c75476030beaa7`
on branch `fix/pr2-reception-cockpit-harness-and-browser-proof`. PR #4 spec.yaml
SHA-256 `139160b508797deddf696b19aa1c103626b066a1c0c8309c06d2aca0d6500d4b`. PR #4
AC block SHA-256 `c5fa32abb8173d1e0d317e4b15e30f6cc13aecfb83d1aa652932c53ea819be96`.
PR #4 ships 9 Playwright/Chromium tests in `tests/test_reception_cockpit_browser.py`.
This extension adds 6 new test functions (AC-E1..AC-E6) covering the gaps called
out in instructions.md: 5-step walk-in E2E, every Kurtaxe Staffelung boundary
+ adjacent values, keyboard-only completion, completion-tile final state and
content, mid-flow persistence across reload, completed-flow persistence across
reload.

**Module surface (this cycle):**
- EXTEND `tests/test_reception_cockpit_browser.py` with 6 new test functions covering AC-E1..AC-E6.
  Reuse the existing `demo_server` + `browser` + `page` fixtures (no rewrites).
- CREATE `output/reception-cockpit-e2e-coverage-report.md` — the job-root
  contract deliverable (per task_brief.md).
- CREATE feature branch `feat/pr4-reception-cockpit-e2e-coverage-follow-up`, commit,
  push, open PR against `main`.

**Anti-drift discipline:**
- NO edits to `src/kurort_engine/**` (the engine is src/, the demo is docs/).
- NO edits to `docs/design/reception-cockpit-demo.html` (PR #4 immutable).
- NO edits to `spec/reception_cockpit_executable_walk_in/spec.yaml` or
  `spec_lock.md` (PR #4 spec lock preserved).
- NO edits to `tests/test_reception_cockpit_demo.py` or
  `tests/test_reception_cockpit_harness_fidelity.py` (sibling suites).
- NO edits to existing test functions in `tests/test_reception_cockpit_browser.py`
  (existing 9 tests stay byte-identical).
- NO `pytest.skip` / `@pytest.mark.skip` / `@pytest.mark.xfail` / `assert True`
  / empty body / mock-the-unit-under-test. Failing tests are preserved as
  issue notes via `kb_write type=issue` — never weakened, deleted, or skipped.

---

## Warning PROTECTED Acceptance Criteria Warning

> **DO NOT EDIT THIS SECTION MID-ITERATION.**
>
> The 6 acceptance criteria below are the binding contract for iteration 1.
> They are copied verbatim from `spec.yaml` and hashed at lock time. If a
> criterion turns out to be wrong, contradictory, or impossible, the correct
> response is to emit `BLOCKED: <reason>` or `ABORT: <reason>` and surface it
> to the strategic phase — NOT to weaken the AC.
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

The 6 EARS-format ACs below are copied verbatim from `spec.yaml` `acceptance_criteria:`.

```yaml
acceptance_criteria:
- id: AC-E1
  ears: When a real or role-played receptionist drives the demo through all five walk-in steps (step 1 select/open arrival, step 2 enter required guest details, step 3 make Kurtaxe/Kurbeitrag decision or auto-compute, step 4 BMG/Meldeschein §29 pre-fill, step 5 review and submit) AND submits the form, the demo shall transition to a completion state in which the completion tile `#completion-tile` is revealed (hidden=false), the walk-in clock `#walk-in-clock-final` reads 00:00 / 05:00, AND the completion tile's body carries the entered guest's full name, the entered arrival date and departure date, the computed Kurbeitrag total formatted as EUR with two decimals (e.g. "14,00 €"), AND a completion timestamp (a `<time>` element with a `datetime` attribute or a `data-completed-at` attribute on the completion tile).
  test_oracle: tests/test_reception_cockpit_browser.py::test_e2e_full_five_step_walk_in_reaches_completion
- id: AC-E2
  ears: While the receptionist has entered values into one or more step 2 (Gastdaten) fields and the demo registers an activeStep value greater than 1 in localStorage `rc-cockpit-state-v2`, then on a full page reload (or browser refresh), the demo shall restore the same step 2 field values into their respective inputs, the displayed active step shall equal the saved activeStep (the `#resume-active-step` element shall carry "Schritt N von 5" with N equal to the saved value), AND the entered guest name shall be mirrored into the `#resume-guest` element.
  test_oracle: tests/test_reception_cockpit_browser.py::test_mid_flow_persistence_repopulates_after_reload
- id: AC-E3
  ears: When the walk-in has been submitted to completion (AC-E1 has fired), the demo shall persist the completion state to the same localStorage key `rc-cockpit-state-v2`, AND on a full page reload the completion tile `#completion-tile` shall be revealed (hidden=false) and the walk-in form `#walk-in-form` shall remain hidden (hidden=true), AND the completion timestamp displayed on the completion tile shall be stable (equal to the timestamp recorded at the moment of first completion — a reload must NOT reset the completion timestamp to the current page load time).
  test_oracle: tests/test_reception_cockpit_browser.py::test_completed_flow_persistence_keeps_completion_tile_after_reload
- id: AC-E4
  ears: For every implemented Staffelung tier in the demo (`hauptsaison-erwachsene` = 3,50 € / Nacht, `nebensaison-erwachsene` = 2,80 € / Nacht, `ganzjahres-kind` = 1,20 € / Nacht, `tagesgast` = 1,80 € Pauschale) AND for adjacent boundary values (1 Nacht vs 2 Nächte vs 30 Nächte; Kind age 6 vs 15 vs 16 entered via the dateOfBirth field; Tagesgast with 0 Übernachtungen), the demo's auto-computed Kurtaxe total displayed in `#kurtaxe-auto-compute` shall equal (a) tier_rate × nights for per-night tiers, OR (b) the Pauschale flat 1,80 € for Tagesgast, AND the total shall be formatted as EUR with two decimals (e.g. "14,00 €") AND the visible breakdown text shall contain the rate label and the per-night line item (e.g. "4 × 3,50 € = 14,00 €").
  test_oracle: tests/test_reception_cockpit_browser.py::test_staffelung_boundary_table
- id: AC-E5
  ears: While a keyboard-only user (no pointer input) drives the demo, the receptionist shall be able to (a) Tab through every interactive element of the 5-step walk-in form in DOM order, (b) observe a visible focus ring on every focused element (WCAG 2.2 SC 2.4.7 Focus Visible), (c) activate any form control's primary action with Enter or Space, (d) advance from step 1 through step 5 using keyboard only, AND (e) reach the completion tile `#completion-tile` revealed without ever using the pointer.
  test_oracle: tests/test_reception_cockpit_browser.py::test_keyboard_only_walk_in
- id: AC-E6
  ears: 'The completion tile''s final state in the post-submit DOM shall contain: (i) a semantic marker identifying completion (a `<section>` or `<article>` with id `completion-tile` and an aria-label including the word "abgeschlossen" or an equivalent German completion phrase); (ii) the guest''s full name as entered in step 2 (concatenated first name + last name, with the literal value entered in the BMG inputs); (iii) the computed Kurbeitrag total formatted as EUR with two decimals (e.g. "14,00 €"); (iv) a date+time stamp of completion (an ISO 8601 datetime on a `<time>` element, or a `data-completed-at` attribute on the completion tile); AND (v) at minimum a "Neuer Walk-in" or equivalent reset affordance (a button or link that clears the completed state and re-shows the empty walk-in form).'
  test_oracle: tests/test_reception_cockpit_browser.py::test_completion_tile_final_state_content

```

---

## Traceability Matrix

| AC ID | Test Oracle | Status | Phase |
|-------|-------------|--------|-------|
| AC-E1  | tests/test_reception_cockpit_browser.py::test_e2e_full_five_step_walk_in_reaches_completion | not_started | Phase 2 (red) |
| AC-E2  | tests/test_reception_cockpit_browser.py::test_mid_flow_persistence_repopulates_after_reload | not_started | Phase 2 (red) |
| AC-E3  | tests/test_reception_cockpit_browser.py::test_completed_flow_persistence_keeps_completion_tile_after_reload | not_started | Phase 2 (red) |
| AC-E4  | tests/test_reception_cockpit_browser.py::test_staffelung_boundary_table | not_started | Phase 2 (red) |
| AC-E5  | tests/test_reception_cockpit_browser.py::test_keyboard_only_walk_in | not_started | Phase 2 (red) |
| AC-E6  | tests/test_reception_cockpit_browser.py::test_completion_tile_final_state_content | not_started | Phase 2 (red) |

All 6 ACs start at `not_started` and progress through `red` -> `verified`
per the TDD lifecycle. Status updates go here (NOT in the PROTECTED block above).

---

## Lock metadata

| Lock # | Iteration | Locked at | spec.yaml SHA-256 | AC block SHA-256 | Reason |
|--------|-----------|-----------|-------------------|------------------|--------|
| 1 | 1 | 2026-08-20T22:00:00Z | `2325c7d3fd1d661dfb73d4c7fcad99c651418bee62c715c31fb5b11c1420410c` | `96e65c62a32dfdc5d412efe1bc43926a839b81279b0b172138681dd87bc1cd3f` | Initial lock: companion spec for the PR #4 E2E coverage extension. 6 EARS ACs covering 5-step walk-in E2E, mid-flow + completed-flow persistence, every Kurtaxe Staffelung boundary + adjacent values, keyboard-only walk-in, completion-tile final state and content. PR #4 spec lock preserved verbatim. |

Lock extensions (spec_version bumps) recorded above. Lock #1 is the initial lock;
subsequent locks are appended with a NEW `spec.yaml` SHA + a NEW AC block SHA +
the override rationale (e.g. `BLOCKED: <reason>` outcome, replan from strategic
phase, or strategic-phase AC revision).

---

## Companion verification tool

The companion `verify_protected_block.py` (mirrors `spec/avv_kaskade/verify_protected_block.py`)
will be added at phase-2 (red) exit to enforce the AC block byte-locking. Failure
modes it must catch:

- AC block in `spec_lock.md` byte-drifts from `spec.yaml` `acceptance_criteria:` section.
- AC block byte length changes without a `Lock metadata` entry.
- `spec.yaml` SHA-256 changes without a `Lock metadata` entry.
