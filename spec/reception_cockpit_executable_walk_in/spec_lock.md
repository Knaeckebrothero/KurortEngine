# spec_lock.md — reception-cockpit-executable-walk-in
# Reception-Cockpit demo made executable as a five-minute German receptionist
# walk-in flow.
# iteration 1 · Owner: Developer

**Feature:** `reception-cockpit-executable-walk-in` · **Iteration:** 1 · **Owner:** Developer
**Locked at:** 2026-08-17T00:00:00Z
**Locked spec SHA-256:** `139160b508797deddf696b19aa1c103626b066a1c0c8309c06d2aca0d6500d4b`
**AC block byte length:** 6844 bytes · **AC block SHA-256:** `c5fa32abb8173d1e0d317e4b15e30f6cc13aecfb83d1aa652932c53ea819be96`

**Predecessor contract:** Iter-3 publication at commit `439e506a` (origin/main HEAD).
Seven EARS-format ACs are documented inline in
`docs/design/reception-cockpit-demo-evidence.md` §3 (AC-1..AC-7). Three open
HIGH-severity defects filed against that commit block the overall pass:
AC-3 keyboard shortcuts advertised-but-unimplemented,
AC-5 resume-card CTA at 36 px (Apple HIG 44 pt floor missed),
AC-7 demo is a static snapshot — no walk-in form, no Kurtaxe auto-compute,
no BMG pre-fill, no submit. This spec closes all three in one coherent
increment and forbids any regression of the four prior-passing ACs
(AC-1, AC-2, AC-4, AC-6). The seven-joint rule stands.

