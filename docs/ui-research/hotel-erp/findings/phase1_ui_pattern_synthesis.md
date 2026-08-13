# Phase 1 UI Pattern Synthesis — Hotel ERP System

**Research question written before synthesis:** Which PMS/front-office UI patterns are useful for a Hotel Rheinland / Kurort ERP design phase, while avoiding duplicate kiosk, guest-portal, command-center, and backend-feature proposals already present in `output/ideas/` and the prior design notes?

**Inputs synthesized:**
1. **Reader A — front desk / PMS command-center patterns:** returned evidence for receptionist task queue, arrival bundle, statutory exception lanes, Kurkarte/key timeline, folio-state badges, and PMS list/calendar primitives.
2. **Reader B — role dashboards / operations UI:** returned evidence for receptionist, housekeeping, manager, folio/reporting, and role-navigation patterns; included local external-doc anchors for Resavio, Canary, and RMS Cloud materials.
3. **Reader C — duplicate risk / mobile-self-service UI:** returned duplicate-risk inventory for kiosk, self-service, guest messaging, mobile wallet, DSGVO cascade, and generic command-center angles.
4. **Local duplicate scan:** `output/findings/phase1_duplicate_risk_inventory.md` lines 18-28 classify duplicate risk by UI direction; lines 32-36 list dead ends to avoid; lines 40-45 list non-duplicate primitives.

## 1. Synthesis verdict

The strongest Phase 1 direction is **staff-facing operational visibility**, not guest self-service or a broad command center. The safe UI design space is a set of narrow, role-based views and reusable components that wrap already-shipped or already-proposed backend surfaces: a receptionist today queue, per-guest artifact strip, statutory delivery lane, Kurkarte/key validity timeline, housekeeping readiness board, manager exception dashboard, and conservative reporting/export views.

The highest duplicate-risk directions are kiosk/self-check-in, generic reception command center, guest messaging/pre-check-in, mobile wallet/Kurkarte app, compliance cockpit, spa slot engine, channel manager, and new backend engines for Meldeschein/Kurtaxe/Kurkarte/spa/channel. Those areas are already represented in prior idea artifacts and should only contribute small staff-facing status, badge, confirmation, or exception primitives.

## 2. Ten evidence-backed UI pattern observations

### Observation 1 — Use a **Today shift queue**, not a generic ERP home page or broad command center.

**Pattern:** The receptionist landing view should be a queue of today’s arrivals, departures, statutory actions, folio blockers, and room-readiness blockers. Each row should have one primary next action and visible completion status.

**Evidence anchors:**
- `output/ideas/iter-16-receptionist-subcommands-proposal.md:12-18` states that iter-16 shipped operator-facing `meldeschein check-in`, `kurtaxe charge`, `remittance generate`, and `arrival bundle`, with an arrival-bundle orchestrator that writes three files per reservation.
- `output/ideas/iter-16-receptionist-subcommands-proposal.md:22-30` lists the concrete receptionist subcommands and the source module invoked by each.
- `output/findings/phase1_duplicate_risk_inventory.md:18` warns that broad reception command-center / single-screen reception UX is high duplicate/supersession risk and recommends a narrow Today shift queue.

**Design implication:** The UI should not be titled or scoped as a new “command center.” It should be framed as a **shift queue**: concrete jobs waiting for Frau Becker / reception staff.

### Observation 2 — Use a **guest artifact strip** for “one guest, all check-in artifacts.”

**Pattern:** Each arriving guest row/card should display the status of Meldeschein, Kurkarte Apple pass, Kurkarte Google object, Kurtaxe charge, remittance readiness, and key-validity state in a compact strip.

