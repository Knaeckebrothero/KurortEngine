# UI Idea 002 — Kurort Exception Radar

**One-line summary:** Add a staff-facing exception/status layer that turns Meldeschein, Kurtaxe, remittance, Rechnung, retention, and audit outputs into proof-labelled badges, without proposing a new tax engine, municipal adapter, fiscal backend, or broad compliance cockpit.

**Target role / workflow:** Receptionist and manager review of Kurort-specific blockers before arrival, check-in, month-end remittance, Badekur Rechnung preparation, and DSGVO retention/audit follow-up.

**Evidence labels:** `CLI-backed`, `module-backed`, `test-contract-backed`, `preview-only`, `stub-shaped`, `negative evidence`, `requires new API contract`.

## Research question for this artifact

How can Hotel Rheinland staff see the most important Kurort compliance and billing exceptions across existing backend/test surfaces while preserving the Phase 1 rule that Meldeschein, Kurtaxe, Kurkarte, spa/channel, and compliance work should be visualized as status/exception layers rather than re-proposed as backend engines?

## Proposal

Create a **Kurort Exception Radar** as a compact status-badge panel available from the receptionist daily view and manager back-office view. The radar is not a control tower and not a compliance cockpit. It is a proof-labelled checklist of exceptions and outputs that tells staff what is generated, previewed, draft-only, blocked, or unsupported.

### Badge rows

| Radar row | Badge examples | Primary action | Evidence label |
|---|---|---|---|
| Meldeschein | `PDF generated`, `missing required field`, `delivery not proven` | Open form/PDF proof drawer | `CLI-backed`, `test-contract-backed`, `preview-only` |
| Kurtaxe / Kurbeitrag | `calculation ready`, `exemption missing`, `charge handler unverified`, `municipality profile needed` | Open calculation confidence drawer | `module-backed`, `test-contract-backed`, `requires new API contract` |
| Remittance | `CSV draft`, `header verified`, `row total mismatch`, `not submitted` | Open CSV preview / reconciliation summary | `CLI-backed`, `test-contract-backed`, `preview-only` |
| Rechnung / Badekur | `invoice preview`, `SGB V fields missing`, `folio category missing` | Open line-item preview | `module-backed`, `test-contract-backed`, `preview-only` |
| Retention / DSGVO Art. 17 | `cascade preview`, `run logged`, `exception reason`, `manual review` | Open deletion impact preview | `module-backed`, `test-contract-backed`, `requires new API contract` |
| Audit trail | `event hash`, `append order`, `actor missing`, `not WORM-certified` | Open audit event drawer | `module-backed`, `test-contract-backed`, `preview-only` |
| Unsupported fiscal/housekeeping claims | `no local DATEV/TSE/POS evidence`, `no room-status backend evidence` | Show “not locally implemented” explanation | `negative evidence` |

### Screen placement

1. **Receptionist daily sidebar:** Shows only guest/reservation-relevant exceptions: Meldeschein, Kurtaxe, Rechnung blocker, and retention/audit flags relevant to a guest record.
2. **Manager month-end view:** Adds remittance CSV, reconciliation status, and aggregate blocker counts.
3. **Evidence drawer:** Every badge opens a drawer with source of truth, proof label, last generated artifact, expected missing fields, and unsupported-claim warning.
4. **No global compliance cockpit:** The radar should not become a legal-task dashboard. AVV and retention evidence-drawer interactions are handled separately in `output/ideas/ui_003_avv_retention_evidence_drawer.md`.

## Proposed UI states and copy

| State | Suggested badge copy | Staff-facing microcopy | Why this copy is safe |
|---|---|---|---|
| Generated | `Meldeschein PDF generated` | “PDF output exists from the backend contract. Submission/delivery is not proven here.” | Separates generation from municipal filing. |
| Needs input | `Kurtaxe exemption missing` | “Calculation confidence is low until exemption and municipality profile are confirmed.” | Avoids claiming a universal tax engine; respects municipality variance. |
| Draft | `Remittance CSV draft` | “CSV header/export is available. Municipality submission and acknowledgement are outside this proof.” | Avoids unsupported Kurverwaltung submission. |
| Preview | `Rechnung preview` | “Line items and statutory text can be reviewed before posting or PDF production.” | Avoids claiming AR ledger/payment/PDF invoice support. |
| Internal log | `Retention cascade logged` | “Internal cascade/audit proof is available. Guest self-service and legal-hold workflow are not proven.” | Avoids broad DSGVO cockpit/self-service scope. |
| Negative evidence | `No local POS/TSE screen` | “Current codebase map found no local module/test contract for this area.” | Prevents fiscalization over-claiming. |

