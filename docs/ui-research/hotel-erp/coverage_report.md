# Hotel ERP UI Design Research — Final Coverage Report

**Job:** Hotel ERP UI Design Research — Scholar  
**Project context:** Hotel Rheinland / Kurort ERP (`kurort_engine`)  
**Phase covered:** Current-job phases through Phase 7 Tactical Final Coverage Report  
**Status:** D1-D9 covered in this report; D10 remains for the final strategic completion gate.

---

## 1. Purpose and evidence basis

This report replaces the older iteration-level `output/coverage_report.md` with a current-job coverage report for the Hotel ERP UI Design research task. The current job’s goal is research/proposal work for a Hotel ERP UI, not production UI or backend implementation. `plan.md:3-5` states that the job is to research and generate evidence-backed UI design ideas grounded in the Hotel Rheinland / Kurort ERP project context.

This report is based on the following current-job artifacts and verification notes:

- `plan.md:21-36` — deliverable table D1-D10.
- `output/findings/phase7_final_coverage_inventory.md` — Phase 7 inventory identifying D9 as the remaining tactical deliverable and D10 as the final strategic completion record.
- `output/findings/phase1_ui_pattern_synthesis.md` — broad PMS/UI pattern synthesis and theme shortlist.
- `output/findings/phase1_duplicate_risk_inventory.md` — duplicate-risk/dead-end inventory and safe primitive pool.
- `output/findings/ui_surface_map.md` — codebase-to-UI surface map with exact repo/test anchors and implementation caveats.
- `output/findings/phase5_ui_idea_evidence_anchors.md` — evidence-anchor extraction note for the three Phase 5 ideas.
- `output/findings/phase7_q_coverage_bullets.md` — Q1-Q6 coverage extraction written in Phase 7.
- `output/findings/phase7_artifact_verification.md` — deterministic verification of the three Phase 5 idea artifacts.
- `output/ideas/ui_001_today_arrivals_artifact_strip.md`, `output/ideas/ui_002_kurort_exception_radar.md`, and `output/ideas/ui_003_avv_retention_evidence_drawer.md` — current-job idea artifacts.

---

## 2. Headline result

The current job produced a focused UI design research package for a German Kurort hotel ERP:

1. A broad UI pattern synthesis that narrowed the safe design space to staff-facing operational visibility rather than guest self-service or a broad command center (`output/findings/phase1_ui_pattern_synthesis.md:11-16`).
2. A duplicate-risk inventory that blocks already-covered kiosk, self-check-in, guest portal, mobile wallet app, broad compliance cockpit, broad reception command center, and backend-engine directions while preserving narrow staff-facing primitives (`output/findings/phase1_duplicate_risk_inventory.md:18-45`).
3. A codebase-to-UI surface map showing that the strongest local project anchors are CLI/module/test contracts, especially F5 receptionist commands, arrival-bundle outputs, AVV, audit, retention, remittance, and related `kurort_engine` modules (`output/findings/ui_surface_map.md:8-21`, `output/findings/ui_surface_map.md:23-51`).
4. Three substantive current-job UI idea artifacts:
   - `ui_001_today_arrivals_artifact_strip.md` — a receptionist arrival row/card for generated Meldeschein PDF, Apple PKPass, Google Wallet JSON, and CLI proof.
   - `ui_002_kurort_exception_radar.md` — proof-labelled exception badges for Meldeschein, Kurtaxe, remittance, Rechnung, retention, audit, and unsupported claims.
   - `ui_003_avv_retention_evidence_drawer.md` — admin/manager evidence drawers and confirmation microinteractions for AVV, retention, and audit proof.
5. An index note, `hotel-erp-ui-design-phase-5-idea-index.md`, indexing the three current-job idea artifacts and shared constraints.

The package intentionally does **not** implement production UI. It gives Critic/Developer a grounded proposal set plus explicit implementation-contract caveats.

---

## 3. Deliverable status D1-D9

