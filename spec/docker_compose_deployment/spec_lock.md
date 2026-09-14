# spec_lock.md — KurortEngine Docker Compose deployment (job 12a0e92c)
# Phase 1 spec SHIPPED — 2026-08-18

This document locks the `## Acceptance Criteria` section of
`spec/docker_compose_deployment/spec.yaml` verbatim. The block below
(lines 4–25 of `spec.yaml`) MUST be byte-identical to the AC block in
`spec.yaml`. The byte-identity is verified by
`spec/docker_compose_deployment/verify_protected_block.py`.

PROTECTED AC block START — verbatim from spec.yaml lines 4–25
---

acceptance_criteria:
  - id: AC-1
    ears: "Ubiquitous: The kurort_engine HTTP server, when started, shall bind to the socket address (`0.0.0.0`, `${PORT:-8080}`) and accept HTTP/1.1 requests on the routes `/healthz` and `/`; and the server shall not require any environment variable other than `PORT` (default `8080`) to start."
    test_oracle: tests/test_server.py::test_ac1_server_binds_on_port_and_accepts_two_routes
  - id: AC-2
    ears: "Event-driven: When the server receives `GET /healthz`, the server shall respond with status `200 OK`, `Content-Type: text/plain; charset=utf-8`, and body `ok\\n` (exactly two bytes: `o`, `k`, then a newline); and the server shall not emit any other body bytes."
    test_oracle: tests/test_server.py::test_ac2_healthz_returns_200_ok_body
  - id: AC-3
    ears: "Event-driven: When the server receives `GET /`, the server shall respond with status `200 OK`, `Content-Type: text/html; charset=utf-8`, and a body whose first 1024 bytes begin with the static-demo banner prefix containing the literal token `Static demo — published Reception-Cockpit walk-in artefact` and whose remainder contains the canonical marker `id=\"load-marker\"` from the published source artefact `docs/design/reception-cockpit-demo.html`."
    test_oracle: tests/test_server.py::test_ac3_root_serves_labelled_reception_cockpit_artefact
  - id: AC-4
    ears: "State-driven: While the server is running, exactly one startup log line shall be written to stdout of the form `kurort-engine serve: listening on 0.0.0.0:<port> (/healthz, /)` where `<port>` is the actual bound port; and the server shall emit no other stdout/stderr lines during a clean start (no Python traceback, no `DeprecationWarning`)."
    test_oracle: tests/test_server.py::test_ac4_startup_log_line_on_stdout
  - id: AC-5
    ears: "Unwanted-behavior: When the server receives a request whose path is not `/healthz` and not `/` (including `GET /does-not-exist`, `GET /static`, `GET /api/v1/anything`), the server shall respond with status `404 Not Found`, `Content-Type: text/plain; charset=utf-8`, and body `not found\\n`; and the server shall emit no Python traceback to stdout or stderr in any 404 case."
    test_oracle: tests/test_server.py::test_ac5_unknown_route_returns_404_no_traceback
  - id: AC-6
    ears: "Unwanted-behavior: The shipped deployment artifacts shall satisfy four security-and-portability properties simultaneously: (a) `Dockerfile` runs the process as user `app` with UID `65532` (non-root), (b) `compose.yaml` declares no `secrets:` block, (c) the named volume `kurort-engine-data` is mounted at `/var/lib/kurort-engine` inside the container via `compose.yaml`, and (d) the published port mapping is `${PORT:-8080}:8080`."
    test_oracle: tests/test_deployment_artifacts.py::test_ac6_dockerfile_and_compose_yaml_security_constraints
  - id: AC-7
    ears: "State-driven: While the feature branch `feature/docker-compose-deployment` exists in the repository, the shipped delivery contract shall simultaneously satisfy five deployment-hygiene properties: (a) the job artifact `output/kurortengine-deployment-smoke-report.md` exists at the workspace root and contains the branch name, the exact commit SHA, the PR URL, the environment, every verification command with exit code and faithful output, the URLs probed, the logs, the limitations, and clean-tree proof; (b) `.dockerignore` exists at the repository root and excludes `.git`, `.venv`, `tests/`, `__pycache__/`, `*.local.yaml`, `*.secret.yaml`, and at least one entry that prevents the local Python site-packages from being copied into the image; (c) `docs/ops/docker-compose-deployment.md` exists at the repository root and contains an operator runbook with sections for build, start, health probe, human-visible probe, log inspection, and shutdown; (d) the change is committed on a branch whose name is `feature/docker-compose-deployment` (created from current `main` HEAD) and a pull request is open against `main`; (e) the change does NOT depend on or modify the unmerged branch `feature/reception-cockpit-functional-walk-in` (PR #2)."
    test_oracle: tests/test_deployment_artifacts.py::test_ac7_delivery_contract_artifacts

PROTECTED AC block END

---

## Lock metadata

| Field | Value |
|-------|-------|
| spec.yaml path | `spec/docker_compose_deployment/spec.yaml` |
| spec_lock.md path | `spec/docker_compose_deployment/spec_lock.md` |
| verify script | `spec/docker_compose_deployment/verify_protected_block.py` |
| AC block source lines | spec.yaml lines 4–25 (inclusive) |
| Locked AC block byte length | arkose_kurort_docker_compose_ac_block_bytes |
| Locked spec SHA-256 | arkose_kurort_docker_compose_spec_sha256 |
| Locked AC block SHA-256 | arkose_kurort_docker_compose_ac_sha256 |

> NOTE: SHA-256 values are computed at verification time by
> `verify_protected_block.py`. The placeholders above are intentionally
> non-valid SHA-256 strings. The verify script computes the actual SHA-256
> of `spec.yaml` and the AC block, then asserts byte-identity between the
> AC block in `spec.yaml` and the AC block in this `spec_lock.md`.

## Traceability matrix

| AC ID | type | test_oracle | status |
|-------|------|-------------|--------|
| AC-1 | Ubiquitous | tests/test_server.py::test_ac1_server_binds_on_port_and_accepts_two_routes | not_started |
| AC-2 | Event-driven | tests/test_server.py::test_ac2_healthz_returns_200_ok_body | not_started |
| AC-3 | Event-driven | tests/test_server.py::test_ac3_root_serves_labelled_reception_cockpit_artefact | not_started |
| AC-4 | State-driven | tests/test_server.py::test_ac4_startup_log_line_on_stdout | not_started |
| AC-5 | Unwanted-behavior | tests/test_server.py::test_ac5_unknown_route_returns_404_no_traceback | not_started |
| AC-6 | Unwanted-behavior | tests/test_deployment_artifacts.py::test_ac6_dockerfile_and_compose_yaml_security_constraints | not_started |
| AC-7 | State-driven | tests/test_deployment_artifacts.py::test_ac7_delivery_contract_artifacts | not_started |

## Anti-drift guarantee

The PROTECTED AC block above MUST be byte-identical to the
`acceptance_criteria:` section of `spec.yaml` (lines 4–25). The
`verify_protected_block.py` script extracts both blocks and asserts
byte-identity. If the assertion fails, the spec is drifted and must
be re-locked.

## Lock provenance

- Lock written: 2026-08-18
- Locked by: Phase 4 Tactical todo_1 (gate-bounce-3 loop-recovery)
- Source: spec.yaml (63 lines, 7 ACs in EARS format)
- Convention: locked-spec triple (spec.yaml, spec_lock.md, verify_protected_block.py)
- Reference: docs/PROVENANCE.md lines 112–117