## Evidence anchors

### Current-job findings and plan anchors

- `output/findings/ui_surface_map.md:29-35` maps Meldeschein PDF review, Kurtaxe breakdown, monthly remittance CSV preview, Rechnung preview, audit event table, AVV evidence drawer, and retention cascade timeline as UI-addressable workflow rows.
- `output/findings/ui_surface_map.md:29` identifies the Meldeschein form/PDF evidence: `repo/src/kurort_engine/meldeschein/__init__.py:97-119`, `:286`, `repo/tests/test_f5_receptionist_subcommands.py:85-135`, and `repo/src/kurort_engine/__main__.py:92-105`; it warns not to claim municipality adapter push, e-signature, multilingual robustness, or unattended self-check-in.
- `output/findings/ui_surface_map.md:30` identifies Kurtaxe anchors: `repo/src/kurort_engine/calculator.py:15-26`, `:171`, `repo/tests/test_calculator.py:23-87`, and `repo/tests/test_f5_receptionist_subcommands.py:143-193`; it warns the `kurtaxe charge` handler must not be presented as fully wired unless source confirms it.
- `output/findings/ui_surface_map.md:31` identifies remittance anchors: `repo/src/kurort_engine/reporting.py:146`, `repo/tests/test_reporting.py:178-420`, `repo/tests/test_f5_receptionist_subcommands.py:201-272`, and `repo/src/kurort_engine/__main__.py:118-136`; it warns there is no evidence of live Kurverwaltung submission, authentication, or municipal API.
- `output/findings/ui_surface_map.md:32` identifies Rechnung anchors: `repo/src/kurort_engine/rechnung.py:78`, `repo/tests/test_rechnung.py:195-369`, and README module table `repo/README.md:103-104`; it warns not to claim AR ledger, payments, dunning, cancellation invoices, ZUGFeRD/XRechnung, or PDF invoice production.
- `output/findings/ui_surface_map.md:33` identifies audit anchors: `repo/src/kurort_engine/audit.py:64-65`, `:102-130`, and `repo/tests/test_audit.py:54-321`; it warns that tests support append-only in-process log semantics, not WORM storage, GoBD-certified archive, role permissions, or multi-user concurrency.
- `output/findings/ui_surface_map.md:35` identifies DSGVO retention anchors: `repo/src/kurort_engine/kurgaste_retention/auto_cascade.py:113-331` and `repo/tests/test_auto_cascade.py:228-804`; it warns there is no evidence of guest self-service portal, identity verification, legal-hold workflow, or role-based authorization.
- `output/findings/ui_surface_map.md:49` lists **Kurort Exception Radar** as the second strongest code-grounded UI candidate and ties it to Meldeschein PDF, Kurtaxe calculator tests, reporting tests, Rechnung tests, retention tests, and audit tests.
- `output/findings/ui_surface_map.md:63-77` records the missing-contract register: CLI-only operator surface, absent web/API layer, suspect Kurtaxe charge wiring, header-only/draft remittance risk, missing persistence, missing role/permission model, unsupported housekeeping backend, unsupported fiscal/POS claims, and the proof-label rule.
- `output/findings/ui_surface_map.md:85-86` shortlists `output/ideas/ui_002_kurort_exception_radar.md` and says it should be only a badge/radar layer showing preview/draft/generated/blocked states with proof labels.
- `plan.md:209` selects this exact artifact and requires it to turn Meldeschein/Kurtaxe/remittance/Rechnung/retention/audit contracts into status badges without proposing new backend engines or a compliance cockpit.

### Duplicate-risk and blocked-scope anchors

- `output/findings/phase1_duplicate_risk_inventory.md:22` says a broad compliance cockpit / DSGVO Art. 17 self-service cascade is duplicate/risky; only narrow confirmation modals and retention/exception badges survive.
- `output/findings/phase1_duplicate_risk_inventory.md:23` says Meldeschein UI/statutory submission is UI-safe only if focused on status and exceptions, not on re-proposing adapters.
- `output/findings/phase1_duplicate_risk_inventory.md:24` says Kurtaxe/Kurbeitrag UI is safe only as status/exceptions; it specifically notes current CLI handler partiality and plugin sensitivity.
- `output/findings/phase1_duplicate_risk_inventory.md:27` says channel manager/OTA/revenue UI is safe only as exception reporting, not as a new channel manager module.
- `output/findings/phase1_duplicate_risk_inventory.md:35-36` says not to draft broad compliance cockpits or new backend engines for Meldeschein, Kurtaxe, Kurkarte, spa/wellness, or channel management.
- `output/findings/phase1_duplicate_risk_inventory.md:40-45` lists the safe primitive pool: statutory delivery lane, validity timeline, folio/compliance badges, and role-based landing pages.