| ID | Deliverable | Current-job status | Evidence / notes |
|---|---|---|---|
| D1 | Exploration plan with scope, questions, phases, and anti-duplication watchlist | **Done** | `plan.md` contains the restated goal, evidence anchors, D1-D10 deliverables, Q1-Q6 exploration questions, scope boundaries, phase outcomes, next/final strategic plan, and anti-duplication watchlist (`plan.md:1-294`). |
| D2 | Broad UI pattern synthesis with evidence anchors and theme shortlist | **Done** | `output/findings/phase1_ui_pattern_synthesis.md` contains ten UI pattern observations and four themes: Reception Shift Queue + Artifact Strip, Kurort Exception Radar, Role-Based Calm Back Office, and Compliance-Safe Microinteractions (`phase1_ui_pattern_synthesis.md:17-157`). |
| D3 | Duplicate-risk inventory naming prior ideas and dead ends to avoid | **Done** | `output/findings/phase1_duplicate_risk_inventory.md` lists duplicate-risk directions, dead ends, and safe primitives (`phase1_duplicate_risk_inventory.md:14-49`). |
| D4 | Codebase-to-UI surface map with exact repo/test anchors, candidate screens, data/API gaps, and risks | **Done** | `output/findings/ui_surface_map.md` maps `repo/README.md`, CLI parser, F5 tests, and many module/test surfaces to UI candidates, with a missing-contract register (`ui_surface_map.md:8-90`). |
| D5 | Design note summarizing codebase UI-ready surfaces and gaps | **Done** | design note `phase-2-codebase-ui-surface-map-for-hotel-erp-ui-design` was recorded earlier; `plan.md:31` marks it done as a codebase-mapping learning note. |
| D6 | 3-4 substantive current-job UI idea artifacts | **Done** | Three current-job artifacts exist and were verified in Phase 7: `ui_001_today_arrivals_artifact_strip.md`, `ui_002_kurort_exception_radar.md`, `ui_003_avv_retention_evidence_drawer.md` (`output/findings/phase7_artifact_verification.md`). |
| D7 | Idea index / output index for current-job ideas and findings | **Done** | `hotel-erp-ui-design-phase-5-idea-index.md` exists and is marked done in `plan.md:33`. Todo 5 will update the design notes only if final verification changes deliverable status. |
| D8 | Optional throwaway sketch/experiment if needed | **Not required** | Phase 5 and Phase 6 concluded no high-uncertainty UI hypothesis required a throwaway sketch/experiment; prose artifacts were sufficient (`plan.md:34`, `plan.md:204-206`). |
| D9 | Final coverage report and honest remaining-gaps list | **Done by this file, pending final verification in todo_5** | This rewritten `output/coverage_report.md` provides final coverage, deliverable status, idea summaries, unexplored gaps, and implementation-contract caveats. Todo 5 will append/integrate deterministic verification results. |

D10, the completion record, is intentionally not counted as a Phase 7 tactical deliverable. `plan.md:36` says it should be produced only after D9 and final deliverable verification pass.

---

## 4. Exploration question coverage

### Q1 — Front-desk / reception workflow

**Coverage level: strong for narrow staff-facing arrival artifacts; intentionally limited for broad reception dashboarding.**

The job identified the safest receptionist UI direction as a Today shift queue and per-guest artifact strip, not a broad command center. Phase 1 says the receptionist landing view should be a queue of arrivals, departures, statutory actions, folio blockers, and room-readiness blockers with one primary next action per row (`phase1_ui_pattern_synthesis.md:19-28`). It also defines a guest artifact strip for Meldeschein, Apple pass, Google Wallet object, Kurtaxe charge, remittance readiness, and key-validity state (`phase1_ui_pattern_synthesis.md:30-39`).

The codebase map grounds this in current CLI/parser/test contracts: `meldeschein check-in`, `kurtaxe charge`, `remittance generate`, and `arrival bundle`; F5 tests require the arrival bundle to write a Meldeschein PDF, Apple PKPass, and Google Wallet JSON (`ui_surface_map.md:15-21`, `ui_surface_map.md:27-31`).

The final artifact `output/ideas/ui_001_today_arrivals_artifact_strip.md` turns this into a concrete UI proposal: one reservation row/card with generated-artifact pills, a proof drawer, and explicit guardrails against guest portal, self-check-in, wallet delivery, payment settlement, room readiness, and persistence claims (`phase5_ui_idea_evidence_anchors.md:33-51`).

### Q2 — Operational dashboard / navigation model

**Coverage level: medium.**

