# Plan — KurortEngine Docker Compose deployment (gate-bounce-5 recovery)

**Job:** `kurortengine-docker-compose-deployment` (reopened after gate-bounce-5 PR-creation freeze + officer's bounded-commit directive)
**Current phase:** 5 Strategic — feedback processing + corrective phase staging
**Plan revision:** 2026-08-18 (gate-bounce-5 rewrite per todo_3)
**Feedback KB note:** `phase-5-feedback-commit-on-main-push-to-feature-branch-draft-pr-gate-bounce-5-re`
**Supersedes:** previous gate-bounce-4 plan (committed to main, branch remained ancestor)

---

## Deliverables (contract)

| Path | Purpose |
|------|---------|
| `output/kurortengine-deployment-smoke-report.md` | **Required deliverable.** Honest evidence record; container/Compose smoke is NOT VERIFIED (no docker binary in this Kubernetes-pod sandbox). §11 Verification Log appended post-PR-open. |

All other bounded artifacts are supporting the smoke-report deliverable; they are committed and shipped via DRAFT PR from `feature/docker-compose-deployment` → `main`.

---

## Completed phases (for context)

| Phase | Status | Key artifacts |
|-------|--------|---------------|
| Phase 0 — Strategic exploration | ✅ Complete (tag `12a0e92c-phase-0-strategic-complete`) | 5 todos archived; KB note `iter-39-scholar-phase-0-tactical-plan-ratification-5-phase-structure-pool-a-3-subagent-fan-out-phase-1-staged` |
| Phase 1 — Tactical spec | ✅ Complete (tag `12a0e92c-phase-1-tactical-complete`) | `spec/docker_compose_deployment/spec.yaml` (63 lines, 7 ACs in EARS, test_oracle paths, done_when); 4 todos archived |
| Phase 2 — Strategic close | ✅ Complete (tag `12a0e92c-phase-2-strategic-complete`) | GAPS verdict recorded; 2 todos archived |
| Phase 3 — Tactical RED tests + branch creation | ✅ Complete | `tests/test_server.py` (5 RED tests AC-1..AC-5), `tests/test_deployment_artifacts.py` (2 RED tests AC-6 + AC-7); branch `feature/docker-compose-deployment` created from `main` HEAD `439e506a` (local ref only — never pushed) |
| Phase 4 — Strategic feedback processing (gate-bounce-4) | ✅ Complete (todo_1 + todo_2 done) | Feedback categorized; outputs evaluated; plan.md (gate-bounce-4 framing) written; 4 Phase 5 corrective todos staged |
| Phase 5 Tactical (first pass, gate-bounce-5 blocker) | ✅ Complete with 3/4 BLOCKED | todo_1 VERIFY PASS (static byte-identity, 12-file content evaluation); todo_2 COMMIT BLOCKED (no git_checkout, refused to commit on main); todo_3 PUSH+PR BLOCKED (bare repo_push was silent no-op); todo_4 ESCAPE VALVE sent to thread `a6c2f1` |
| Phase 5 Strategic (gate-bounce-5 feedback processing) | ✅ todo_1 PROCESS FEEDBACK done; ✅ todo_2 EVALUATE OUTPUTS done; ⏳ todo_3 ADAPT PLAN (this file); � todo_4 CREATE CORRECTIVE TODOS pending | KB note `phase-5-feedback-commit-on-main-push-to-feature-branch-draft-pr-gate-bounce-5-re` updated with per-item evaluation |

**Real git state (verified 2026-08-18 via harness git_status + git_log, no prior summary trust):**

- HEAD on `main` at commit `439e506a` (Reception-Cockpit demo commit from prior job)
- `origin/feature/docker-compose-deployment` at the SAME commit `439e506a` (branch is an ancestor of `main` because no commit has ever landed on it)
- Working tree on `main` is DIRTY: 10 untracked entries representing **12 bounded deliverable files** that exist on disk but are not committed anywhere
- PR #2 (`feature/reception-cockpit-functional-walk-in` @ `0256d6d` on `origin`) is remote-only from prior job; not in local git_log; UNTOUCHED per invariant

**Root cause of gate-bounce-5:** Phase 5 Tactical (first pass) followed the stale "do NOT commit on main" guardrail from Phase 4 strategic without realizing the officer's gate-bounce-5 reply explicitly permits a LOCAL-only `repo_commit` on main (no remote push to main). The repo_commit was refused to fire, leaving the working tree dirty and the feature branch as an ancestor. The officer's new directive in feedback.md supersedes that guardrail.

---

## Corrective phase (ONE phase, bounded handoff — gate-bounce-5)

**Goal:** Execute the officer's 4-step repo-tool sequence. ONE corrective Phase 5 covers ALL 5 feedback sub-items. No meta-todos, no cleanup, no packaging, no re-implementation.

### Feedback-traceability matrix (gate-bounce-5)

| Feedback sub-item | Severity | Phase 5 todo that addresses it |
|-------------------|----------|-------------------------------|
| 1.1 `repo_commit` while HEAD on main — LOCAL commit only, must NOT push to remote main | CRITICAL | todo_5b (single `repo_commit` call on local main; no remote push) |
| 1.2 `repo_push` targeting `feature/docker-compose-deployment` — publishes local HEAD to that remote feature branch | CRITICAL | todo_5c (single `repo_push(branch="feature/docker-compose-deployment")` — must use explicit branch target, NOT bare) |
| 1.3 `git_log` verification — new commit at `origin/feature/docker-compose-deployment`; `origin/main` remains at `439e506` | CRITICAL | todo_5c step 2 (`git_log --oneline --decorate -5` after push; verify two invariants) |
| 1.4 `repo_open_pr` DRAFT from feature branch to main | CRITICAL | todo_5c step 3 (`repo_open_pr(base="main", head="feature/docker-compose-deployment")` with explicit NOT VERIFIED annotation) |
| 1.5 INVARIANT — do NOT push main, do NOT touch PR #2 | CRITICAL | todo_5b (single repo_commit, NO push); todo_5c (push targets `feature/docker-compose-deployment` only, NOT `main`); PR #2 verified untouched via `git_log` |
| 1.6 Failure mode — ONE blocker with exact tool call/error + git status/log, no loop | MEDIUM | todo_5d (escape valve: `send_message mode=blocking`, then STOP) |

### Bounded corrective sequence (one pass, no loop)

**Phase 5 covers ALL feedback sub-items in ONE tactical phase. 4 todos, 1–3 tool calls each.**

#### todo_5b — COMMIT (Items 1.1, 1.5)

**Goal:** Stage ALL 12 bounded deliverables and commit them as a LOCAL commit on `main` (no remote push). The commit lands on `main`'s local ref only; the push to remote happens in todo_5c with an explicit branch target.

**Tool calls:**
1. **git_status** `KurortEngine` — pre-commit inspection (Item 4 in earlier feedback; preserved as discipline). Verify branch is `main` and the 10 untracked entries are exactly the 12 intended files.
2. **repo_commit** `KurortEngine` with message: `deploy: add self-hostable Docker Compose deployment for KurortEngine (Dockerfile, compose.yaml, .dockerignore, operator runbook, stdlib HTTP server, RED tests, spec bundle, smoke report)`.
3. **git_log** `KurortEngine` with `max_count=3` — verify new commit landed locally; capture new SHA for todo_5c. Verify `main` local ref advanced but `origin/main` is NOT yet advanced.

**No `git_diff --stat` needed**: working tree contains only untracked additions (no modifications to existing files), so there are no surprises to inspect. Confirmed in todo_1 of Phase 5 Tactical first pass (10 untracked entries, 0 modified).

**No remote push in this todo.** The push happens in todo_5c with an explicit `branch="feature/docker-compose-deployment"` argument.

**Failure handling:** If `repo_commit` refuses with a non-recoverable error, route todo_5d immediately. Do NOT retry.

#### todo_5c — PUSH + VERIFY + PR (Items 1.2, 1.3, 1.4, 1.5)

**Goal:** Push `feature/docker-compose-deployment` to `origin` (publishing local HEAD to that remote ref); verify it is no longer an ancestor of `main`; open DRAFT PR against `main` with the explicit NOT VERIFIED annotation.

**Tool calls:**
1. **repo_push** `KurortEngine` with `branch="feature/docker-compose-deployment"` (EXPLICIT branch target — bare calls produced silent no-op in first pass).
2. **git_log** `KurortEngine` with `max_count=5`, `oneline=true` — verify two invariants:
   - `origin/feature/docker-compose-deployment` shows the new commit (advance from `439e506` to new SHA)
   - `origin/main` STILL shows `439e506` (NOT advanced — invariant 1.5)
3. **repo_open_pr** `KurortEngine` with:
   - `title="deploy: add self-hostable Docker Compose deployment for KurortEngine"`
   - `base="main"`
   - `head="feature/docker-compose-deployment"`
   - `body` = markdown body that includes:
     - **The explicit "Container/Compose smoke NOT VERIFIED" annotation** as the first paragraph: `> Container/Compose smoke is NOT VERIFIED on this sandbox because the docker binary is absent (Kubernetes pod, no container-in-container runtime). Non-Docker verification PASSED. See output/kurortengine-deployment-smoke-report.md § Verification Log and §6 LIMITATIONS.`
     - A summary of the 7 ACs from `spec/docker_compose_deployment/spec.yaml`
     - A list of the 12 bounded deliverable files
     - The PR #2 untouched assertion (`This PR does NOT depend on or modify feature/reception-cockpit-functional-walk-in (PR #2)`)
     - A short note that operators with Docker + Compose v2 should expect `docker compose up -d` to satisfy the spec's `done_when` contract
4. **read_file** `output/kurortengine-deployment-smoke-report.md` (verify-before-done gate).
5. **edit_file** smoke report: append new `## 11. Post-Commit/PR Verification Log` section at end of file (lines 348+). Content: new commit SHA from step 2; PR URL from step 3; verbatim `git_log --oneline --decorate -5` showing `origin/feature/docker-compose-deployment` advanced and `origin/main` unchanged.
6. **repo_commit** `KurortEngine` with message: `docs: append §11 Post-Commit/PR Verification Log to smoke report after PR open` — this commit also lands on local main (subsequent push in step 7).
7. **repo_push** `KurortEngine` with `branch="feature/docker-compose-deployment"` — push the smoke-report update to the feature branch.
8. **todo_complete** todo_5c with PASS verdict + the PR URL.

**Failure handling:** If step 1 (push) or step 3 (PR open) refuses with a non-recoverable error, route todo_5d immediately. Do NOT retry. Do NOT attempt to push main. Do NOT touch PR #2.

#### todo_5d — ESCAPE VALVE (Item 1.6)

**Goal:** Triggered ONLY if todo_5b step 2 (commit) or todo_5c step 1 (push) or step 3 (PR open) fails. Send ONE blocking officer message via `send_message` with exact evidence, then STOP.

**Tool calls:**
1. **git_status** `KurortEngine` — capture exact `git status --short` output.
2. **git_log** `KurortEngine` with `max_count=5`, `oneline=true` — capture exact `git log --oneline --decorate -5` output.
3. **send_message** to `user` with `mode="blocking"`, `purpose="blocker"`, subject `[BLOCKER] Phase 5 <step> failed — <exact one-line error>`, message body containing:
   - EXACT git_status output (verbatim)
   - EXACT git_log output (verbatim)
   - EXACT tool error message (verbatim)
   - State-change inventory: what was attempted, what succeeded before failure, what remains to do
4. **todo_complete** todo_5d with BLOCKED verdict — DO NOT call job_complete, DO NOT retry, DO NOT loop.

---

## Bounded handoff enforcement

- **One corrective phase, 3 main todos + 1 escape valve.** No more phases.
- **No new housekeeping/meta todos.** The system handles delivery.
- **No re-implementation of server.py or test_server.py.** They PASS.
- **No retry of Docker.** It is BLOCKED on this sandbox.
- **No broadening of scope.** No CLI `serve` subcommand, no Helm charts, no k8s manifests.
- **PR #2 untouched.** Verified at todo_5b step 1 (git_status confirms no changes to PR #2 branch) and again at todo_5c step 2 (git_log shows origin/feature/reception-cockpit-functional-walk-in unchanged at 0256d6d).
- **Loop prevention.** Each todo is completable in 1–3 tool calls. If a tool fails, return the exact command + raw error and route the escape valve.

---

## Corrective phase exit criteria

The corrective phase is complete when ALL of the following are true:

1. ✅ All 12 bounded deliverables committed locally on `main` (commit visible in `git_log --oneline --decorate -5`).
2. ✅ `origin/feature/docker-compose-deployment` shows the new commit AND `origin/main` remains at `439e506a` (invariant 1.5).
3. ✅ `feature/docker-compose-deployment` is no longer an ancestor of `main`.
4. ✅ DRAFT PR opened against `main` with explicit NOT VERIFIED annotation.
5. ✅ Smoke report §11 Post-Commit/PR Verification Log appended with new commit SHA, PR URL, and verbatim git_log.
6. ✅ PR #2 (`feature/reception-cockpit-functional-walk-in` @ `0256d6d`) is untouched.

Once the corrective phase exits, the next strategic phase runs `job_complete` with the deliverable list and the "NOT VERIFIED" annotation. **Never** call `job_complete` from the corrective tactical phase.

---

## Escape valve protocol

If at any point during the corrective phase a concrete repo-tool call fails:

1. Do NOT retry the same command.
2. Do NOT work around it with a creative alternative (no force-push, no amend, no new branch, no checkout, no manual git CLI).
3. Record the exact tool call string and raw error output verbatim.
4. Send ONE blocking officer message via `send_message` with the evidence.
5. STOP and wait for supervisor guidance.

Never loop. Never claim successful delivery when the evidence does not support it.

---

## Branch discipline lesson (PIN for future KurortEngine work)

ALWAYS verify which branch you are on (`git_status` on the repo) BEFORE the first `repo_commit` of a feature deliverable. If the feature branch was created from the working-tree base, artifacts MUST land on the feature branch (via an explicit `repo_push(branch="<feature-branch>")`), NOT on `main`'s remote ref. The gate-bounce-5 root cause was: (a) refusing to commit on main when the officer's directive permitted LOCAL-only commit, AND (b) calling bare `repo_push` which silently no-op'd. Future jobs must pre-flight `git_status`, commit on the current branch, push with an EXPLICIT branch target, and verify the push via `git_log --decorate` before claiming success.