### Memory / assumption handling

- Pinned project memory says Kurtaxe rules need a municipality plug-in approach because predicates and exemptions vary by Bundesland and Gemeinde. This artifact treats that as a design constraint for the `municipality profile needed` and `calculation confidence` badges rather than as a new implementation claim.

## Specific project locations investigated

- `output/findings/ui_surface_map.md` — primary codebase-to-UI map for all badge rows.
- `output/findings/phase1_duplicate_risk_inventory.md` — duplicate-risk and safe primitive pool source.
- `output/findings/phase5_ui_idea_evidence_anchors.md` — Phase 5 extraction note for artifact-specific evidence anchors.
- `plan.md` — deliverable template and selected drafting target.
- KB search query used before drafting: `Kurort Exception Radar Meldeschein Kurtaxe remittance Rechnung retention audit compliance cockpit duplicate failed dead-end Hotel Rheinland UI`.

## Likely future project locations touched by a Developer

These are future handoff pointers only; this Scholar artifact does not implement them.

- `repo/src/kurort_engine/meldeschein/__init__.py` and `repo/tests/test_f5_receptionist_subcommands.py` for Meldeschein/PDF proof.
- `repo/src/kurort_engine/calculator.py` and `repo/tests/test_calculator.py` for Kurtaxe calculation confidence.
- `repo/src/kurort_engine/reporting.py` and `repo/tests/test_reporting.py` for remittance CSV preview and reconciliation.
- `repo/src/kurort_engine/rechnung.py` and `repo/tests/test_rechnung.py` for Rechnung/Badekur preview.
- `repo/src/kurort_engine/audit.py` and `repo/tests/test_audit.py` for audit event drawers.
- `repo/src/kurort_engine/kurgaste_retention/auto_cascade.py` and `repo/tests/test_auto_cascade.py` for retention cascade preview and exception states.
- A future frontend/API path, persistent status table, role/permission model, and file-delivery endpoint; the current surface map found these contracts missing.

## Expected impact

- **Fewer silent blockers:** Staff can see when a guest or month-end process is blocked by missing fields, draft-only output, unverified charge wiring, or unsupported submission claims.
- **More honest compliance UX:** The radar distinguishes generated, previewed, draft, logged, stub-shaped, and unsupported states, reducing risk that staff treat a local file as a legal filing or official municipal acknowledgement.
- **Better Critic/Developer handoff:** Each badge points to source/test anchors and missing contracts, so downstream implementation can pick one badge row at a time.
- **Lower duplicate risk:** The artifact reuses Phase 1’s safe folio/compliance badges and statutory lane instead of reviving a compliance cockpit or backend engine.

## Effort estimate

**Medium design effort; medium-to-large implementation dependency.**

- Design/prototype effort: **M** — a badge panel, drawer pattern, and copy system across six workflow rows.
- Backend/API integration effort: **L** until a web/API layer, persistent status model, file index, and role model exist. `output/findings/ui_surface_map.md:63-70` flags these as missing.
- Incremental build path: **S/M per badge row** if Developer starts with a single proof source, such as remittance CSV draft or Meldeschein PDF generated.

## Risks and dependencies

