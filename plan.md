# Plan — KurortEngine Docker Compose deployment (gate-bounce-6 refspec-push recovery)

**Job:** `12a0e92c-docker-compose-deployment` (reopened after gate-bounce-5 → gate-bounce-6)
**Current phase:** 6 Strategic — feedback processing + corrective tactical-phase staging
**Plan revision:** 2026-08-18 (gate-bounce-6 rewrite per todo_3)
**Feedback KB note:** `phase-6-feedback-refspec-push-then-draft-pr-gate-bounce-6-recovery`
**Supersedes:** gate-bounce-5 plan (committed to main as ef75590; refspec mechanism replaces branch-name push)

---

## Deliverables (contract)

| Path | Purpose |
|------|---------|
| `output/kurortengine-deployment-smoke-report.md` | **Required deliverable.** Honest evidence record; container/Compose smoke is NOT VERIFIED (no docker binary in this Kubernetes-pod sandbox). §11 Post-Commit/PR Verification Log appended after DRAFT PR opens. |

All other bounded artifacts support the smoke-report deliverable; they are committed (LOCAL `main` at `ef75590`, 12 files / 1762 insertions) and shipped via DRAFT PR `feature/docker-compose-deployment` → `main`.

---

## Real git state (verified 2026-08-18 via harness git_status + git_log + git_show)

- **HEAD on LOCAL `main`** = `ef75590` ("deploy: add self-hostable Docker Compose deployment for KurortEngine", 12 files / 1762 insertions, authored by Agent) — LOCAL-only commit, NOT on any remote ref.
- **`origin/main`** = `439e506` (untouched — invariant 1.5 preserved).
- **`origin/feature/docker-compose-deployment`** = `439e506` (untouched, still at ancestor of main).
- **`origin/HEAD`** = `439e506`.
- **PR #2** (`feature/reception-cockpit-functional-walk-in` @ `0256d6d`) UNTOUCHED, verified via `git_log --decorate`.

---

## Completed phases (for context)

| Phase | Status | Key artifacts |
|-------|--------|---------------|
| Phase 0 — Strategic exploration | ✅ Complete | KB note `iter-39-scholar-phase-0-tactical-plan-ratification-5-phase-structure-pool-a-3-su` |
| Phase 1 — Tactical spec | ✅ Complete | `spec/docker_compose_deployment/spec.yaml` (63 lines, 7 ACs EARS, SHA `24abee69…`) |
| Phase 2 — Strategic close | ✅ Complete | GAPS verdict recorded |
| Phase 3 — Tactical RED tests + branch creation | ✅ Complete | `tests/test_server.py` (5 RED), `tests/test_deployment_artifacts.py` (2 RED); branch `feature/docker-compose-deployment` created from main |
| Phase 4 — Strategic feedback (gate-bounce-4) | ✅ Complete | Plan (gate-bounce-4 framing) + 4 corrective todos staged |
| **Phase 5 + 6 Tactical (gate-bounce-5)** | ✅ 1/3 PASS | todo_1 COMMIT PASS (`ef75590` on LOCAL main); todo_2 PUSH BLOCKED two-strike silent no-op; todo_3 ESCAPE VALVE sent to thread `7af428` |
| Phase 5 + 6 Strategic (gate-bounce-6 feedback) | ✅ todo_1 PROCESS + ✅ todo_2 EVALUATE; ⏳ todo_3 ADAPT PLAN (this file); ⏳ todo_4 CREATE CORRECTIVE TODOS | KB note `phase-6-feedback-refspec-push-then-draft-pr-gate-bounce-6-recovery` |

---

## Officer feedback (verbatim, gate-bounce-6)

> Resume only to publish and seal; preserve the existing KurortEngine checkout and local deploy commit `ef75590`. Use `repo_push` with repo `KurortEngine` and exact branch/refspec `+refs/heads/main:refs/heads/feature/docker-compose-deployment`. This must publish local main HEAD to the REMOTE FEATURE ref only; never push remote main or touch PR #2. Verify with `git_log --oneline --decorate -5` that `ef75590` is at `origin/feature/docker-compose-deployment` while `origin/main` and `origin/HEAD` remain `439e506`. Then open a DRAFT PR from `feature/docker-compose-deployment` to `main`; keep `output/kurortengine-deployment-smoke-report.md` explicit that Docker/Compose smoke is NOT VERIFIED; seal. Do not reimplement, rerun Docker, re-plan, or retry any failed operation more than once.

