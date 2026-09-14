"""RED tests for the KurortEngine stdlib HTTP server (AC-1..AC-5).

Test_oracle paths recorded in `spec/docker_compose_deployment/spec.yaml`
and `spec_lock.md`. Each test exercises an acceptance criterion that
ships in `src/kurort_engine/server.py` (GREEN phase). In the RED phase,
the tests fail with `AssertionError` (NOT ImportError, NOT
CollectionError, NOT pytest.skip) because the server module does not
yet exist.

Coverage map (7 ACs total; AC-6 + AC-7 live in tests/test_deployment_artifacts.py):

  AC-1  Ubiquitous: bind on (0.0.0.0, ${PORT:-8080}) and accept /healthz + /.
  AC-2  Event-driven: GET /healthz → 200 OK, body 'ok\n', text/plain charset.
  AC-3  Event-driven: GET /       → 200 OK, banner + Reception-Cockpit marker.
  AC-4  State-driven: exactly one startup log line on stdout.
  AC-5  Unwanted-behavior: GET /<other> → 404 'not found\n', no traceback.
"""
from __future__ import annotations

import socket
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

import pytest


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


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _skip_if_no_server():
    """Return the server module if it exists, else raise AssertionError.

    The red-phase discipline: tests must fail with AssertionError, not
    ImportError. If the module is missing, raises AssertionError with a
    diagnostic pointing at the GREEN-phase todo.
    """
    try:
        import kurort_engine.server as srv_mod  # noqa: F401
    except ImportError as exc:
        raise AssertionError(
            f"RED phase: src/kurort_engine/server.py is not implemented yet "
            f"({exc}). GREEN phase must provide it."
        ) from exc
    return srv_mod


@contextmanager
def _serve(tee: list[str]) -> Iterator[tuple[str, int]]:
    """Start the server on a free port in a background thread."""
    srv_mod = _skip_if_no_server()
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


class _HttpResponse:
    def __init__(self, status: int, content: bytes, headers: dict[str, str]) -> None:
        self.status = status
        self.content = content
        self.headers = headers

    @property
    def body(self) -> str:
        return self.content.decode("utf-8", errors="replace")


def _http_get(host: str, port: int, path: str, timeout: float = 2.0) -> _HttpResponse:
    conn = socket.create_connection((host, port), timeout=timeout)
    try:
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Connection: close\r\n"
            f"User-Agent: kurortengine-test-server/1.0\r\n"
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
    return _HttpResponse(status, body, headers)


# ---------------------------------------------------------------------------
# AC-1 — Ubiquitous: bind on (0.0.0.0, ${PORT:-8080}) and accept /healthz + /.
# ---------------------------------------------------------------------------

def test_ac1_server_binds_on_port_and_accepts_two_routes() -> None:
    """The server binds on 0.0.0.0 (reachable as 127.0.0.1) and accepts /healthz + /."""
    tee: list[str] = []
    with _serve(tee) as (host, port):
        h = _http_get(host, port, "/healthz")
        r = _http_get(host, port, "/")
        assert h.status == 200, f"/healthz status {h.status} != 200"
        assert r.status == 200, f"/ status {r.status} != 200"


# ---------------------------------------------------------------------------
# AC-2 — Event-driven: GET /healthz → 200 OK, body 'ok\n', text/plain charset.
# ---------------------------------------------------------------------------

def test_ac2_healthz_returns_200_ok_body() -> None:
    """GET /healthz → 200 OK, Content-Type text/plain; charset=utf-8, body 'ok\\n'."""
    tee: list[str] = []
    with _serve(tee) as (host, port):
        resp = _http_get(host, port, "/healthz")
        assert resp.status == 200, f"status {resp.status} != 200"
        assert resp.body == "ok\n", f"body {resp.body!r} != 'ok\\n'"
        ct = resp.headers.get("content-type", "")
        assert "text/plain" in ct, f"Content-Type {ct!r} missing text/plain"
        assert "charset=utf-8" in ct, f"Content-Type {ct!r} missing charset=utf-8"


# ---------------------------------------------------------------------------
# AC-3 — Event-driven: GET / → 200 OK, banner + Reception-Cockpit marker.
# ---------------------------------------------------------------------------

def test_ac3_root_serves_labelled_reception_cockpit_artefact() -> None:
    """GET / → 200 OK, Content-Type text/html, banner prefix + Reception-Cockpit marker."""
    tee: list[str] = []
    with _serve(tee) as (host, port):
        resp = _http_get(host, port, "/")
        assert resp.status == 200, f"status {resp.status} != 200"
        ct = resp.headers.get("content-type", "")
        assert "text/html" in ct, f"Content-Type {ct!r} missing text/html"
        assert "charset=utf-8" in ct, f"Content-Type {ct!r} missing charset=utf-8"
        prefix = resp.body[:1024]
        assert "Static demo" in prefix, "first 1024 bytes missing the 'Static demo' banner prefix"
        assert "Reception-Cockpit" in prefix, "first 1024 bytes missing 'Reception-Cockpit' label"
        assert 'id="load-marker"' in resp.body, "body missing canonical Reception-Cockpit marker"


# ---------------------------------------------------------------------------
# AC-4 — State-driven: exactly one startup log line on stdout.
# ---------------------------------------------------------------------------

def test_ac4_startup_log_line_on_stdout() -> None:
    """While the server is running, exactly one startup log line is written.

    The line MUST match `kurort-engine serve: listening on 0.0.0.0:<port> (/healthz, /)`.
    """
    tee: list[str] = []
    with _serve(tee) as (host, port):
        joined = "".join(tee)
        expected = f"kurort-engine serve: listening on 0.0.0.0:{port} (/healthz, /)"
        assert expected in joined, (
            f"missing startup log line; expected {expected!r}; got {joined!r}"
        )
        assert "Traceback" not in joined, f"unexpected traceback in stdout: {joined!r}"
        assert "DeprecationWarning" not in joined, f"unexpected warning in stdout: {joined!r}"


# ---------------------------------------------------------------------------
# AC-5 — Unwanted-behavior: GET /<other> → 404 'not found\n', no traceback.
# ---------------------------------------------------------------------------

def test_ac5_unknown_route_returns_404_no_traceback() -> None:
    """GET /does-not-exist (and others) returns 404 'not found\\n' with no Python traceback."""
    tee: list[str] = []
    with _serve(tee) as (host, port):
        for path in ("/does-not-exist", "/static", "/api/v1/anything", "/healthcheck"):
            resp = _http_get(host, port, path)
            assert resp.status == 404, f"GET {path} status {resp.status} != 404"
            assert resp.body == "not found\n", \
                f"GET {path} body {resp.body!r} != 'not found\\n'"
            ct = resp.headers.get("content-type", "")
            assert "text/plain" in ct, f"GET {path} Content-Type {ct!r} missing text/plain"
        joined = "".join(tee)
        assert "Traceback" not in joined, f"unexpected traceback in stdout: {joined!r}"