The job explored role-based navigation as a design primitive rather than as a fully specified ERP IA. Phase 1 proposes a Role-Based Calm Back Office with Reception, Housekeeping, Guests/Folios, Reports, Kurort Compliance, and Admin/AVV, with each role landing on its actionable queue (`phase1_ui_pattern_synthesis.md:143-149`). The duplicate-risk inventory preserves role-based landing pages as safe navigation/visual design (`phase1_duplicate_risk_inventory.md:38-45`).

The codebase map supports some back-office status views through modules/tests for Kurpaket, spa/wellness, MinStay/channel dry-run, EV/e-bike charging, ESG/HCMI, predicate filing, AVV, audit, and retention (`ui_surface_map.md:37-42`, `ui_surface_map.md:51`). However, it also records negative evidence for locally implemented housekeeping/room-status backend and DATEV/GoBD/Kasse/TSE/POS production screens (`ui_surface_map.md:43-44`, `ui_surface_map.md:71-72`).

Important caveat: the repo scan found no user/role/permission model, so role labels such as Receptionist, Manager, Kurverwaltung, and Admin/AVV are design personas/navigation groups, not verified authorization boundaries (`ui_surface_map.md:69-70`).

### Q3 — Competitor and vendor patterns

**Coverage level: medium-low to medium.**

Phase 1 used local/external document anchors and parallel-reader synthesis to identify general PMS primitives: financial dashboards, reporting, housekeeping tools, task/status/inventory, occupancy/forecast reports, PMS list/calendar primitives, and role dashboards (`phase1_ui_pattern_synthesis.md:5-8`, `phase1_ui_pattern_synthesis.md:73-90`, `phase1_ui_pattern_synthesis.md:114-123`).

The main conclusion is that general PMS primitives are useful only after Kurort-specific overlay: Meldeschein, Kurtaxe/Kurbeitrag, Kurkarte, Badekur/GKV, Toskana/spa, AVV/DSGVO, and Kurverwaltung reporting (`phase1_ui_pattern_synthesis.md:114-123`).

Coverage caveat: Phase 1 explicitly warns that some external/vendor anchors were returned by readers and should be re-read directly before making exact vendor-comparison claims (`phase1_ui_pattern_synthesis.md:186-191`). For that reason, final idea artifacts rely primarily on local code/test and current-job finding anchors rather than strong vendor-comparison claims.

### Q4 — Existing-code fit

**Coverage level: strong.**

The codebase surface map is the primary Q4 deliverable. It explored the repo, README, tests, CLI parser, and `kurort_engine` modules, then mapped backend files/tests to likely UI screens and components (`ui_surface_map.md:3-6`, `ui_surface_map.md:8-90`).

The strongest code-grounded UI candidates were:

1. Guest Artifact Strip / Arrival Action Runner (`ui_surface_map.md:48`).
2. Kurort Exception Radar (`ui_surface_map.md:49`).
3. AVV / Retention Evidence Microinteractions (`ui_surface_map.md:50`).
4. Operational Back-Office Status Views, but only as narrower, more fragmented preview/status/report panels (`ui_surface_map.md:51`).

The map also records the key implementation caveat: no existing web/UI/API layer was found. The evidence is CLI/module/test-first, so proposals must be framed as design layers over module/CLI contracts, not as discovered existing frontend behavior (`ui_surface_map.md:53-57`, `ui_surface_map.md:65-66`).

### Q5 — Compliance and trust UX

**Coverage level: strong for proof-labelled microinteractions; limited for legal completeness.**

Phase 1 supports compliance-safe microinteractions: confirmation dialogs, retention badges, audit-log result chips, locale-status chips, BFSG/accessibility chips, and staff-only template switches, while blocking broad compliance-cockpit or DSGVO cascade claims (`phase1_ui_pattern_synthesis.md:104-112`, `phase1_ui_pattern_synthesis.md:151-157`).

The codebase map grounds trust UX in audit logs, AVV processor/reporting/test contracts, retention cascade source/tests, wallet payload tests, remittance/reporting tests, and required proof labels for generated/preview/dry-run/stub-shaped states (`ui_surface_map.md:33-36`, `ui_surface_map.md:57`, `ui_surface_map.md:73-77`).

Two final artifacts directly cover Q5:

- `ui_002_kurort_exception_radar.md` proposes proof-labelled badges for Meldeschein, Kurtaxe, remittance, Rechnung, retention, audit, and unsupported fiscal/housekeeping claims.
- `ui_003_avv_retention_evidence_drawer.md` proposes evidence drawers, confirmation copy, stub-shaped packet labels, exception reasons, audit hash visibility, and preview/executed distinctions for AVV/retention/audit workflows.

The compliance caveat is explicit: the current evidence supports UI status/proof/copy patterns, not final legal PDFs, certified WORM archives, complete DSGVO automation, legal-hold workflows, role-permission enforcement, or production municipal submission.

### Q6 — Mobile / self-service angle

**Coverage level: strong as duplicate-risk/constraint coverage; intentionally no new guest-facing concept.**

The duplicate-risk inventory directly blocks kiosk, self-check-in, guest-facing PWA, mobile guest portal, and new mobile wallet app directions (`phase1_duplicate_risk_inventory.md:18-21`, `phase1_duplicate_risk_inventory.md:30-36`).

The safe surviving mobile-adjacent primitive is staff-facing visibility into generated artifacts: a per-guest artifact strip showing pass/payload status and re-download/re-run state, not a new mobile wallet app or guest self-service flow (`phase1_duplicate_risk_inventory.md:20`, `phase1_duplicate_risk_inventory.md:40-42`). The codebase map similarly allows a Kurkarte wallet payload preview but warns not to claim production signing, push updates, installed pass state, device delivery, or a wallet app (`ui_surface_map.md:36`, `ui_surface_map.md:74`).

`ui_001_today_arrivals_artifact_strip.md` follows this constraint by treating Apple PKPass and Google Wallet JSON as generated artifacts/proof states rather than a delivered mobile journey.

---

## 5. Current-job idea artifact summaries

### 5.1 `output/ideas/ui_001_today_arrivals_artifact_strip.md`

**Summary:** A receptionist-facing arrival row/card that shows generated Meldeschein PDF, Apple PKPass, Google Wallet JSON, and CLI proof for one reservation.

**Evidence basis:** CLI/parser and F5 test anchors for `arrival bundle`, reported in `ui_surface_map.md:15-21`, `ui_surface_map.md:27-29`, and `ui_surface_map.md:48`.

**Why it matters:** It gives reception staff a narrow operational artifact/status view without creating another broad command center, kiosk, guest portal, or wallet app.

**Key caveats:** Requires a future API/file-delivery/status contract; cannot claim device delivery, municipal submission, room readiness, payment settlement, or persistence.

### 5.2 `output/ideas/ui_002_kurort_exception_radar.md`

**Summary:** A staff/manager exception-status badge layer for Meldeschein, Kurtaxe, remittance, Rechnung, retention, audit, and unsupported fiscal/housekeeping claims.

**Evidence basis:** Workflow-to-UI anchors for Meldeschein, Kurtaxe, remittance, Rechnung, audit, and retention in `ui_surface_map.md:29-35`; missing-contract warnings in `ui_surface_map.md:63-77`; duplicate constraints in `phase1_duplicate_risk_inventory.md:22-27` and `phase1_duplicate_risk_inventory.md:35-45`.

**Why it matters:** It lets staff see whether outputs are generated, previewed, draft-only, blocked, unsupported, or unverified, reducing silent operational and compliance over-claims.

**Key caveats:** Must not become a broad compliance cockpit or backend engine; Kurtaxe charge wiring, remittance submission, certified audit archive, role authorization, fiscal/POS production screens, and housekeeping backend remain unproven.

### 5.3 `output/ideas/ui_003_avv_retention_evidence_drawer.md`

**Summary:** A narrow admin/manager evidence-drawer pattern for AVV processor checks, AVV packet export warnings, retention cascade preview/run results, and audit proof microcopy.

**Evidence basis:** Audit, AVV, and retention rows in `ui_surface_map.md:33-35`; strongest-candidate note in `ui_surface_map.md:50`; stub-shaped AVV packet warning in `ui_surface_map.md:73`; proof-label rule in `ui_surface_map.md:77`; duplicate-risk constraints in `phase1_duplicate_risk_inventory.md:22` and `phase1_duplicate_risk_inventory.md:35`.

**Why it matters:** It provides safer microinteractions for sensitive compliance-adjacent actions without proposing a new AVV backend module, DSGVO self-service cascade, legal-hold manager, or global compliance cockpit.