**Evidence anchors:**
- `output/ideas/iter-16-receptionist-subcommands-proposal.md:98-105` describes `arrival bundle --reservation ...` composing a `MeldescheinForm`, `KurpaketGuestCard`, and three shipped outputs: `meldeschein_<R>.pdf`, `kurkarte_apple_<R>.pkpass`, and `kurkarte_google_<R>.json`.
- `output/findings/phase1_duplicate_risk_inventory.md:20` notes that wallet/pass issuance is duplicate or shipped-foundation territory, but a per-guest artifact strip showing wallet/pass status remains safe.
- Reader A independently identified “one guest, all artifacts” as high-value and tied it to the arrival-bundle evidence.

**Design implication:** The UI can make the shipped bundle visible without proposing another wallet app or kiosk flow.

### Observation 3 — Use a **statutory delivery lane** for Meldeschein/Secra/AVS/Optima state.

**Pattern:** A lane or column should show `ready`, `sent`, `failed`, `needs correction`, and `retry scheduled` for statutory Meldeschein delivery.

**Evidence anchors:**
- `output/findings/phase1_duplicate_risk_inventory.md:23` classifies Meldeschein UI as partially duplicated at backend/CLI level but safe if focused on status and exceptions.
- The duplicate scan cites `output/ideas/iter2_002_proposal_w8_secra_avs_optima_meldeschein_push.md:15-20` for the existing Secra/AVS/Optima adapter proposal and `:51-53` for adapter ACs.
- `output/ideas/iter-16-receptionist-subcommands-proposal.md:22-30` anchors the shipped `meldeschein check-in` operator surface.

**Design implication:** UI design should visualize delivery state and retries; it should not re-propose vendor adapters or statutory push logic.

### Observation 4 — Add a **Kurkarte / room-key validity timeline** rather than a new mobile pass.

**Pattern:** A guest card should show Kurkarte activation, room-key valid-from/valid-until, checkout revocation, and mismatch warnings on a small timeline.

**Evidence anchors:**
- `output/findings/phase1_duplicate_risk_inventory.md:25` states that Kurkarte / room-key temporal binding is prior proposal territory, while a timeline and mismatch warnings remain UI-safe.
- The duplicate scan ties that to `output/ideas/iter2_001_proposal_w1_kurkarte_room_key_temporal_binding.md` functions for binding, temporal consistency, and checkout revocation around lines 62-64.
- `output/ideas/iter-16-receptionist-subcommands-proposal.md:98-105` confirms Kurkarte outputs are already part of the arrival bundle.

**Design implication:** Treat Kurkarte as a visible operational validity problem, not as a new app/pass issuance idea.

### Observation 5 — Show **Kurtaxe calculation confidence and exception badges** because current operator reachability is partial.

**Pattern:** The receptionist UI should flag missing municipality/exemption inputs, calculation confidence, and whether the charge was posted from a full calculator path or only recorded as a manual/stubbed charge.

**Evidence anchors:**
- `output/ideas/iter-16-receptionist-subcommands-proposal.md:73-84` says the shipped `kurtaxe charge` handler is a stub and does not call the shipped `calculate_kurtaxe_for_reservation(...)` path.
- `output/findings/phase1_duplicate_risk_inventory.md:24` classifies Kurtaxe/Kurbeitrag UI as safe only as status/exceptions, not as a new tax-engine proposal.

**Design implication:** UI should make calculation uncertainty visible; it must not imply the underlying calculation pipeline is fully wired if it is not.

### Observation 6 — Split **reception folio settlement** from **manager/statutory reporting**.

**Pattern:** Reception sees open balances, departure blockers, charge/refund state, and remittance readiness; managers see occupancy/revenue/Kurtaxe/remittance/DATEV/export and audit-ready reports.

**Evidence anchors:**
- Reader B found local external-document anchors: `documents/external/resavio.com_854742e8.md:L66` for “Financial dashboard and reports,” `documents/external/resavio.com_b8de1a3e.md:L35-L37` for reports, and `documents/external/www.rmscloud.com_6d3281ce.md:L75-L77` for daily/monthly/YTD reporting plus occupancy/forecast reports.
- `output/findings/phase1_duplicate_risk_inventory.md:44-45` includes folio/compliance badges and role-based landing pages in the non-duplicate primitive pool.
- `output/ideas/iter-16-receptionist-subcommands-proposal.md:86-92` warns that the shipped remittance handler currently emits header-only CSV with no data rows.