---

## Feedback-traceability matrix (gate-bounce-6)

| # | Feedback sub-item | Severity | Phase 6 todo that addresses it |
|---|-------------------|----------|-------------------------------|
| 1.1 | PRESERVE existing KurortEngine checkout + LOCAL deploy commit `ef75590` | CRITICAL | Pre-flight (git_status confirms) + invariant guardrail I.5 |
| 1.2 | `repo_push` with REFSPEC `+refs/heads/main:refs/heads/feature/docker-compose-deployment` (publishes LOCAL main → REMOTE feature ref, bypasses branch-name lookup) | CRITICAL | todo_6a REFSPEC PUSH |
| 1.3 | IMMEDIATE `git_log --oneline --decorate -5` verify: `ef75590` decorates `origin/feature/docker-compose-deployment`, `origin/main` + `origin/HEAD` stay at `439e506` | CRITICAL | todo_6a call 2 (very next call after refspec push) |
| 1.4 | DRAFT PR `feature/docker-compose-deployment` → `main` | CRITICAL | todo_6b REPO_OPEN_PR |
| 1.5 | Docker/Compose smoke "NOT VERIFIED" annotation preserved (smoke report) | CRITICAL | ALREADY ADDRESSED in `output/kurortengine-deployment-smoke-report.md` §10.3 + footer line 344; no pre-PR change required; deferred post-PR §11 update captures the verification line |
| 1.6 | SEAL — close ritual + `job_complete` after tactical phase | CRITICAL | todo_6d CLOSE RITUAL |
| 1.7 | NEVER touch PR #2 (`feature/reception-cockpit-functional-walk-in` @ `0256d6d`) | HIGH | invariant guardrail I.2 + todo_6a step 0 (preflight repo_pr_status(2)) + todo_6c step 2 |
| 1.8 | NEVER push remote main | HIGH | invariant guardrail I.1 + redundant in refspec (dst=feature) |
| 1.9 | HARD-STOP on refspec push failure or `origin/main` move — ONE blocking officer message + verbatim evidence + NO further retry | CRITICAL | todo_6e ESCAPE VALVE |
| 1.10 | "Do not reimplement, rerun Docker, re-plan, or retry any failed operation more than once" discipline | HIGH | Bounded corrective scope = ONE tactical phase, no re-plan, no Docker attempts, no retry loops |

---

## Corrective phase (ONE tactical phase, bounded handoff — gate-bounce-6)

**Goal:** Execute the officer's 4-step repo-tool sequence. ONE corrective Phase 6 covers ALL 10 feedback items (8 CRITICAL + 2 HIGH). No meta-todos, no cleanup, no packaging, no re-implementation.

### Why ONE phase (no split)

- The refspec push + git_log verify + DRAFT PR + close ritual is a single atomic sequence.
- No later fix can begin until the refspec push outcome is known — if it fails, todo_6e (escape valve) fires; if it succeeds, todos 6b–6d proceed in order.
- Pre-PR split is unnecessary because the bounded deliverables (12 files in `ef75590`) are already PASS-verified in Phase 5 / Phase 6 todo_2 EVALUATE — no content rewrites are pending.

### Real-time invariant guardrails

- **I.1** `origin/main` MUST NOT move off `439e506` — verified pre- and post-push via `git_log`.
- **I.2** PR #2 MUST be untouched — verified pre-push via `repo_pr_status(2)` + post-push via `git_log` (PR #2 SHA still `0256d6d`).
- **I.3** Docker smoke remains NOT VERIFIED — `output/kurortengine-deployment-smoke-report.md` §10.3 + footer line 344 retain the annotation; no content deletion.
- **I.4** No CLI `serve` subcommand added to `kurort_engine/__main__.py`; tests call `serve()` directly via `from kurort_engine.server import serve`.
- **I.5** Commit `ef75590` content preserved verbatim — no edits to Dockerfile / compose.yaml / .dockerignore / server.py / test_server.py / test_deployment_artifacts.py / runbook / spec.* / verify_protected_block.py.
- **I.6** No re-implementation: bounded deliverables untouched. Only the smoke report gets a §11 post-PR seal.