**Key caveats:** Final legal PDF rendering, role-permission enforcement, durable audit archive, legal review, identity verification, and complete DSGVO automation remain outside current evidence.

---

## 6. Honest unexplored or underexplored gaps

1. **No shipped frontend/API architecture was found.** The repo evidence is Python modules, tests, and CLI contracts; UI proposals require a future web/API architecture, request/response schemas, auth/session model, async job model, file-delivery contract, and frontend route/component plan (`ui_surface_map.md:55-66`).
2. **No persistence model was established.** The codebase map found no database model, migrations, ORM/repository layer, transaction model, or durable status store for UI state (`ui_surface_map.md:69`).
3. **No role/permission model was established.** Role names in the artifacts are personas and navigation groups, not verified authorization boundaries (`ui_surface_map.md:70`).
4. **Housekeeping remains mostly external-pattern-only.** Phase 1 discusses housekeeping as a PMS primitive, but Phase 2 found no local housekeeping/room-status backend/test evidence (`ui_surface_map.md:43`, `ui_surface_map.md:71`).
5. **DATEV/GoBD/Kasse/TSE/POS production UI remains unsupported.** README mentions DATEV, but the scan did not find matching modules/tests for production fiscalization screens (`ui_surface_map.md:44`, `ui_surface_map.md:72`).
6. **Vendor/competitor evidence is useful but not deep enough for final vendor claims.** Phase 1 warns that reader-only vendor anchors should be re-read directly before exact vendor-comparison claims (`phase1_ui_pattern_synthesis.md:186-191`).
7. **Kurtaxe charge and remittance submission need implementation verification.** The map flags suspect/stub-like Kurtaxe charge wiring and header-only/draft remittance risk; UI copy must remain cautious until Developer re-reads and tests implementation paths (`ui_surface_map.md:67-68`).
8. **AVV and audit evidence are not legal certification.** The AVV audit packet is stub-shaped in at least one path, and audit tests do not prove WORM/GoBD-certified archive or multi-user authorization (`ui_surface_map.md:33`, `ui_surface_map.md:73`).
9. **Operational Back-Office Preview Panels were not drafted.** The fourth candidate, `ui_004_backoffice_preview_panels.md`, was intentionally skipped because the three drafted artifacts already satisfy D6 and the fourth was broader/more fragmented (`ui_surface_map.md:88-90`, `plan.md:204-206`).

---

## 7. Implementation-contract caveats for Critic/Developer

A Developer should not treat these artifacts as implementation-ready frontend specs. They are evidence-backed proposals requiring contract decisions before build.

Required contracts before production implementation include:

- **Web/API contract:** route definitions, request/response schemas, error envelopes, async job model, command execution boundary, and file-delivery model (`ui_surface_map.md:65-66`).
- **Persistence contract:** database schema, migration history, transaction/concurrency model, generated-file index, durable status store, and retention rules (`ui_surface_map.md:69`).
- **Auth/RBAC contract:** users, roles, permissions, denied-action auditing, and least-privilege tests (`ui_surface_map.md:70`).
- **Kurtaxe/remittance contract:** verified handler-to-calculator integration, folio mutation rules, idempotency, remittance data rows/totals, municipal submission protocol, and acknowledgement model (`ui_surface_map.md:67-68`).
- **Wallet/pass contract:** production signing key management, Apple/Google API integration, delivery callbacks, revocation/update flow, and device/platform error handling (`ui_surface_map.md:74`).
- **Compliance/audit contract:** final AVV PDF renderer/spec, legal review status, evidence attachment/signature/hash verification, durable audit storage, WORM/GoBD claim rules, and sensitive-data permission checks (`ui_surface_map.md:33`, `ui_surface_map.md:73`).
- **Live integration contract:** credentials, webhook/retry/backoff, reconciliation logs, production transport tests, and monitoring for channel/EV/spa-like integrations (`ui_surface_map.md:75`).

Until these exist, artifacts should retain labels such as `module-backed`, `CLI-backed`, `test-contract-backed`, `preview-only`, `dry-run`, `stub-shaped`, `negative evidence`, and `requires new API contract` (`ui_surface_map.md:77`).

---

## 8. Final verification results

Phase 7 final verification was run after the report rewrite and saved in `output/findings/phase7_final_verification.md`.

