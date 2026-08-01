# UI Idea 001 — Today Arrivals Artifact Strip

**One-line summary:** Add a narrow receptionist-facing arrival row/card that shows the generated Meldeschein PDF, Apple PKPass, Google Wallet JSON, and CLI proof for one reservation without re-proposing a broad reception command center, kiosk, guest portal, or wallet app.

**Target role / workflow:** Receptionist during same-day arrivals, with manager/Kurverwaltung visibility only as read-only status consumers.

**Evidence labels:** `CLI-backed`, `test-contract-backed`, `module-backed`, `preview-only`, `requires new API contract`.

## Research question for this artifact

How can the Hotel Rheinland / Kurort ERP UI expose the already-tested arrival-bundle and receptionist CLI outputs in a staff-facing screen while avoiding duplicate kiosk, command-center, and mobile-wallet proposals?

## Proposal

Create a **Today Arrivals Artifact Strip** as a component inside a receptionist arrivals list. Each reservation row shows one guest/reservation, the action that produced its artifacts, and the current proof state of each generated output:

| Strip zone | Proposed UI element | State model | Evidence label |
|---|---|---|---|
| Reservation identity | Reservation ID chip, guest name label, arrival/departure date if provided by a future API | `missing data`, `ready`, `generated` | `requires new API contract` for any web/API data feed |
| Meldeschein artifact | PDF pill: `not generated`, `generated`, `download`, `rerun` | `not run`, `generated`, `failed`, `rerun needed` | `CLI-backed`, `test-contract-backed` |
| Kurkarte Apple pass | `.pkpass` pill with filename/proof link | `not run`, `generated`, `download`, `unsupported delivery` | `test-contract-backed`, `preview-only` |
| Google Wallet object | `.json` pill with payload-preview button | `not run`, `generated`, `download`, `unsupported delivery` | `test-contract-backed`, `preview-only` |
| CLI proof drawer | Collapsible details: command label, reservation ID, return code, stdout/stderr summary, output directory, file list | `success`, `failure`, `partial`, `unverified` | `CLI-backed` |
| Unsupported claims guard | Inline badges: `No guest portal`, `No device delivery proof`, `No web API yet` | Always visible in design handoff, hidden from final user only after product contracts exist | `requires new API contract` |

The artifact strip should be deliberately smaller than a “reception command center.” It is a single row/card pattern for one arrival. It can be repeated in a list, but the proposal does **not** include room assignment, payment settlement, housekeeping readiness, guest messaging, or guest-facing self-service.

## Suggested screen behavior

1. **Default same-day row:** The receptionist sees a reservation row with artifact pills. Empty or unavailable values show `not generated` rather than implying missing backend persistence.
2. **Generate / rerun action:** A guarded `Run arrival bundle` button triggers, or in a prototype simulates, the existing CLI/module contract. The button copy should say `Generate artifacts from backend contract`, not `Check in guest`.
3. **Success state:** The row shows three generated artifacts: Meldeschein PDF, Apple PKPass, and Google Wallet JSON. The proof drawer records command/output-directory details.
4. **Partial/failure state:** If one artifact is missing, the strip shows a red/amber pill and a `view proof` drawer with stdout/stderr and expected filenames.
5. **Download/preview state:** PDF and payload preview links are labelled as generated files, not as submitted, installed, pushed, or legally filed.
6. **Manager/Kurverwaltung visibility:** A future manager view may aggregate counts of `generated` vs `blocked`, but this artifact should not add Kurverwaltung submission or municipal API behavior.

## Evidence anchors

### Current-job findings and plan anchors

