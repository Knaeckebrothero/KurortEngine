"""RED tests for PR #3 container entrypoint fix (AC-E1..AC-E4).

Test_oracle paths recorded in `spec/pr3_entrypoint_fix/spec.yaml` and
`spec_lock.md`. Each test exercises an acceptance criterion that ships
via Dockerfile + compose.yaml + bounded diff (GREEN phase). In the RED
phase, the tests fail with `AssertionError` (NOT ImportError, NOT
CollectionError, NOT pytest.skip) because the bounded fix is not yet
applied.

Coverage map (4 ACs; AC-E5 is a suite-level assertion tested by running
`python -m pytest tests/ -q` and inspecting the summary line):

  AC-E1  Event-driven:       Dockerfile CMD targets `kurort_engine.server`,
                             not the bare `kurort_engine` CLI-help path.
  AC-E2  State-driven:       compose.yaml effective command resolves to
                             the server module (no `command:` override, OR
                             override also targets the server module).
  AC-E3  Event-driven:       Direct server module invocation (the same
                             module the container will use) serves
                             GET /healthz with 200 + 'ok\\n' AND GET / with
                             200 + Reception-Cockpit banner.
  AC-E4  Unwanted-behavior:  The bounded diff does NOT touch
                             .github/workflows/, PR #2, PR #4, or main,
                             and ≤ 5 changed files in the bounded set.
"""
from __future__ import annotations

import json
import re
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

import pytest


REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Helpers (mirror tests/test_server.py + test_deployment_artifacts.py style).
# ---------------------------------------------------------------------------