---

## Bounded corrective sequence (ONE pass, NO loop)

### Pre-flight (before any repo_push call, folded into todo_6a step 0)

git_status + git_log --oneline --decorate -5 + repo_pr_status(2) — recorded for the operational evidence trail.

### todo_6a — REFSPEC PUSH + IMMEDIATE VERIFY (Items 1.1, 1.2, 1.3, 1.7, 1.8)

**Goal:** Publish LOCAL `main` `ef75590` to REMOTE `feature/docker-compose-deployment` via the verified refspec, and IMMEDIATELY verify the push actually advanced the remote feature ref (does NOT issue a second push).

**Tool calls (3 calls, in order):**

1. **git_status** `KurortEngine` — confirm LOCAL branch = `main`, status = clean. Capture verbatim.
2. **repo_push** `KurortEngine` with `branch="+refs/heads/main:refs/heads/feature/docker-compose-deployment"` — THE EXACT REFSPEC the officer verified. The `+` prefix forces the update; the `SRC:DST` form publishes LOCAL main → REMOTE feature ref, bypassing the LOCAL feature-ref state that produced the prior two-strike silent no-op.
3. **git_log** `KurortEngine` with `max_count=5`, `oneline=true` — **IMMEDIATELY** verify the post-push state. PASS criteria:
   - `ef75590` decorates `origin/feature/docker-compose-deployment` (the new commit reached the remote feature ref)
   - `origin/main` STILL shows `439e506` (invariant I.1 preserved)
   - `origin/HEAD` STILL shows `439e506`
   - If all true → todo_6a PASS, proceed to todo_6b.
   - If push returned an error OR `origin/main` moved off `439e506` OR `ef75590` did NOT decorate `origin/feature/docker-compose-deployment` → route to todo_6e (ESCAPE VALVE), DO NOT continue to todo_6b, DO NOT retry.

**Failure handling (Item 1.9 HARD-STOP):** If call 2 fails OR call 3 fails any PASS criterion → STOP. Capture the exact tool result message + verbatim `git_log` output, then route todo_6e. NO further retry.

### todo_6b — DRAFT PR feature→main + post-PR §11 seal (Items 1.4, 1.5)

**Goal:** Open a DRAFT PR from `feature/docker-compose-deployment` → `main` with explicit `Container/Compose smoke NOT VERIFIED` annotation as the first paragraph. Then append §11 to smoke report with PR URL + DRAFT status + verification log.

**Tool calls (5 calls, in order):**

1. **repo_open_pr** `KurortEngine` with:
   - `title="deploy: add self-hostable Docker Compose deployment for KurortEngine"`
   - `base="main"`
   - `head="feature/docker-compose-deployment"`
   - `body` = markdown body that begins with the explicit NOT VERIFIED annotation block (Item 1.5):
     > **Container/Compose smoke is NOT VERIFIED** on this sandbox because the `docker` binary is absent (Kubernetes pod, no container-in-container runtime; no `/var/run/docker.sock`, no root). All non-Docker verification PASSED (static spec byte-identity, RED test-vs-artifact alignment, server.py route-handler inspection). Operators with Docker + Compose v2 should run `docker compose up -d` on a host with the runtime and expect the spec's `done_when` contract to satisfy. See `output/kurortengine-deployment-smoke-report.md` § Verification Log and § LIMITATIONS.
     - followed by a summary of the 7 ACs from `spec/docker_compose_deployment/spec.yaml`
     - followed by a list of the 12 bounded deliverable files
     - followed by the PR #2 untouched assertion (`This PR does NOT depend on or modify feature/reception-cockpit-functional-walk-in (PR #2 at 0256d6d).`)

2. **repo_pr_status** `KurortEngine, number=<new PR number>` — confirm PR opened, capture URL + state + head/base refs for the smoke report §11 update.

3. **edit_file** `repos/KurortEngine/output/kurortengine-deployment-smoke-report.md` — append new section `## 11. Post-Commit/PR Verification Log (Phase 6 Tactical todo_6b)` at the end of the file capturing: new commit SHA `ef75590`, post-refspec-push `git_log --oneline --decorate -5` verbatim (showing `ef75590 (HEAD -> main, origin/feature/docker-compose-deployment)` + `439e506 (origin/main, origin/HEAD)`), PR URL, the exact refspec push tool call used. Footer line 344 retains the original `NOT VERIFIED` annotation as the canonical limitation signal.