**Design implication:** Keep daily checkout speed separate from manager reporting; show remittance data-quality state before presenting a report as final.

### Observation 7 — Housekeeping should be a **room-readiness board connected to arrivals**, not a generic report.

**Pattern:** Housekeeping should see dirty/clean/inspected/out-of-order states, priority arrivals, late checkout blockers, and a “ready for guest” handoff visible to reception.

**Evidence anchors:**
- Reader B found local external-document anchors: `documents/external/resavio.com_854742e8.md:L68` for “Digital housekeeping tools,” `documents/external/resavio.com_b8de1a3e.md:L23-L35` for housekeeping/housekeeping app, and `documents/external/www.canarytechnologies.com_9c1190a9.md:L15-L17` for task/status/inventory and reporting/analytics.
- `output/findings/phase1_duplicate_risk_inventory.md:45` lists housekeeping readiness board as a role-based landing-page primitive.

**Design implication:** A housekeeping board is a UI/navigation primitive; it should not require a new unrelated back-office module in this research phase.

### Observation 8 — Manager dashboard should be **exception control for Kurort obligations**, not a decorative analytics dashboard.

**Pattern:** Manager view should prioritize unresolved statutory, financial, and operational exceptions: missing Meldeschein push, unposted Kurtaxe, Badekur billing blockers, quarterly Heilbad/reporting tasks, Kurkarte/key mismatches, and unresolved room/folio blockers.

**Evidence anchors:**
- Reader B tied this to design note `iter-2-q2-33-room-hessen-heilbad-operational-workflow-matrix-resavio-coverage-ga`, which identifies high-severity Kurkarte/room-key, Badekur billing, and Secra/AVS/Optima Meldeschein gaps and medium-severity Heilbad/Kurbeitrag update workflows.
- `output/findings/phase1_duplicate_risk_inventory.md:40-45` lists shift queue, statutory lane, validity timeline, folio/compliance badges, and role-based landing pages as safe primitives.

**Design implication:** Manager UI should collect exceptions across role views; it should not become a generic BI dashboard or new compliance cockpit.

### Observation 9 — Compliance actions should use **confirmation modals and retention badges**, not a broad “compliance cockpit.”

**Pattern:** Staff/admin UI may show retention blockers, required reasons, audit-log status, and consequence summaries for sensitive actions.

**Evidence anchors:**
- `output/findings/phase1_duplicate_risk_inventory.md:22` classifies broad compliance cockpit / DSGVO Art. 17 self-service cascade as duplicate/risky and reserves narrow confirmation modal plus retention/exception badges as safe.
- Reader C cites `output/ideas/iter34_002_proposal_dsgvo_art17_cascade.md:13-22` for the existing single-action cascade and `:110-122` for its retention/health-data/channel-reconciliation risks.

**Design implication:** Later UI ideas can improve affordance and safety around compliance actions, but cannot claim novelty for the cascade itself.

### Observation 10 — External PMS primitives are useful only after **Kurort-specific overlay**.

**Pattern:** Calendar/list/report/housekeeping primitives from general PMS systems should be adapted with Hotel Rheinland-specific statuses: Meldeschein, Kurbeitrag/Kurtaxe, Kurkarte, Badekur/GKV, Toskana/spa, AVV/DSGVO, and Kurverwaltung reporting.

**Evidence anchors:**
- Reader A found design note `iter-2-q1-resavio-pms-gap-matrix-vs-best-in-class-competitors-mewscloudbedsapale`, which describes Resavio PMS primitives such as occupancy calendar, offers/optional reservations, invoicing/accounting, financial dashboard, check-in/check-out/meals lists, digital housekeeping, and automatic pre-stay mails.
- Reader B found local external anchors for Resavio housekeeping/reports and RMS Cloud reporting: `documents/external/resavio.com_854742e8.md:L66-L68`, `documents/external/resavio.com_b8de1a3e.md:L23-L37`, and `documents/external/www.rmscloud.com_6d3281ce.md:L75-L77`.
- `output/findings/phase1_duplicate_risk_inventory.md:36` warns not to draft new backend engines for Meldeschein, Kurtaxe, Kurkarte, spa/wellness, or channel management in this UI design job.

