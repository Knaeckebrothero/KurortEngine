# Docker Compose deployment — operator runbook

This runbook is the operator-side companion to the Docker Compose deployment of
KurortEngine. It documents the smallest set of commands an operator needs to
bring the service up, probe it, inspect it, and shut it down — and the honest
deployment contract that ships with it.

**Audience:** operators with shell access on a small server. No prior
KurortEngine knowledge required.

**Honesty note (read first):** KurortEngine is a working CLI for Meldeschein,
Kurtaxe, and related operator subcommands. The **containerized hosted surface**
is a stdlib-only HTTP server that serves:

  * `GET /healthz` → `200 OK`, body `ok\n` (used by Docker `HEALTHCHECK`)
  * `GET /`        → `200 OK`, the published `docs/design/reception-cockpit-demo.html`
                     with a banner prefix that labels it as a static demo
  * `GET /<other>` → `404 Not Found`, body `not found\n`

The container does **not** expose the CLI subcommands over HTTP, does **not**
re-implement the operator workflows, and does **not** have a live arrival
backend. The published Reception-Cockpit walk-in is the only honest
human-visible surface on `main`; the functional walk-in lives in
`feature/reception-cockpit-functional-walk-in` (PR #2) and is intentionally
**not** part of this deployment.

---

## Build

Build the image from the repository root:

```sh
docker build -t kurortengine:dev .
```

The image is `python:3.11-slim`-based, runs as user `app` with UID `65532`
(non-root), and contains the stdlib-only `src/kurort_engine/server.py` plus
the published `docs/design/reception-cockpit-demo.html` artefact. No secrets,
no external runtime network dependency.

---

## Start

Bring the service up with Docker Compose:

```sh
docker compose up -d
```

The default published port is `8080`. Override with `PORT`:

```sh
PORT=9000 docker compose up -d
```

The container binds `0.0.0.0:8080` (or `$PORT`) inside its network namespace;
Docker Compose maps it to the host on the same port. Logs land in the default
`docker compose logs` stream.

---

## Health probe

`/healthz` is the liveness/readiness endpoint. It returns `200 OK` with body
`ok\n` whenever the server is up. The Docker Compose file declares a
`healthcheck` that probes this endpoint every 10 seconds.

```sh
# Direct probe
curl -fsS http://localhost:${PORT:-8080}/healthz
# → ok

# Compose health status
docker compose ps
# → STATUS column shows "Up (healthy)" once the first probe succeeds
```

The probe uses only the Python stdlib (`urllib.request`) so no extra
packages are pulled into the image.

---

## Human-visible probe

`GET /` returns the published Reception-Cockpit walk-in artefact with a
banner prefix that labels it as a static demo:

```sh
curl -fsS http://localhost:${PORT:-8080}/ | head -n 20
# → begins with the static-demo banner, then the published HTML
```

Any other path returns `404 Not Found` with body `not found\n` and no
traceback leak:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:${PORT:-8080}/does-not-exist
# → 404
```

---

## Log inspection

The server emits exactly one startup log line on stdout of the form
`kurort-engine serve: listening on 0.0.0.0:<port> (/healthz, /)`. The
container does not emit tracebacks or deprecation warnings during a clean
start.

```sh
# Tail all logs
docker compose logs -f kurort-engine

# First 100 lines (includes the startup log line)
docker compose logs kurort-engine | head -n 100
```

For audit purposes, capture the full log to a file:

```sh
docker compose logs kurort-engine > /var/log/kurort-engine.log
```

---

## Shutdown

Stop and remove the container, and remove the named volume if you want a
clean slate:

```sh
# Stop and remove the container (keeps the named volume)
docker compose down

# Stop, remove the container, AND remove the named volume
docker compose down -v
```

The image is preserved on disk; rerun `docker compose up -d` to bring the
service back. To remove the image too:

```sh
docker rmi kurortengine:dev
```

---

## Limitations and NOT VERIFIED annotations

**This runbook was authored and the artifacts were built in a sandbox
without Docker / Compose available.** The following checks were executed
locally (non-Docker evidence) and PASSED:

  1. `py_compile src/kurort_engine/server.py` → exit 0
  2. `pytest tests/test_server.py tests/test_deployment_artifacts.py` → 7 passed, 0 failed
  3. Direct local-server smoke: `GET /healthz` → `ok`, `GET /` → static-demo
     banner + Reception-Cockpit marker, `GET /does-not-exist` → `404`
  4. `git rev-parse origin/feature/reception-cockpit-functional-walk-in`
     unchanged (PR #2 untouched)

**The following checks were NOT executed on this sandbox** because the
`docker` binary and container runtime are absent (the sandbox is a
Kubernetes pod without a container-in-container runtime):

  * `docker build -t kurortengine:dev .` — NOT VERIFIED
  * `docker compose up -d` — NOT VERIFIED
  * `docker compose ps` (health status) — NOT VERIFIED
  * `docker compose logs kurort-engine` — NOT VERIFIED
  * `docker compose down` — NOT VERIFIED

Operators running this on a host with Docker / Compose should expect the
containerized check list to pass; the Dockerfile, `compose.yaml`,
`.dockerignore`, and server module are designed to satisfy the spec's
`done_when` contract (see `spec/docker_compose_deployment/spec.yaml` lines 41–52).

---

## Security notes

  * The container runs as UID `65532`, a fixed high non-root UID. No
    password, no home directory, no interactive shell.
  * No `secrets:` block in `compose.yaml`. No `environment:` block with
    secret values. The only operator knob is the `PORT` env var.
  * The named volume `kurort-engine-data` is mounted at
    `/var/lib/kurort-engine` for future persistent state. The current
    static-demo service writes nothing there.
  * The image is stdlib-only at runtime; `pip install` happens at build
    time and the pip cache is not preserved in the final image.

---

## See also

  * `spec/docker_compose_deployment/spec.yaml` — the acceptance criteria
  * `spec/docker_compose_deployment/spec_lock.md` — the locked AC block
    and traceability matrix
  * `src/kurort_engine/server.py` — the stdlib-only HTTP server
  * `tests/test_server.py` — RED tests for AC-1..AC-5
  * `tests/test_deployment_artifacts.py` — RED tests for AC-6 + AC-7
  * `output/kurortengine-deployment-smoke-report.md` — the local smoke
    evidence and the NOT-VERIFIED annotation