### Verification method

The verification script checked required current-job deliverables, findings, the three idea artifacts, this coverage report, and the materialized design notes idea/output index for file existence, required section strings, unresolved marker tokens, byte size, word count, and evidence-label presence in the three idea artifacts. Ordinary phase-management words such as todo/todos were not treated as failures.

### Verification summary

- `plan.md` — PASS; 28051 bytes; 3541 words; missing sections: none; unresolved markers: none.
- `output/findings/phase1_ui_pattern_synthesis.md` — PASS; 19600 bytes; 2115 words; missing sections: none; unresolved markers: none.
- `output/findings/phase1_duplicate_risk_inventory.md` — PASS; 12152 bytes; 1400 words; missing sections: none; unresolved markers: none.
- `output/findings/ui_surface_map.md` — PASS; 34219 bytes; 3736 words; missing sections: none; unresolved markers: none.
- `output/findings/phase5_ui_idea_evidence_anchors.md` — PASS; 10383 bytes; 1198 words; missing sections: none; unresolved markers: none.
- `output/findings/phase7_final_coverage_inventory.md` — PASS; 4178 bytes; 553 words; missing sections: none; unresolved markers: none.
- `output/findings/phase7_q_coverage_bullets.md` — PASS; 10279 bytes; 1136 words; missing sections: none; unresolved markers: none.
- `output/findings/phase7_artifact_verification.md` — PASS; 4241 bytes; 596 words; missing sections: none; unresolved markers: none.
- `output/ideas/ui_001_today_arrivals_artifact_strip.md` — PASS; 14659 bytes; 1824 words; missing sections: none; unresolved markers: none.
- `output/ideas/ui_002_kurort_exception_radar.md` — PASS; 18078 bytes; 2154 words; missing sections: none; unresolved markers: none.
- `output/ideas/ui_003_avv_retention_evidence_drawer.md` — PASS; 17202 bytes; 2103 words; missing sections: none; unresolved markers: none.
- `output/coverage_report.md` — PASS; 25692 bytes; 2854 words; missing sections: none; unresolved markers: none.
- `hotel-erp-ui-design-phase-5-idea-index.md` — PASS; 5122 bytes; 541 words; missing sections: none; unresolved markers: none.

### Idea artifact label summary

- `output/ideas/ui_001_today_arrivals_artifact_strip.md` — proof/evidence labels present: module-backed, CLI-backed, test-contract-backed, preview-only, negative evidence, requires new API contract; evidence-anchor hits: 75; result: PASS.
- `output/ideas/ui_002_kurort_exception_radar.md` — proof/evidence labels present: module-backed, CLI-backed, test-contract-backed, preview-only, stub-shaped, negative evidence, requires new API contract; evidence-anchor hits: 102; result: PASS.
- `output/ideas/ui_003_avv_retention_evidence_drawer.md` — proof/evidence labels present: module-backed, test-contract-backed, preview-only, dry-run, stub-shaped, requires new API contract; evidence-anchor hits: 78; result: PASS.

### Final verification verdict

**PASS.** All required current-job deliverable, finding, idea, coverage, and materialized index files checked by the script exist, include the required section strings, contain no unresolved marker tokens, meet minimum byte-size thresholds, and the three idea artifacts include evidence/proof labels plus multiple file/path anchors. Deliverable status did not change: D1-D9 are covered; D10 remains for final strategic completion. Because deliverable status did not change, the design notes idea/output index did not require an update.

## 9. Coverage conclusion

The current job has produced a complete research/proposal package for Hotel ERP UI design with strong local evidence for three UI idea artifacts and clear caveats for what remains unimplemented or unproven.

**Most covered:**

- Q1 front-desk artifact/status workflow.
- Q4 existing-code fit.
- Q5 compliance/trust microinteractions.
- Q6 mobile/self-service duplicate constraints.

**Partially covered:**

- Q2 full role-based IA, because role/persona navigation is explored but auth/persistence/backend support is missing.
- Q3 competitor/vendor patterns, because PMS primitives were surveyed but exact vendor claims should be re-read before any external benchmark deliverable.

**Recommended next action:** final strategic review should verify this file after todo_5 integrates the final check results, then produce D10 via completion tooling if all deliverables remain present and substantive.