**Design implication:** Use PMS conventions for layout, but make the meaning Kurort-specific and staff-operational.

## 3. Theme shortlist for later idea artifacts

### Theme A — **Reception Shift Queue + Artifact Strip**

**Core idea:** A receptionist view that lists today’s guests and wraps existing workflows: Meldeschein, Kurkarte Apple/Google artifacts, Kurtaxe, remittance, room readiness, key validity, and folio blockers.

**Why it survives duplicate scan:** It is narrower than a command center and visualizes shipped/known primitives rather than proposing new backend or kiosk scope.

**Primary anchors:** `output/ideas/iter-16-receptionist-subcommands-proposal.md:12-30`, `:73-105`; `output/findings/phase1_duplicate_risk_inventory.md:18-24`, `:40-45`.

### Theme B — **Kurort Exception Radar for Manager + Reception**

**Core idea:** A staff-facing exception layer for Meldeschein delivery, Kurtaxe calculation confidence, Kurkarte/key mismatches, Badekur/GKV blockers, retention blockers, and report/export data quality.

**Why it survives duplicate scan:** It is a visibility and prioritization UI, not a new Meldeschein adapter, Kurtaxe calculator, DSGVO cascade, or BI platform.

**Primary anchors:** `output/findings/phase1_duplicate_risk_inventory.md:22-25`, `:30-36`, `:40-45`; design note `iter-2-q2-33-room-hessen-heilbad-operational-workflow-matrix-resavio-coverage-ga` per Reader B.

### Theme C — **Role-Based Calm Back Office**

**Core idea:** Conservative ERP navigation with Reception, Housekeeping, Guests/Folios, Reports, Kurort Compliance, and Admin/AVV; each role lands on the queue it can act on today.

**Why it survives duplicate scan:** It is navigation and information architecture rather than a duplicated backend proposal.

**Primary anchors:** Reader B source anchors `documents/external/resavio.com_854742e8.md:L66-L68`, `documents/external/resavio.com_b8de1a3e.md:L23-L37`, `documents/external/www.canarytechnologies.com_9c1190a9.md:L15-L17`, `documents/external/www.rmscloud.com_6d3281ce.md:L75-L77`; duplicate inventory line 45.

### Theme D — **Compliance-Safe Microinteractions**

**Core idea:** Confirmation dialogs, retention badges, audit-log result chips, locale-status chips, BFSG/accessibility result chips, and staff-only template switches.

**Why it survives duplicate scan:** It extracts safe primitives from duplicated kiosk, guest-comms, and DSGVO-cascade proposals without re-proposing those modules.

**Primary anchors:** `output/findings/phase1_duplicate_risk_inventory.md:19-22`, `:30-36`, `:40-45`; Reader C anchors for `iter31_002`, `iteration7_002`, `loop16_002`, and `iter34_002`.

## 4. Source anchor index