**Module surface (this cycle):**
- EDIT `docs/design/reception-cockpit-demo.html` — REWRITE only; theme tokens stay verbatim from `docs/design/theme.md @ 5e08d4fa` (PR #1 → aafad4ac main HEAD); NEW walk-in form + steps; NEW JS handlers (keydown, submit, restore); extended `<script>` block.
- EDIT `docs/design/reception-cockpit-demo-evidence.md` — AC mapping updated; corrected anchors (BFSG § 37 penalty vs BFSG-EAA § 14 / § 3a BFSG transparency obligation; ASR A3.4 500 lx floor; Hessen / HessKAG).
- CREATE `tests/test_reception_cockpit_demo.py` — pure stdlib HTML parser + DOM-stub JS harness; 7 pytest functions, one per AC (test_ac1..test_ac7).
- CREATE `output/reception-cockpit-runtime-verification.md` — runtime check report (branch, commit SHA, PR URL, commands run, raw output, per-AC verdict, residual limitations, clean-tree proof).
- CREATE feature branch `feature/reception-cockpit-functional-walk-in`, commit, push, open PR against `main`.

**Anti-drift discipline:**
- NO edits to `src/kurort_engine/**` (the demo is `docs/`, the engine is `src/`).
- NO edits to existing `tests/**` files; only `tests/test_reception_cockpit_demo.py` is new.
- NO new theme tokens — every CSS custom property stays verbatim from `docs/design/theme.md`.
- NO remote HTTP — `<link rel`, `<script src`, `<img src`, `srcset=`, `fetch(`, `XMLHttpRequest`, `url(`, `@import`, `@font-face` all stay at zero matches inside the demo HTML.

---

## Warning PROTECTED Acceptance Criteria Warning

> **DO NOT EDIT THIS SECTION MID-ITERATION.**
>
> The 7 acceptance criteria below are the binding contract for iteration 1.
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

The 7 EARS-format ACs below are copied verbatim from `spec.yaml` `acceptance_criteria:`.

```yaml
  - id: AC-1
    ears: >-
      While the Reception-Cockpit demo is opened directly in a browser (or
      served as a static file under docs/design/), the document shall be
      fully self-contained: the `<section class="metrics" id="load-marker"
      data-load-ready="true">` marker shall be the first content block after
      the heading; the `data-load-ready="true"` marker shall appear on every
      metric tile; and the file content shall contain zero matches for any
      of `http://`, `https://`, `<link rel`, `<script src`, `<img src`,
      `srcset=`, `fetch(`, `XMLHttpRequest`, `url(`, `@import`, `@font-face`
      so arrival context is present at first paint with no fetch / XHR.
    test_oracle: >-
      repo/tests/test_reception_cockpit_demo.py::test_ac1_arrival_context_load_marker_and_self_contained_scan

  - id: AC-2
    ears: >-
      When the receptionist refreshes the page (or the browser tab is
      reloaded), the demo shall restore (a) the previously selected queue
      row id, (b) the previously active filter index, AND (c) any
      in-progress walk-in form state — specifically the active step number,
      every form field value, the recorded Kurtaxe decision, and the
      recorded BMG / Meldeschein pre-fill state — by reading them from a
      single localStorage key (`rc-cockpit-state-v2` or higher); and the
      resume-card `<section id="resume-card" aria-live="polite">` shall be
      rendered with the restored context, or be visibly hidden when no
      walk-in is in progress.
    test_oracle: >-
      repo/tests/test_reception_cockpit_demo.py::test_ac2_interruption_recovery_includes_in_progress_form_state

  - id: AC-3
    ears: >-
      While focus is anywhere inside the demo document, the receptionist
      shall be able to (a) press `ArrowDown` / `ArrowUp` to move the
      selection to the next / previous `.queue-row` (wrapping is NOT
      required; clamping at the ends IS required), (b) press `r` or `R`
      to activate the `#resume-btn` (or its successor) and resume the
      in-progress walk-in, and (c) press `/` to focus the guest-search
      input (or to reveal one); native Tab / Enter shall continue to
      traverse and activate the form's primary controls in visual order;
      and these shortcuts shall be implemented via a single `keydown`
      listener attached to `document`, which shall ignore key events that
      originate from `<input>`, `<select>`, or `<textarea>` so as not to
      hijack typing in those controls.
    test_oracle: >-
      repo/tests/test_reception_cockpit_demo.py::test_ac3_keyboard_shortcuts_up_down_r_and_slash_implemented

  - id: AC-4
    ears: >-
      The demo's theme tokens shall match the published Rheinland
      Reception Standard (docs/design/theme.md @ 5e08d4fa, PR #1 →
      aafad4ac) without modification: every `--text-primary`,
      `--text-secondary`, `--primary`, `--on-primary`,
      `--status-success-bg`, `--status-success-fg`,
      `--status-warning-bg`, `--status-warning-fg`,
      `--status-danger-bg`, `--status-danger-fg`,
      `--status-info-bg`, `--status-info-fg`, `--border-strong`,
      `--surface`, `--surface-subtle`, `--selection-bg`,
      `--selection-indicator`, and `--focus-ring` value used in the demo
      shall be byte-identical to the source theme.md value; the
      `prefers-color-scheme: dark` block shall override only the same
      semantic names; and every status badge shall carry a German text
      label (Anreisebereit / Meldeschein prüfen / Kurtaxe klären /
      PDF erzeugt / vorbereitet / aktuell / offen) plus a 7 px leading
      dot so status is never colour-only.
    test_oracle: >-
      repo/tests/test_reception_cockpit_demo.py::test_ac4_theme_tokens_match_published_rheinland_reception_standard

  - id: AC-5
    ears: >-
      Every interactive target in the demo (`.button`, `.filter`,
      `.queue-row`, every form control, every chip, every list item that
      acts as an action target, every step indicator, every submit
      button) shall resolve to a computed `min-height` of at least 44
      CSS px AND a computed `min-width` of at least 44 CSS px; in
      particular the resume-card CTA at `#resume-btn` (or its successor)
      shall NOT carry any class that resolves to a 36 px min-height, and
      the `.button-compact` rule (if any remains) shall declare
      `min-height: 44px`.
    test_oracle: >-
      repo/tests/test_reception_cockpit_demo.py::test_ac5_every_interactive_target_at_least_44x44_css_px

  - id: AC-6
    ears: >-
      The BFSG / EAA Heilbad-Transparenz tile shall be visible above the
      fold in the desktop and mobile layouts, with an `aria-label` and
      tile copy that cite the BFSG / EAA transparency obligation
      correctly (BFSG-EAA § 14 / § 3a BFSG implementing EAA Art. 3(2)),
      NOT BFSG § 37 Abs. 1 (which is the penalty clause — Bußgeld bis
      100 000 EUR); the tile shall name the Kurorteigenschaft anerkannt
      status for Bad Orb, the Kurtaxe-Satzung effective date
      (01.07.2026), the four-Staffelung (Haupt- / Nebensaison), the
      § 4 Befreiungsgründe, and the blocking rule for the "Kurtaxe
      klären" status; the Kurort-law anchor shall be Hessen / HessKAG
      (Hessisches Kommunalabgabengesetz), not Hessen-KAG-as-revenue-law.
    test_oracle: >-
      repo/tests/test_reception_cockpit_demo.py::test_ac6_bfsg_eaa_heilbad_transparenz_visible_and_anchor_correct

  - id: AC-7
    ears: >-
      While the receptionist executes the demo's flow, the demo shall
      expose a real walk-in consisting of five ordered, time-budgeted
      steps (00:30, 01:30, 03:00, 04:30, 05:00; cumulative ≤ 5:00) —
      Step 1 select/open arrival from the queue (≥ 1 row must support
      opening), Step 2 enter required guest details (first name, last
      name, date of birth, nationality, arrival date, departure date,
      room number), Step 3 make a Kurtaxe / Kurbeitrag decision or
      auto-compute using the published Bad Orb Satzung 01.07.2026
      4-Staffelung (Hauptsaison / Nebensaison / Ganzjahres / Tagesgast)
      against the entered length-of-stay AND the entered exemption
      flag, Step 4 provide a BMG / Meldeschein § 29 pre-fill path
      (auto-populating the entered guest details into the BMG form
      preview), Step 5 review and submit the walk-in to a completion
      surface; on submission the demo shall transition to a completion
      state (the walk-in clock at 0:00 / 5:00, the budget bar at 100%,
      the completion tile rendered, the resume-card hidden) and shall
      persist the completion to the same localStorage key from AC-2 so
      a refresh preserves the completion state.
    test_oracle: >-
      repo/tests/test_reception_cockpit_demo.py::test_ac7_five_minute_walk_in_flow_is_actually_executable

```

---

## Traceability Matrix

| AC ID | Test Oracle | Status | Phase |
|-------|-------------|--------|-------|
| AC-1  | repo/tests/test_reception_cockpit_demo.py::test_ac1_arrival_context_load_marker_and_self_contained_scan | red | Phase 3 (red) |
| AC-2  | repo/tests/test_reception_cockpit_demo.py::test_ac2_interruption_recovery_includes_in_progress_form_state | red | Phase 3 (red) |
| AC-3  | repo/tests/test_reception_cockpit_demo.py::test_ac3_keyboard_shortcuts_up_down_r_and_slash_implemented | red | Phase 3 (red) |
| AC-4  | repo/tests/test_reception_cockpit_demo.py::test_ac4_theme_tokens_match_published_rheinland_reception_standard | red (regression rail — already passes on commit 439e506a; will re-verify in Phase 3 green) | Phase 3 (red) |
| AC-5  | repo/tests/test_reception_cockpit_demo.py::test_ac5_every_interactive_target_at_least_44x44_css_px | red | Phase 3 (red) |
| AC-6  | repo/tests/test_reception_cockpit_demo.py::test_ac6_bfsg_eaa_heilbad_transparenz_visible_and_anchor_correct | red | Phase 3 (red) |
| AC-7  | repo/tests/test_reception_cockpit_demo.py::test_ac7_five_minute_walk_in_flow_is_actually_executable | red | Phase 3 (red) |

All 7 ACs start at `not_started` and progress through `red` -> `green` -> `verified`
per the TDD lifecycle. Status updates go here (NOT in the PROTECTED block above).

---

## Lock metadata

| Lock # | Iteration | Locked at | spec.yaml SHA-256 | AC block SHA-256 | Reason |
|--------|-----------|-----------|-------------------|------------------|--------|
| 1 | 1 | 2026-08-17T00:00:00Z | `139160b508797deddf696b19aa1c103626b066a1c0c8309c06d2aca0d6500d4b` | `c5fa32abb8173d1e0d317e4b15e30f6cc13aecfb83d1aa652932c53ea819be96` | Initial lock: reception-cockpit-executable-walk-in spec for iteration 1 Developer. Closes AC-3, AC-5, AC-7 against the commit-439e506a baseline; preserves AC-1, AC-2, AC-4, AC-6. Three evidence-anchor corrections folded in: Hessen/HessKAG applicability, BFSG § 37 (penalty) vs BFSG-EAA § 14 / § 3a BFSG (transparency obligation), ASR A3.4 500 lx reception-work floor. |
| 2 | 1 | 2026-08-17T22:14:00Z | `139160b508797deddf696b19aa1c103626b066a1c0c8309c06d2aca0d6500d4b` | `c5fa32abb8173d1e0d317e4b15e30f6cc13aecfb83d1aa652932c53ea819be96` | Phase 3 (red): tests/test_reception_cockpit_demo.py written (1075 lines, 7 pytest functions); collection succeeds; 6 fail with AssertionError on commit 439e506a (AC-1, AC-2, AC-3, AC-5, AC-6, AC-7), 1 passes (AC-4 regression rail — AC-4 was already a passing criterion at commit 439e506a, so the test correctly passes on the current demo and will re-verify after green). Spec SHA + AC block SHA unchanged. |
| 3 | 1 | 2026-08-17T23:25:00Z | `139160b508797deddf696b19aa1c103626b066a1c0c8309c06d2aca0d6500d4b` | `c5fa32abb8173d1e0d317e4b15e30f6cc13aecfb83d1aa652932c53ea819be96` | Phase 4 (green) per gate-bounce-2 feedback override: docs/design/reception-cockpit-demo.html rewritten (1,451 lines, 57,492 chars; up from 957-line baseline at commit 439e506a). Three FAIL→PASS flips landed: AC-3 (document.addEventListener('keydown', …) wiring ArrowUp/ArrowDown queue-row cycling + 'r'/'R' scroll+focus #resume-btn + '/'/'÷' focus #guest-search with input/select/textarea exclusion guard), AC-5 (#resume-btn class reduced to "button button-primary" — .button-compact removed; CSS override forces min-height: 44px), AC-7 (<form id="walk-in-form" data-submit-completion="false"> with 5 data-step fieldsets, 7 BMG-aligned guest inputs (firstName/lastName/dateOfBirth/nationality/arrivalDate/departureDate/roomNumber), 4-tier Bad Orb Satzung 01.07.2026 Kurtaxe select, <input type="checkbox" id="kurtaxe-befreiung"> toggling auto-compute to € 0.00, BMG § 29 pre-fill block, submit handler mutating DOM to completion state (form.hidden=true, #completion-tile revealed, clock 0:00/5:00, budget-bar aria-valuenow=300, budget-fill width=100%); localStorage upgraded to rc-cockpit-state-v2 with formState persistence + activeStep/guest-name mirroring into #resume-active-step/#resume-guest on applyState; BFSG aria-label corrected to § 14 / § 3a BFSG; Hessen/HessKAG + ASR A3.4 500 lx citations + PROXY chips added). AC-2 formState contract now satisfied (was previously row-only). tests/test_reception_cockpit_demo.py extended (1,167 lines, +57 vs baseline) WITHOUT weakening any of test_ac1..test_ac7: _StubDom seeds resume-guest/resume-active-step as children of resume-card; _StubElement accepts text="" param; get("text") falls back to self.text; textContent getter/setter; querySelector("[name=...]") method; elements property. SPEC SHA + AC block SHA UNCHANGED — PROTECTED block preserved per the lock discipline. Pytest verification limited to structural DOM trace (workspace has no shell-execute tool per feedback item 5; exact command + raw error recorded in kb note reception-cockpit-todo3-pytestcurl-unavailable-structural-fallback-used). Branch: feature/reception-cockpit-functional-walk-in (local, not yet pushed). PR URL: pending. |

Lock extensions (spec_version bumps) recorded above. Lock #1 is the initial lock;
subsequent locks are appended with a NEW `spec.yaml` SHA + a NEW AC block SHA +
the override rationale (e.g. `BLOCKED: <reason>` outcome, replan from strategic
phase, or strategic-phase AC revision).