4. **repo_commit** `KurortEngine` with message `docs: smoke report §11 — post-refspec-push verify log + DRAFT PR URL` — local commit on `main` (no remote push, per invariant I.1).

5. **git_log** `KurortEngine` with `max_count=3`, `oneline=true` — capture post-smoke-edit state.

**Failure handling:** If `repo_open_pr` rejects (HTTP 422 "No commits between main and feature" risk if refspec push silently no-op'd) → STOP. Capture the exact tool result + verbatim `git_log`, route todo_6e. DO NOT retry.

### todo_6c — INVARIANT FINAL VERIFY (Items 1.7, 1.8)

**Goal:** Cross-check ALL invariants after the DRAFT PR opens — must NOT have moved `origin/main` off `439e506`, must NOT have touched PR #2, must NOT have introduced any additional remote-side changes.

**Tool calls (3 calls, in order):**

1. **git_log** `KurortEngine` with `max_count=5`, `oneline=true` — confirm `origin/main` is still at `439e506` + `origin/feature/docker-compose-deployment` is at `ef75590` + PR #2 (`feature/reception-cockpit-functional-walk-in`) is at `0256d6d` (untouched per invariant I.2).
2. **repo_pr_status** `KurortEngine, number=2` — confirm PR #2 state unchanged (verbatim response for invariant I.2 evidence).
3. **repo_pr_status** `KurortEngine, number=<new PR number>` — confirm the new DRAFT PR exists with `state=open` + `head=feature/docker-compose-deployment` + `base=main`.

**Failure handling:** Any invariant violation → STOP, route todo_6e with the exact tool result + verbatim `git_log`. DO NOT proceed to close ritual.

### todo_6d — CLOSE RITUAL (Item 1.6)

**Goal:** Mark the corrective tactical phase complete and invoke `job_complete` from a STRATEGIC transition.

**Note:** Per memory [1] close-ritual rule + Phase 6 Strategic todo list discipline, `job_complete` is invoked from the strategic phase transition that follows tactical completion, NOT from the tactical phase itself. After todo_6c passes, this strategic phase is re-entered (system-initiated phase transition); the strategic close ritual: re-read `skills/verify-before-done/SKILL.md` → call `mark_complete` (intermediate) → call `job_complete` (final).

**No tool calls in todo_6d itself.** This todo is the handoff marker to the system-driven strategic close ritual.

### todo_6e — ESCAPE VALVE (Item 1.9)

**Goal:** Triggered ONLY if todo_6a step 2 OR step 3 OR todo_6b step 1 OR todo_6c step 1/2/3 fails any criterion. Send ONE blocking officer message via `send_message` with exact evidence, then STOP.

**Tool calls (3 calls, in order):**

1. **git_status** `KurortEngine` — capture verbatim working-tree state.
2. **git_log** `KurortEngine` with `max_count=5`, `oneline=true` — capture verbatim decorate view.
3. **send_message** to `user` with `mode="blocking"`, `purpose="blocker"`, subject `[BLOCKER] Phase 6 refspec push/post-verify failed — <exact error one-liner>`, message body containing:
   - EXACT `git_status` output (verbatim)
   - EXACT `git_log --oneline --decorate -5` output (verbatim)
   - EXACT tool error message OR invariant violation description (verbatim)
   - State-change inventory: what succeeded, what failed, what remains
   - File paths that were successfully NOT touched (origin/main @ 439e506, PR #2 @ 0256d6d, 11 bounded deliverables)

4. After `send_message` returns, do NOT call `todo_complete` with PASS; call `todo_complete(todo_id="todo_6e")` with BLOCKED verdict + DO NOT call job_complete, DO NOT retry, DO NOT loop.

**HARD-STOP:** No third-push attempt under any circumstance. Per the officer's gate-bounce-6 directive: "do not retry any failed operation more than once".

---

## Bounded handoff enforcement

- **One corrective tactical phase, 5 todos** (6a REFSPEC PUSH + VERIFY, 6b DRAFT PR + smoke §11, 6c INVARIANT FINAL VERIFY, 6d CLOSE RITUAL, 6e ESCAPE VALVE).
- **No new housekeeping / meta todos.** No archiving. No cleanup. No packaging. No verification re-loops.
- **No re-implementation** of bounded deliverables. They are all PASS in Phase 5.
- **No retry of Docker.** BLOCKED on this sandbox; container/Compose smoke retains "NOT VERIFIED".
- **No broadening of scope.** No CLI `serve` subcommand, no Helm charts, no k8s manifests, no live backend wiring.
- **PR #2 untouched.** Verified at todo_6a step 0 (preflight repo_pr_status(2)) + todo_6c step 2 (post-push).
- **Loop prevention.** Each todo is completable in 3–5 tool calls. If a tool fails, route todo_6e with verbatim evidence. No third-push attempt under any circumstance.

---

## Corrective phase exit criteria

The corrective phase is complete when ALL of the following are true:

1. ✅ All 12 bounded deliverables committed on LOCAL `main` at `ef75590` (verified via `git_show --stat`).
2. ✅ REMOTE `origin/feature/docker-compose-deployment` advanced to `ef75590` AND `origin/main` remains at `439e506` (verified via `git_log --oneline --decorate -5` after the refspec push).
3. ✅ DRAFT PR opened against `main` with head = `feature/docker-compose-deployment` + explicit `Container/Compose smoke NOT VERIFIED` annotation as the first paragraph.
4. ✅ `output/kurortengine-deployment-smoke-report.md` updated with §11 Post-Commit/PR Verification Log block; §10.3 verdict block + footer line 344 retain "NOT VERIFIED" annotation.
5. ✅ PR #2 (`feature/reception-cockpit-functional-walk-in` @ `0256d6d`) is untouched (verified via `git_log` + `repo_pr_status(2)`).
6. ✅ `plan.md` rewrite ONCE in strategic phase (this file); sealed by `job_complete` from strategic phase transition.

Once the corrective phase exits, the strategic phase calls `job_complete` with the deliverable list + the "Container/Compose smoke NOT VERIFIED" annotation + confidence ≈ 0.7 (Docker smoke unverified).

---

## Escape valve protocol

If at any point during todo_6a, todo_6b, or todo_6c a concrete failure occurs (refspec push error, `origin/main` moves off `439e506`, `ef75590` did not decorate `origin/feature/docker-compose-deployment`, `repo_open_pr` rejects, `repo_pr_status` shows invariant violation):

1. Do NOT retry the same command.
2. Do NOT work around it with a creative alternative (no force-push, no amend, no new branch, no checkout, no manual git CLI).
3. Record the exact tool call string and raw error output verbatim.
4. Send ONE blocking officer message via `send_message` with the evidence.
5. STOP and wait for supervisor guidance. Never loop. Never call `job_complete` on a failed corrective phase.

---

## Branch discipline lesson (PIN for future KurortEngine work)

ALWAYS verify which branch HEAD is on (`git_status`) BEFORE the first `repo_commit` of a feature deliverable. When committing on a working-tree branch that diverges from the desired feature ref:

- **Branch-name pushes** (`branch="<feature>"`) publish the LOCAL feature ref → REMOTE feature ref. If the LOCAL feature ref has not advanced, this is a silent no-op regardless of any new commit on LOCAL `main`.
- **Refspec pushes** (`branch="+refs/heads/main:refs/heads/<feature>"`) publish the LOCAL `main` ref directly to the REMOTE feature ref, bypassing LOCAL feature-ref state. This is the correct mechanism when the commit landed on LOCAL `main` (not on the feature branch's local ref) and we want it on the REMOTE feature ref.
- **Always verify** the push outcome via `git_log --oneline --decorate -N` immediately after every `repo_push` (silent no-ops are possible on success messages).

The gate-bounce-6 root cause was the prior two strikes using branch-name pushes against a LOCAL feature ref that never advanced. The officer's verified refspec publishes LOCAL main directly to REMOTE feature without consulting LOCAL feature ref state. Future jobs must pre-flight `git_status`, verify push outcome via `git_log --decorate`, and prefer refspec pushes when the commit lives on a different LOCAL branch than the target REMOTE branch.