- `output/findings/ui_surface_map.md:12-17` says the current operator surface is CLI-oriented: `kurort_engine` is reachable through `python -m kurort_engine` / `kurort-engine`, and the CLI parser exposes F5 receptionist and AVV subcommands. This supports a UI wrapper over CLI/module outputs, not a claim that a web app already exists.
- `output/findings/ui_surface_map.md:15-21` records that `repo/src/kurort_engine/__main__.py:92-153` exposes `meldeschein check-in`, `kurtaxe charge`, `remittance generate`, and `arrival bundle`, while F5 tests cover their observable output contracts.
- `output/findings/ui_surface_map.md:21` records that `repo/tests/test_f5_receptionist_subcommands.py:280-335` requires the arrival bundle to write three files: Meldeschein PDF, Apple PKPass, and Google Wallet JSON.
- `output/findings/ui_surface_map.md:27-29` maps the receptionist CLI action runner and arrival bundle artifacts to a safe **Guest Artifact Strip** rather than a general-purpose reception screen.
- `output/findings/ui_surface_map.md:48` identifies **Guest Artifact Strip / Arrival Action Runner** as the strongest code-grounded UI candidate, anchored to `repo/tests/test_f5_receptionist_subcommands.py:280-335`, `repo/src/kurort_engine/__main__.py:138-153`, and `repo/src/kurort_engine/guest_arrival.py:34`.
- `output/findings/ui_surface_map.md:55-57` warns that no web/UI/API layer was found and that later idea artifacts should use proof labels because many surfaces are test-contract or CLI-contract backed.
- `output/findings/ui_surface_map.md:83-86` explicitly shortlists this path, `output/ideas/ui_001_today_arrivals_artifact_strip.md`, and says the idea is non-duplicate because it is scoped to one arrival row/card and artifact statuses.
- `plan.md:30-31` says D6 and D7 remain: current-job UI idea artifacts and a KB idea/output index. This file advances D6.
- `plan.md:189-204` defines the required sections for each idea artifact; this artifact follows that template.
- `plan.md:208` selects this exact artifact as the strongest local grounding and requires it to wrap the CLI-backed arrival bundle without command-center/kiosk framing.

### Duplicate-risk anchors

- `output/findings/phase1_duplicate_risk_inventory.md:18` says a generic reception command center / single-screen reception UX has high duplicate/supersession risk; only a narrow Today shift queue visualizing shipped primitives survives.
- `output/findings/phase1_duplicate_risk_inventory.md:19` says kiosk/self-check-in/guest-facing PWA is a direct duplicate and should not be re-proposed.
- `output/findings/phase1_duplicate_risk_inventory.md:20` says a new mobile wallet/Kurkarte app is duplicate or shipped-foundation risk, but a per-guest artifact strip showing wallet/pass status is safe.
- `output/findings/phase1_duplicate_risk_inventory.md:40-42` lists Today shift queue, Guest artifact strip, and Statutory delivery lane as safe surviving UI primitives.
- `output/findings/phase1_duplicate_risk_inventory.md:49` states that exact candidate source files should be reopened before final proposal drafting if the proposal depends on specific line claims; this artifact therefore cites the Phase 2 surface map’s exact repo/test anchors and labels implementation claims as `requires new API contract` until Developer re-reads source before building.

## Specific project locations investigated

- `output/findings/ui_surface_map.md` — primary codebase-to-UI mapping source used for this artifact.
- `output/findings/phase1_duplicate_risk_inventory.md` — duplicate/dead-end source used to constrain scope.
- `plan.md` — deliverable template and selected drafting target.
- `output/findings/phase5_ui_idea_evidence_anchors.md` — Phase 5 extraction note for this artifact’s evidence anchors and guardrails.

## Likely future project locations touched by a Developer

These are **not** implementation instructions for this Scholar phase; they are handoff pointers for a later Developer if Critic approves the idea.

- `repo/src/kurort_engine/__main__.py` — current CLI parser contract for `arrival bundle` and related receptionist commands.
- `repo/src/kurort_engine/guest_arrival.py` — current module anchor for `build_arrival_bundle` as reported in `ui_surface_map.md:28` and `:48`.
- `repo/tests/test_f5_receptionist_subcommands.py` — current test contract for the three-file arrival bundle output.
- A future frontend/API path, not currently present in the repo, would need to be created or selected before implementation. The Phase 2 map found no existing web/API layer (`output/findings/ui_surface_map.md:55-66`).

## Expected impact

- **Receptionist speed:** A single row can show whether the three arrival artifacts exist, reducing the need to inspect output directories or remember CLI command results.
- **Lower duplicate risk:** The component reuses the safe artifact-strip primitive rather than restarting kiosk, guest portal, or command-center work already flagged as duplicate.
- **Better implementation handoff:** Explicit proof labels separate what is already test/CLI-backed from what still needs API, persistence, and delivery contracts.
- **Compliance clarity:** The UI can distinguish generated documents from submitted/installed/delivered documents, reducing over-claiming in legal and wallet-adjacent workflows.

## Effort estimate

**Small-to-medium design effort; medium implementation uncertainty.**

- Design/prototype effort: **S** — one reusable row/card component with pills, drawer, and state copy.
- Backend/API integration effort: **M/L** until a web/API contract, persistence model, auth model, and file-delivery contract exist. `output/findings/ui_surface_map.md:63-70` flags CLI-only, absent API, missing persistence, and missing role/permission contracts.
- Test effort: **M** — should preserve existing F5 CLI tests and add UI/API-level tests only after a frontend/API architecture exists.

