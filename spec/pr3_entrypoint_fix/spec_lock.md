# spec_lock.md — KurortEngine PR #3 entrypoint fix

> **Locked:** 2026-08-20 (Phase 1 spec, job 6ce5bc4c-b773-4027-b47f-55d5308c92bb)
> **Feature:** `pr3-entrypoint-fix`
> **Branch (planned):** `fix/pr3-container-entrypoint-server-module` (stacked on `feature/docker-compose-deployment`)
> **Locked spec SHA-256:** `497aa23f07457962c86376bd4bb51b8915369714091258887b81aa1ea786e050`
> **AC block byte length:** 10723 bytes (full spec.yaml), 5247 bytes (AC block only)
> **AC block SHA-256:** `65d5171c4e92f836214c2cabbac3ff2b9a5be9c0d60cc4803aa919ddf8bbe50c`

## Locked spec provenance

- `spec.yaml` was authored on `feature/docker-compose-deployment` @ `28e93ec26b0e1612b6e5e4f31a792f8ec64e26bc` (this branch, see `git rev-parse HEAD`).
- The acceptance-criteria block was extracted byte-for-byte from `spec.yaml` (lines between `## Acceptance criteria (EARS)` and the next `## ` section) and copied verbatim into the PROTECTED block below. No characters were added, removed, re-encoded, or normalised.
- PyYAML is not installed in this sandbox; the canonical AC block was extracted by literal line-slicing on the source file (which is byte-stable for the AC block because the block contains no YAML re-encoding or round-trip).
- The companion `verify_protected_block.py` (mirroring the existing PR #3 `spec/docker_compose_deployment/verify_protected_block.py`) re-runs the byte-identity check on every CI / future iteration.

## Bases and heads

- `main` (protected): `439e506a218c2e6a8c708cdf7b1f9c9a8a4ae3b5` — `docs: add Reception-Cockpit five-minute walk-in demo`.
- `feature/docker-compose-deployment` (PR #3 base): `439e506` + 2 commits:
  - `ef75590` deploy: add self-hostable Docker Compose deployment for KurortEngine
  - `28e93ec` docs: plan.md gate-bounce-6 refspec-push recovery rewrite
- `feature/reception-cockpit-functional-walk-in` (PR #2, FROZEN): `0256d6db88bc9c74db4affb5d723dcac964add7d`
- `fix/pr2-reception-cockpit-harness-and-browser-proof` (PR #4 base): `bea4c6d148f7dd4ad7b9fd0016c75476030beaa7`
- `feat/pr4-reception-cockpit-e2e-coverage-follow-up` (PR #4 follow-up): `ddde0f0…` (head at the time of the fix; recorded at run time)

## Real entrypoint evidence (why the bounded fix is needed)

- `src/kurort_engine/server.py` line 55: `__all__ = ["serve", "build_handler", "find_default_artefact"]`.
- `src/kurort_engine/server.py` line 200: `def serve(host: str = "0.0.0.0", port: int | None = None) -> None:`.
- `Dockerfile` line 54 (CURRENT, broken): `CMD ["python", "-m", "kurort_engine"]` — at runtime this invokes `src/kurort_engine/__main__.py:parser.print_help()` (line 273) and returns 0, never importing `kurort_engine.server` and never binding a port.
- `src/kurort_engine/__main__.py` (277 lines) does NOT register a `serve` subcommand; registered subcommands are `demo`, `version`, `meldeschein`, `kurtaxe`, `remittance`, `arrival`, `avv`, `rechnung`, `dsgvo`, `predicate` (lines 80-230). Therefore `python -m kurort_engine serve` would error with argparse "invalid choice".
- The operator runbook `docs/ops/docker-compose-deployment.md` documents the server as the live surface (`GET /healthz`, `GET /`).
- Hence the canonical, already-published HTTP entrypoint is `python -m kurort_engine.server`, not `python -m kurort_engine`.

## Acceptance Criteria

<!-- PROTECTED BLOCK BEGIN — DO NOT EDIT; byte-locked against spec.yaml SHA-256 497aa23f07457962c86376bd4bb51b8915369714091258887b81aa1ea786e050 -->

- id: AC-E1
  category: Event-driven
  statement: >-
    When the operator runs the published image (or `docker compose up -d`),
    the container's effective default command MUST invoke the
    `kurort_engine.server` module such that the imported server's
    `serve()` is bound on 0.0.0.0:${PORT:-8080}. The effective command
    MUST NOT be the bare `python -m kurort_engine` invocation that
    triggers the CLI parser's help-and-exit path.
  test_oracle: tests/test_pr3_entrypoint_fix.py::test_e1_dockerfile_cmd_targets_server_module_not_cli_help
  preconditions:
    - "Worker has read repos/KurortEngine/Dockerfile on feature/docker-compose-deployment HEAD (28e93ec) and computed the failure-mode baseline."
    - "Dockerfile CMD is in exec form (a JSON array), so the check is purely textual."

- id: AC-E2
  category: State-driven
  statement: >-
    While the effective command is computed from `compose.yaml` (overrides
    the image's CMD when present), the effective command that
    `docker compose up` would execute MUST resolve to the
    `kurort_engine.server` module. That is: either `compose.yaml` carries
    no `command:` block (in which case the Dockerfile CMD controls) OR
    any `command:` block present MUST itself invoke the
    `kurort_engine.server` module — it MUST NOT re-point the deployed
    command at the CLI-help path.
  test_oracle: tests/test_pr3_entrypoint_fix.py::test_e2_compose_yaml_effective_command_targets_server
  preconditions:
    - "compose.yaml is a YAML document; the test parses it with python stdlib (yaml.safe_load) and inspects the `services.kurort-engine.command` key (if present)."

- id: AC-E3
  category: Event-driven
  statement: >-
    When the same module form the container will use is invoked directly
    in the workspace (`python -m kurort_engine.server` with `PORT`
    pointing at an ephemeral port), the server MUST bind on that port,
    serve `GET /healthz` with HTTP 200 and body `b"ok\n"` (Content-Type
    `text/plain; charset=utf-8`), AND serve `GET /` with HTTP 200 and a
    body that begins with the static-demo banner and contains the
    Reception-Cockpit walk-in artefact's `id="load-marker"` element.
    The server MUST also emit exactly one startup log line on stdout of
    the form `kurort-engine serve: listening on 0.0.0.0:<port> (/healthz, /)`.
  test_oracle: tests/test_pr3_entrypoint_fix.py::test_e3_direct_server_invocation_healthz_and_root
  preconditions:
    - "The test binds the server on 127.0.0.1:<ephemeral port> via a worker thread, probes /healthz and / with stdlib urllib.request, captures stdout, and shuts the server down cleanly."
    - "The test does NOT mock `kurort_engine.server`; it calls the real module."

- id: AC-E4
  category: Unwanted-behavior
  statement: >-
    If the bounded fix touches any of the following, the build is
    INVALID: `.github/workflows/` (any file), the file tree of PR #2's
    commits (`feature/reception-cockpit-functional-walk-in`,
    `0256d6db88bc9c74db4affb5d723dcac964add7d`), the file tree of PR #4's
    commits (`fix/pr2-reception-cockpit-harness-and-browser-proof`
    `bea4c6d148f7dd4ad7b9fd0016c75476030beaa7` /
    `feat/pr4-reception-cockpit-e2e-coverage-follow-up`
    `ddde0f0`), or the protected `main` branch (`origin/main` at
    `439e506`). The fix MUST also stay inside the bounded set of files
    (Dockerfile, compose.yaml, tests/test_pr3_entrypoint_fix.py, and the
    two spec files under spec/pr3_entrypoint_fix/); diff stat on the
    follow-up branch MUST show ≤ 5 changed files.
  test_oracle: tests/test_pr3_entrypoint_fix.py::test_e4_diff_scope_respects_forbidden_edits
  preconditions:
    - "Worker runs `git diff --name-only <base>..HEAD` against the integration base and asserts the file list contains only paths under {(Dockerfile, compose.yaml, tests/test_pr3_entrypoint_fix.py, spec/pr3_entrypoint_fix/*)}."
    - "Worker runs `git rev-parse origin/main` and asserts it equals 439e506."
    - "Worker runs `git rev-parse origin/feature/reception-cockpit-functional-walk-in` and asserts it equals 0256d6db88bc9c74db4affb5d723dcac964add7d."
    - "Worker runs `git rev-parse origin/fix/pr2-reception-cockpit-harness-and-browser-proof` and asserts it equals bea4c6d148f7dd4ad7b9fd0016c75476030beaa7."
    - "Diff-confined assertion runs only on the worker tree if the worker has the follow-up branch checked out; in this sandbox the test asserts the file-list invariant on the staged diff instead."

- id: AC-E5
  category: Ubiquitous
  statement: >-
    The full Python test suite MUST exit 0 with all tests passing
    while the bounded fix is applied. The suite MUST include the
    existing 7 PR #3 tests on `feature/docker-compose-deployment`
    (5 in tests/test_server.py + 2 in tests/test_deployment_artifacts.py)
    AND the new tests/test_pr3_entrypoint_fix.py (4 tests for
    AC-E1..AC-E4). The test command MUST be runnable in the
    container-safe developer workspace (no VM, no container runtime).
  test_oracle: tests/test_pr3_entrypoint_fix.py::test_e5_full_python_test_suite_passes
  preconditions:
    - "Worker runs `python -m pytest tests/ -q` and asserts the exit code is 0 and the summary line contains `passed` (no `failed`, no `error`)."

<!-- PROTECTED BLOCK END — DO NOT EDIT -->

## Traceability matrix

| AC ID | EARS category | Test oracle (will be implemented in phase 2/red) | Status (phase 1) |
|-------|---------------|---------------------------------------------------|------------------|
| AC-E1 | Event-driven          | `tests/test_pr3_entrypoint_fix.py::test_e1_dockerfile_cmd_targets_server_module_not_cli_help` | not_started |
| AC-E2 | State-driven          | `tests/test_pr3_entrypoint_fix.py::test_e2_compose_yaml_effective_command_targets_server`    | not_started |
| AC-E3 | Event-driven          | `tests/test_pr3_entrypoint_fix.py::test_e3_direct_server_invocation_healthz_and_root`        | not_started |
| AC-E4 | Unwanted-behavior     | `tests/test_pr3_entrypoint_fix.py::test_e4_diff_scope_respects_forbidden_edits`              | not_started |
| AC-E5 | Ubiquitous            | `tests/test_pr3_entrypoint_fix.py::test_e5_full_python_test_suite_passes`                    | not_started |

## Notes

- The PROTECTED block above is byte-identical to the AC block in `spec.yaml`. The two SHA-256 values (`Locked spec SHA-256` and `AC block SHA-256`) are recorded both at the top of this file and above the PROTECTED block, and are echoed in the `verify_protected_block.py` companion script.
- The AC block defines 5 acceptance criteria. The spec also carries metadata (`feature`, `intent`, `created`, `job_id`, `owner`, `dependencies`, `out_of_scope`, `bounded_scenario`, `test_oracle_paths`, `done_when`, `limitations`) that lives OUTSIDE the PROTECTED block and is therefore not byte-locked — it is intended for reviewer scanning and will be re-emitted in the integration-phase PR description.
- A repro script (`verify_protected_block.py`) lives on the follow-up branch and can be invoked as `python spec/pr3_entrypoint_fix/verify_protected_block.py` to re-verify the byte-identity on any future commit. This mirrors the existing PR #3 `spec/docker_compose_deployment/verify_protected_block.py` companion.