| Risk / dependency | Evidence / reason | Mitigation in this proposal |
|---|---|---|
| Compliance cockpit scope creep | Phase 1 blocks broad compliance cockpit and full DSGVO cascade scope (`phase1_duplicate_risk_inventory.md:22`, `:35`). | Keep only badge rows and drawers; route AVV/retention deep interaction to the separate evidence-drawer artifact. |
| Kurtaxe charge over-claim | Phase 2 warns the `kurtaxe charge` handler may be stub-like / not fully wired (`ui_surface_map.md:30`, `:67`). | Use `calculation confidence` and `charge handler unverified` badges until handler-to-calculator integration is verified. |
| Remittance submission over-claim | Phase 2 says no evidence of live Kurverwaltung submission/auth/API (`ui_surface_map.md:31`, `:68`). | Use `CSV draft`, `header verified`, `not submitted`; never use `submitted` without new contract. |
| Rechnung over-claim | Phase 2 warns no AR ledger, payments, dunning, cancellation invoices, ZUGFeRD/XRechnung, or PDF invoice production evidence (`ui_surface_map.md:32`). | Present line-item/statutory text preview only. |
| Audit durability over-claim | Phase 2 says tests support in-process append-only semantics, not WORM/GoBD/role permissions/concurrency (`ui_surface_map.md:33`). | Label audit as event proof, not certified archive. |
| Retention self-service/legal workflow over-claim | Phase 2 says no guest self-service, identity verification, legal-hold workflow, or role-based authorization (`ui_surface_map.md:35`). | Keep retention badges internal/operator-facing and mark legal workflow as needing a new contract. |
| Missing persistence/roles/API | Phase 2 missing-contract register flags missing persistence and role/permission model (`ui_surface_map.md:69-70`). | Treat personas as design roles; require future API/status schemas before build. |
| Unsupported housekeeping/fiscal temptation | Phase 2 records negative evidence for housekeeping and DATEV/GoBD/Kasse/TSE/POS (`ui_surface_map.md:43-44`, `:71-72`). | Include negative-evidence badges rather than design production screens for these areas. |

## Validation plan

1. **Badge-to-evidence matrix review:** For each badge row, verify it maps to at least one exact anchor in `output/findings/ui_surface_map.md:29-35` or to negative evidence in `ui_surface_map.md:43-44`.
2. **Unsupported-claim review:** Reject any copy that says `submitted`, `certified`, `posted`, `paid`, `WORM`, `role-authorized`, `live sync`, or `guest self-service` unless a new contract is found.
3. **Kurtaxe implementation check before build:** Re-read `repo/src/kurort_engine/__main__.py`, `repo/src/kurort_engine/calculator.py`, and relevant tests to decide whether the `kurtaxe charge` badge can graduate from `charge handler unverified` to `charge generated`.
4. **Remittance implementation check before build:** Re-read `repo/src/kurort_engine/reporting.py`, `repo/tests/test_reporting.py`, and F5 remittance tests to confirm header, row count, totals, and output path behavior.
5. **Duplicate check:** Compare final feature copy against `output/findings/phase1_duplicate_risk_inventory.md:22-27` and `:35-36`; reject broad compliance cockpit, backend engine, channel manager, or adapter language.
6. **Future acceptance-test sketch:** Given a synthetic reservation/month context, each badge must show one of `generated`, `preview`, `draft`, `blocked`, `unverified`, or `not locally implemented`, with a proof drawer explaining the source.

## Duplication check

This artifact is **not**:

- a broad compliance cockpit or DSGVO Art. 17 self-service cascade;
- a new Meldeschein municipal adapter or statutory push integration;
- a new Kurtaxe/Kurbeitrag calculation engine;
- a new remittance/Kurverwaltung submission system;
- a fiscalization, DATEV, GoBD, Kasse, TSE, POS, or Z-Bon production screen;
- a housekeeping/room readiness board;
- a channel manager, OTA sync, or spa/wellness engine.

It **is** a narrow exception/status badge layer grounded in the current codebase map’s tested/module-backed surfaces and Phase 1’s safe primitive pool.

## Open questions

1. What normalized status schema should connect CLI/module outputs to badge states: per-reservation, per-month, per-processor, or per-audit-event?
2. Which row should be the first implementation slice: Meldeschein PDF, remittance CSV draft, or Kurtaxe calculation confidence?
3. How should badge timestamps be represented before durable persistence exists?
4. Which fields define `calculation confidence` for Kurtaxe: municipality profile, predicate, age, exemption, stay purpose, and Satzung version?
5. Which audit event fields can be safely shown to receptionist vs manager personas before a role/permission model exists?
6. Should negative-evidence badges be visible in production UI, or only in internal design/dev documentation?

## Minimal acceptance criteria for a future build

- The radar displays discrete badges rather than a broad cockpit.
- Every badge has a proof drawer with source, evidence label, and unsupported-claim warning.
- Kurtaxe, remittance, Rechnung, retention, and audit rows use cautious `preview`, `draft`, `unverified`, or `logged` language where required by the current map.
- The feature blocks or labels unsupported housekeeping and fiscal/POS claims.
- The design remains staff-facing and avoids guest portal, kiosk, backend-engine, and municipal-submission scope.