## Risks and dependencies

| Risk / dependency | Why it matters | Mitigation in this proposal |
|---|---|---|
| No current web/API layer | The Phase 2 map found CLI/module/tests, not routes/components/API schemas (`output/findings/ui_surface_map.md:55-66`). | Label as `requires new API contract`; design around command/result proof rather than pretending a web app exists. |
| Missing persistence model | The map found no database/repository/transaction contract (`output/findings/ui_surface_map.md:69`). | Treat artifact state as generated-output proof until durable status storage exists. |
| Missing role/permission model | The map found no users/RBAC/login surface (`output/findings/ui_surface_map.md:70`). | Treat `Receptionist` as a persona, not verified authorization; include disabled/sensitive-action states in later design. |
| Wallet over-claim | Wallet payloads are generated/test-key outputs, not proof of device installation or push delivery (`output/findings/ui_surface_map.md:74`). | Use `payload generated`, `download`, and `preview` copy; avoid `sent to phone` or `installed`. |
| Kiosk/portal duplicate drift | Kiosk/self-check-in/guest portal work is a direct duplicate risk (`phase1_duplicate_risk_inventory.md:19`). | Staff-only row/card; no guest-facing PWA, offline queue, or self-service journey. |
| Broad command-center drift | A generic reception command center is high duplicate/supersession risk (`phase1_duplicate_risk_inventory.md:18`). | One artifact strip component; no all-purpose reception dashboard scope. |
| Housekeeping/room-readiness temptation | Phase 2 found no code-grounded housekeeping/room backend (`output/findings/ui_surface_map.md:43`, `:71`). | Do not include room readiness or housekeeping controls in this artifact. |

## Validation plan

1. **Static design review:** Confirm every pill/drawer state maps to one of the allowed proof labels: `CLI-backed`, `test-contract-backed`, `preview-only`, or `requires new API contract`.
2. **Contract review:** Re-read `repo/src/kurort_engine/__main__.py`, `repo/src/kurort_engine/guest_arrival.py`, and `repo/tests/test_f5_receptionist_subcommands.py` before implementation to verify command names, output filenames, and error cases.
3. **Acceptance test sketch:** Given a reservation ID and output directory, the UI/API layer should display success only when the expected Meldeschein PDF, Apple PKPass, and Google Wallet JSON are present, matching the F5 contract reported at `output/findings/ui_surface_map.md:21`.
4. **Duplicate review:** Compare final copy against `output/findings/phase1_duplicate_risk_inventory.md:18-22`; reject copy that says kiosk, self-check-in, guest portal, mobile wallet app, or command center.
5. **Unsupported-claim review:** Check that the UI never says “submitted to municipality,” “installed in wallet,” “room ready,” “paid,” or “checked in” unless later source evidence adds those contracts.

## Duplication check

This artifact is **not**:

- a broad reception command center (`phase1_duplicate_risk_inventory.md:18` blocks that scope),
- a kiosk/self-check-in/guest portal/PWA (`phase1_duplicate_risk_inventory.md:19` blocks that scope),
- a new mobile wallet app (`phase1_duplicate_risk_inventory.md:20` blocks that scope),
- a new Meldeschein/Kurtaxe/Kurkarte backend engine (`phase1_duplicate_risk_inventory.md:36` blocks backend-engine re-proposals),
- a housekeeping/room-readiness board (`ui_surface_map.md:43` and `:71` provide negative evidence).

It **is** a narrow, staff-facing artifact/status strip that visualizes outputs already identified as CLI/test-backed by the Phase 2 codebase map.

## Open questions

1. What should be the canonical API response shape for an arrival-bundle run: synchronous command result, async job, or file-index endpoint?
2. Where should generated files live in a web deployment, and what retention/security rules apply to Meldeschein and wallet payload artifacts?
3. What exact error states does `build_arrival_bundle` return or raise beyond the F5 happy-path output-file contract?
4. Should the receptionist row display Kurtaxe/remittance status later, or should that stay in the separate Kurort Exception Radar artifact?
5. What permission level should allow rerun/download once auth/RBAC exists?

## Minimal acceptance criteria for a future build

- The UI shows one row/card per reservation with explicit artifact status pills.
- The three artifact pills correspond to Meldeschein PDF, Apple PKPass, and Google Wallet JSON.
- A proof drawer exposes command/result/output evidence without claiming unsupported device delivery or municipal submission.
- All unsupported states are visibly labelled during design/dev review.
- The feature remains staff-facing and avoids kiosk, guest portal, command-center, mobile-wallet-app, housekeeping, and fiscal/POS scope.