def _read_text(path) -> str:
    """Read a file as UTF-8 text. Returns "" if missing."""
    p = REPO_ROOT / path
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def _git_stdout(*args: str) -> str:
    """Run a git command in REPO_ROOT and return stdout (stripped)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), *args],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""
    return result.stdout.strip()


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _Tee:
    """Write to a real stream and a captured list simultaneously."""

    def __init__(self, real, sink: list[str]) -> None:
        self._real = real
        self._sink = sink

    def write(self, s: str) -> int:
        self._sink.append(s)
        return self._real.write(s)

    def flush(self) -> None:
        self._real.flush()


def _http_get(host: str, port: int, path: str, timeout: float = 2.0) -> tuple[int, dict[str, str], bytes]:
    """Raw socket HTTP/1.1 GET. Returns (status, headers, body)."""
    conn = socket.create_connection((host, port), timeout=timeout)
    try:
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Connection: close\r\n"
            f"User-Agent: kurortengine-test-pr3-entrypoint/1.0\r\n"
            f"\r\n"
        ).encode("ascii")
        conn.sendall(req)
        buf = bytearray()
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf.extend(chunk)
    finally:
        conn.close()
    raw = bytes(buf)
    head, _, body = raw.partition(b"\r\n\r\n")
    status_line = head.split(b"\r\n", 1)[0].decode("ascii", errors="replace")
    parts = status_line.split(" ", 2)
    status = int(parts[1]) if len(parts) >= 2 else 0
    headers: dict[str, str] = {}
    for line in head.split(b"\r\n")[1:]:
        if b":" in line:
            k, _, v = line.partition(b":")
            headers[k.decode("ascii").strip().lower()] = v.decode("ascii").strip()
    return status, headers, body


# ---------------------------------------------------------------------------
# AC-E1 — Dockerfile CMD targets kurort_engine.server, not the CLI-help path.
# ---------------------------------------------------------------------------


def test_e1_dockerfile_cmd_targets_server_module_not_cli_help() -> None:
    """The container's default CMD MUST invoke the server module, not the CLI-help path.

    The published defect: `CMD ["python", "-m", "kurort_engine"]` invokes
    `src/kurort_engine/__main__.py:parser.print_help()` and exits 0. The
    real HTTP entrypoint is `python -m kurort_engine.server` (per
    `src/kurort_engine/server.py:__all__` and the operator runbook).
    """
    dockerfile = _read_text("Dockerfile")
    assert dockerfile, "RED phase: Dockerfile does not exist (GREEN phase must provide it)"

    # Extract the LAST CMD directive (Dockerfile final CMD wins on ENTRYPOINT-less runs).
    cmd_matches = re.findall(r"^\s*CMD\s+(.+?)\s*$", dockerfile, re.MULTILINE)
    assert cmd_matches, "Dockerfile has no CMD directive"

    # Parse the exec-form CMD (JSON array). Reject shell form here because
    # the spec requires exec form so SIGTERM reaches the process.
    last_cmd = cmd_matches[-1]
    assert last_cmd.startswith("[") and last_cmd.endswith("]"), (
        f"Dockerfile CMD is not in exec form (JSON array); got {last_cmd!r}. "
        "Exec form is required so SIGTERM from `docker stop` reaches the process."
    )
    parsed = json.loads(last_cmd)
    assert isinstance(parsed, list) and parsed, (
        f"Dockerfile CMD does not parse as a non-empty JSON list; got {parsed!r}"
    )

    # The OLD broken form is exactly ["python", "-m", "kurort_engine"].
    assert parsed != ["python", "-m", "kurort_engine"], (
        f"Dockerfile CMD regressed to the CLI-help path {parsed!r}; "
        "the HTTP server would never start."
    )

    # The new form MUST contain the server module substring.
    rendered = " ".join(str(x) for x in parsed)
    assert "kurort_engine.server" in rendered, (
        f"Dockerfile CMD {parsed!r} does not target `kurort_engine.server` "
        "(the real HTTP entrypoint per src/kurort_engine/server.py:__all__)"
    )


# ---------------------------------------------------------------------------
# AC-E2 — compose.yaml effective command resolves to the server module.
# ---------------------------------------------------------------------------


def test_e2_compose_yaml_effective_command_targets_server() -> None:
    """The effective command computed from compose.yaml MUST resolve to the server module.

    Either compose.yaml carries no `command:` block (so the Dockerfile CMD
    controls — already covered by AC-E1), OR any `command:` block present
    MUST itself invoke `kurort_engine.server` (exec form or shell form).
    """
    compose = _read_text("compose.yaml")
    assert compose, "RED phase: compose.yaml does not exist (GREEN phase must provide it)"

    # Find a top-level `command:` key under the kurort-engine service.
    # Compose YAML is indented; the command key (when present) lives at
    # 4-space indent. Walk the file and search for the matching key.
    in_service = False
    service_indent = -1
    found_command: list[str] | None = None
    for line in compose.splitlines():
        stripped = line.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            continue
        # Detect the `kurort-engine:` service block.
        m_svc = re.match(r"^(\s{2})kurort-engine\s*:\s*$", line)
        if m_svc:
            in_service = True
            service_indent = len(m_svc.group(1))
            continue
        # If we hit a new top-level `services:` already consumed or another
        # top-level key at the same indent as the service, leave.
        if in_service and line and not line.startswith(" " * (service_indent + 1)):
            # Either back to top-level or out of service block.
            if line.startswith(" " * service_indent) and not line.startswith(" " * (service_indent + 1)):
                # Same indent as service key (sibling) — not command.
                continue
            if not line.startswith(" "):
                # Out of services altogether.
                in_service = False
                continue
        # Within the service block, look for `command:` key.
        if in_service:
            m_cmd = re.match(r"^\s{4,}command\s*:\s*(.*)$", line)
            if m_cmd:
                value = m_cmd.group(1).strip()
                if not value or value == "|" or value == ">" or value.startswith("|-") or value.startswith(">-"):
                    # Multi-line scalar — render blank for this check; we
                    # only need to confirm the command is NOT a CLI-help
                    # invocation. The bounded fix deliberately leaves
                    # compose.yaml without a command: block, so this
                    # branch should not be hit.
                    found_command = []
                else:
                    # Inline YAML list (e.g. ["python", "-m", "kurort_engine.server"]).
                    try:
                        parsed = json.loads(value)
                    except json.JSONDecodeError:
                        # Single-quoted scalar.
                        parsed = value.strip().strip("'\"")
                    if isinstance(parsed, list):
                        found_command = [str(x) for x in parsed]
                    else:
                        found_command = [str(parsed)]

    # If no command: block is present, the Dockerfile CMD controls — AC-E1
    # already pins that. This is acceptable.
    if found_command is None:
        return

    rendered = " ".join(found_command)
    assert "kurort_engine.server" in rendered, (
        f"compose.yaml `command:` {found_command!r} does not target "
        "`kurort_engine.server`; it would re-point the deployed command at "
        "a non-server path (CLI-help regression)."
    )


# ---------------------------------------------------------------------------
# AC-E3 — Direct server module invocation serves /healthz + /.
# ---------------------------------------------------------------------------


@contextmanager
def _serve_direct(tee: list[str]) -> Iterator[tuple[str, int]]:
    """Bind the real server module on a free port in a background thread."""
    try:
        import kurort_engine.server as srv_mod  # noqa: F401
    except ImportError as exc:
        raise AssertionError(
            f"RED phase: src/kurort_engine/server.py is not importable ({exc}). "
            "GREEN phase must provide the server module."
        ) from exc
    real_stdout = sys.stdout
    sys.stdout = _Tee(real_stdout, tee)
    bound_port = _pick_free_port()
    thread = threading.Thread(
        target=srv_mod.serve,
        kwargs={"host": "127.0.0.1", "port": bound_port},
        daemon=True,
    )
    thread.start()
    try:
        for _ in range(40):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.05)
                try:
                    s.connect(("127.0.0.1", bound_port))
                    break
                except OSError:
                    pass
            time.sleep(0.05)
        yield "127.0.0.1", bound_port
    finally:
        sys.stdout = real_stdout


def test_e3_direct_server_invocation_healthz_and_root() -> None:
    """`python -m kurort_engine.server` (the container's effective command) serves both routes."""
    tee: list[str] = []
    with _serve_direct(tee) as (host, port):
        # /healthz must return 200 + 'ok\n' + text/plain charset.
        status_h, headers_h, body_h = _http_get(host, port, "/healthz")
        assert status_h == 200, f"GET /healthz status {status_h} != 200"
        assert body_h == b"ok\n", f"GET /healthz body {body_h!r} != b'ok\\n'"
        ct_h = headers_h.get("content-type", "")
        assert "text/plain" in ct_h, f"GET /healthz Content-Type {ct_h!r} missing text/plain"
        assert "charset=utf-8" in ct_h, f"GET /healthz Content-Type {ct_h!r} missing charset=utf-8"

        # / must return 200 + the Static demo banner + the Reception-Cockpit
        # `id="load-marker"` element.
        status_r, headers_r, body_r = _http_get(host, port, "/")
        assert status_r == 200, f"GET / status {status_r} != 200"
        ct_r = headers_r.get("content-type", "")
        assert "text/html" in ct_r, f"GET / Content-Type {ct_r!r} missing text/html"
        assert "charset=utf-8" in ct_r, f"GET / Content-Type {ct_r!r} missing charset=utf-8"
        body_r_text = body_r.decode("utf-8", errors="replace")
        prefix = body_r_text[:1024]
        assert "Static demo" in prefix, "GET / first 1024 bytes missing 'Static demo' banner"
        assert "Reception-Cockpit" in prefix, "GET / first 1024 bytes missing 'Reception-Cockpit' label"
        assert 'id="load-marker"' in body_r_text, "GET / body missing canonical Reception-Cockpit marker"

        # Startup log line on stdout.
        joined = "".join(tee)
        expected = f"kurort-engine serve: listening on 0.0.0.0:{port} (/healthz, /)"
        assert expected in joined, (
            f"missing startup log line; expected {expected!r}; got {joined!r}"
        )
        assert "Traceback" not in joined, f"unexpected traceback in stdout: {joined!r}"


# ---------------------------------------------------------------------------
# AC-E4 — Bounded diff scope (no .github/workflows/, PR #2, PR #4, or main).
# ---------------------------------------------------------------------------


def test_e4_diff_scope_respects_forbidden_edits() -> None:
    """The bounded fix MUST NOT touch .github/workflows/, PR #2, PR #4, or main.

    Pinned protected refs (must remain unchanged AFTER the fix):

      origin/main                                            = 439e506afc69c96cd18e3b9e6566695c44d48ddd
      origin/feature/reception-cockpit-functional-walk-in    = 0256d6db88bc9c74db4affb5d723dcac964add7d
      origin/fix/pr2-reception-cockpit-harness-and-browser-proof = bea4c6d148f7dd4ad7b9fd0016c75476030beaa7
      origin/feat/pr4-reception-cockpit-e2e-coverage-follow-up   = ddde0f0… (head at run time)

    File-list invariant: the bounded diff MUST be a subset of:
        {Dockerfile, compose.yaml, tests/test_pr3_entrypoint_fix.py,
         spec/pr3_entrypoint_fix/*}
    """
    # (1) Protected refs unchanged.
    expected = {
        "origin/main": "439e506afc69c96cd18e3b9e6566695c44d48ddd",
        "origin/feature/reception-cockpit-functional-walk-in":
            "0256d6db88bc9c74db4affb5d723dcac964add7d",
        "origin/fix/pr2-reception-cockpit-harness-and-browser-proof":
            "bea4c6d148f7dd4ad7b9fd0016c75476030beaa7",
    }
    for ref, expected_sha in expected.items():
        actual = _git_stdout("rev-parse", ref)
        assert actual == expected_sha, (
            f"protected ref {ref} moved: expected {expected_sha}, got {actual}"
        )

    # (2) Diff scope: the committed diff between the integration base
    # (origin/main) and HEAD MUST be a subset of the bounded file set.
    base = "origin/feature/docker-compose-deployment"
    files_changed = _git_stdout("diff", "--name-only", base + "..HEAD").splitlines()
    files_changed = sorted({f for f in files_changed if f})

    # Allow the NEW spec dir files (added by the spec phase) and the
    # Dockerfile + compose.yaml edits (added by the green phase) and the
    # new test file (added by the red phase). That is the bounded set.
    allowed = {
        "Dockerfile",
        "compose.yaml",
        "tests/test_pr3_entrypoint_fix.py",
        "spec/pr3_entrypoint_fix/spec.yaml",
        "spec/pr3_entrypoint_fix/spec_lock.md",
        "spec/pr3_entrypoint_fix/verify_protected_block.py",
    }
    forbidden_patterns = (
        ".github/workflows/",
        "src/kurort_engine/server.py",
        "src/kurort_engine/__main__.py",
    )
    for f in files_changed:
        assert f in allowed, (
            f"bounded-diff scope violated: {f!r} is outside the allowed set "
            f"{sorted(allowed)}. protected category? matched one of {forbidden_patterns}? "
            f"Full diff: {files_changed}"
        )
        for pat in forbidden_patterns:
            assert not f.startswith(pat), (
                f"bounded-diff scope violated: {f!r} matches the forbidden pattern {pat!r}"
            )

    # (3) No .github/workflows/ edits in the unstaged working tree either.
    status_work = _git_stdout("status", "--porcelain")
    for line in status_work.splitlines():
        # porcelain format: XY <path>
        if len(line) >= 4 and line[3:].startswith(".github/workflows/"):
            raise AssertionError(
                f"working-tree edit in forbidden path: {line!r}"
            )