### Local idea / finding files
- `output/findings/phase1_duplicate_risk_inventory.md:18-28` — duplicate-risk matrix.
- `output/findings/phase1_duplicate_risk_inventory.md:32-36` — dead ends to avoid.
- `output/findings/phase1_duplicate_risk_inventory.md:40-45` — non-duplicate primitive pool.
- `output/ideas/iter-16-receptionist-subcommands-proposal.md:12-30` — shipped receptionist CLI workflows.
- `output/ideas/iter-16-receptionist-subcommands-proposal.md:73-92` — Kurtaxe stub and remittance empty-CSV gaps.
- `output/ideas/iter-16-receptionist-subcommands-proposal.md:98-105` — arrival bundle composing Meldeschein + Apple Wallet + Google Wallet outputs.
- `output/ideas/iter31_002_proposal_h4_kiosk_mvp.md:15-18`, `:61-67`, `:84-91`, `:108-123` — kiosk/self-check-in duplicate and risk/scope warnings.
- `output/ideas/iter34_002_proposal_dsgvo_art17_cascade.md:13-22`, `:110-122` — compliance cascade duplicate and risks, per reader C.
- `output/ideas/iteration7_002_multi_language_guest_comms.md` and `output/ideas/loop16_002_multi_language_guest_comms.md` — guest-comms duplicate anchors, per reader C.
- `output/ideas/loop16_001_spa_wellness_resource_management.md` and `output/ideas/iter34_003_proposal_spa_belegung_sync_toskana.md` — spa/wellness duplicate anchors, per duplicate inventory.
- `output/ideas/iter4_003_channel_revenue_de_ota_bundle_hrs_booking.md` — channel/revenue duplicate anchor.

### Design-note anchors from readers / prior review
- `iter-30-product-qa-summary-hotel-rheinland-erp-2026-07-09` — current product is CLI/reception workflow shaped; UI/Web/API not probed by that QA cycle, per reader B.
- `iter-2-q2-33-room-hessen-heilbad-operational-workflow-matrix-resavio-coverage-ga` — Kurkarte/key, Badekur billing, Meldeschein push, and Heilbad/Kurbeitrag workflow gaps, per parallel readers A/B.
- `iter-2-q1-resavio-pms-gap-matrix-vs-best-in-class-competitors-mewscloudbedsapale` — generic PMS primitives and Resavio gap baseline, per reader A.
- `hotel-erp-ui-design-prior-knowledge-review-current-job` — current-job prior design-note review and duplicate-risk cautions.

### External/local document anchors from reader B
- `documents/external/resavio.com_854742e8.md:L66-L68` — financial dashboard/reports and digital housekeeping tools.
- `documents/external/resavio.com_b8de1a3e.md:L23-L37` — housekeeping app and reports anchors.
- `documents/external/www.canarytechnologies.com_9c1190a9.md:L15-L17` — housekeeping task/status/inventory and analytics anchors.
- `documents/external/www.rmscloud.com_6d3281ce.md:L75-L77` — reporting, occupancy, and forecast report anchors.

## 5. Evidence gaps and cautions before drafting final ideas

1. **Line-level re-read needed for reader-only anchors.** Several external/local document and prior-idea anchors were returned by readers but not re-opened in the parent context during this todo. Before an idea artifact relies on a specific quotation, re-read that source file and copy the exact line evidence.
2. **Current proof is CLI-heavy.** The strongest local product anchors are CLI and proposal artifacts, not a current web UI. UI proposals should be framed as design research, not as implementation-ready frontend code.
3. **Avoid novelty claims for backend scope.** Meldeschein push, Kurtaxe calculation, Kurkarte wallet/key binding, DSGVO cascade, spa sync, and channel manager each have existing proposal or shipped surfaces.
4. **Do not over-claim external vendor coverage.** Reader B provided useful PMS pattern anchors, but a later competitive benchmark should extract documents directly and use citation records if making vendor comparison claims.
5. **Terminology caution:** avoid “kiosk,” “self-check-in,” “guest portal,” “command center,” and “compliance cockpit” in idea titles unless the artifact is explicitly recording a dead end, because those terms overlap duplicated territory.

## 6. Phase 1 conclusion

Phase 1 advances four UI theme families for later proposal drafting: **Reception Shift Queue + Artifact Strip**, **Kurort Exception Radar**, **Role-Based Calm Back Office**, and **Compliance-Safe Microinteractions**. The duplicate scan blocks broad kiosk, command-center, guest messaging, compliance cockpit, mobile wallet, spa engine, and channel-manager ideas, but it leaves substantial room for staff-facing operational UI patterns that expose existing workflows, status, exceptions, and handoffs clearly.
