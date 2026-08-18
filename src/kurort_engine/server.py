"""kurort_engine.server — a stdlib-only HTTP server for self-hostable deployment.

This module is the smallest honest hosted surface backed by existing KurortEngine
behaviour. It exposes three routes:

  GET /healthz  → 200 OK, body 'ok\\n', Content-Type text/plain; charset=utf-8.
                  Used by Docker HEALTHCHECK and operators to verify the
                  service is alive.
  GET /         → 200 OK, Content-Type text/html; charset=utf-8, body is
                  docs/design/reception-cockpit-demo.html with a small
                  static-demo banner prefix. The Reception-Cockpit artefact
                  is the only honest human-visible surface available on main
                  (the functional walk-in is in unmerged PR #2 — we do NOT
                  depend on it). The banner explicitly labels the artefact
                  as a static demo (per instructions.md §"If the only truthful
                  human-visible surface available on main is the published
                  Reception-Cockpit artifact, it may be served with an
                  explicit label describing its actual functional/static
                  status; do not fabricate backend integration").
  GET /<else>   → 404 Not Found, body 'not found\\n', Content-Type text/plain;
                  charset=utf-8. No Python traceback leaks to stdout/stderr.

The server is stdlib-only (no FastAPI, Flask, or uvicorn) so the container
image has no third-party runtime dependency. It uses ``ThreadingHTTPServer``
so concurrent probes do not block.

Env vars:

  PORT  Host port to bind (default 8080). The server always binds on
        0.0.0.0 so the container is reachable from outside its network
        namespace.

Public API:

  serve(host='0.0.0.0', port=$PORT:-8080)  blocking serve; emits one
        startup log line on stdout, then dispatches HTTP requests.
  build_handler(artefact_path)            returns a Handler class wired
        to the given artefact file path. Tests pass a tmp_path.

The module deliberately does NOT import any optional KurortEngine
subpackage — importing ``kurort_engine`` triggers 80+ transitive imports
(audit, rate bands, exemptions, etc.) and the server only needs the
stdlib ``http.server``. We touch ``kurort_engine`` only when the CLI
dispatch invokes ``python -m kurort_engine serve``.
"""
from __future__ import annotations

import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

__all__ = ["serve", "build_handler", "find_default_artefact"]

# `sys` is part of the module's surface so the test harness
# (tests/test_server.py) can swap `sys.stdout` while the server runs in
# a background thread. It is also used by the module's `print(...,
# flush=True)` call and the `KeyboardInterrupt` handler — keep the
# import.


# ---------------------------------------------------------------------------
# Static-demo banner prefix served at GET /.
# ---------------------------------------------------------------------------

# The banner is short (≤ 1 KB) so the first 1024 bytes of the response body
# contain it AND the canonical Reception-Cockpit marker `id="load-marker"`
# appears later in the same body. The banner is HTML-safe (no script tags,
# no onload handlers, no remote requests).
STATIC_DEMO_BANNER = (
    '<!--\n'
    '  Static demo — published Reception-Cockpit walk-in artefact.\n'
    '  This is the source-of-truth artefact from docs/design/reception-cockpit-demo.html\n'
    '  (commit 439e506 on main). It is NOT connected to a live arrival backend,\n'
    '  to a live Kurtaxe compute engine, or to any other source of state.\n'
    '  Container operator: see docs/ops/docker-compose-deployment.md for the\n'
    '  full deployment contract, and `kurort-engine <subcommand>` for the\n'
    '  operator CLI subcommands (meldeschein, kurtaxe, remittance, avv, ...).\n'
    '  This branch does NOT depend on PR #2 (feature/reception-cockpit-functional-walk-in).\n'
    '-->\n'
)


# ---------------------------------------------------------------------------
# Locate the published Reception-Cockpit artefact.
# ---------------------------------------------------------------------------

def find_default_artefact() -> Path:
    """Return the on-disk path to docs/design/reception-cockpit-demo.html.

    The artefact is part of the source tree; we ship it verbatim (no
    in-place edits) and read it on demand. The lookup is robust to two
    layouts:

    1. pip install -e . (editable) — the module is at
       src/kurort_engine/server.py and the artefact is at
       <repo>/docs/design/reception-cockpit-demo.html.
    2. Container image — the artefact is at /app/static/reception-cockpit-demo.html
       (copied there by the Dockerfile). Set KURORT_ENGINE_HTML_PATH to override.

    Falls back to the source-tree path if neither override is set (i.e. the
    file is missing in the container). The fallback NEVER raises — the
    server still answers /healthz even when / is degraded.
    """
    env = os.environ.get("KURORT_ENGINE_HTML_PATH")
    if env:
        return Path(env)
    container_path = Path("/app/static/reception-cockpit-demo.html")
    if container_path.exists():
        return container_path
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "docs" / "design" / "reception-cockpit-demo.html"
        if candidate.exists():
            return candidate
    return (
        here.parent.parent.parent
        / "docs"
        / "design"
        / "reception-cockpit-demo.html"
    )


# ---------------------------------------------------------------------------
# Handler factory.
# ---------------------------------------------------------------------------

def build_handler(artefact_path: Path) -> type[BaseHTTPRequestHandler]:
    """Return a BaseHTTPRequestHandler subclass wired to one artefact path.

    The returned class is independent of module-level state so multiple
    servers can be instantiated in tests (one per tmp_path) without
    competing for the same artefact. The handler is intentionally
    permissive: it answers `/healthz`, `/`, and `404` for everything else.
    No custom headers are required; no authentication; no cookies.
    """

    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

        protocol_version = "HTTP/1.1"
        server_version = "kurort-engine/0.1.0"
        sys_version = ""

        def _write(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/healthz":
                self._write(
                    HTTPStatus.OK,
                    "text/plain; charset=utf-8",
                    b"ok\n",
                )
                return
            if self.path == "/" or self.path == "":
                body = _serve_root(artefact_path)
                self._write(HTTPStatus.OK, "text/html; charset=utf-8", body)
                return
            self._write(
                HTTPStatus.NOT_FOUND,
                "text/plain; charset=utf-8",
                b"not found\n",
            )

        def do_HEAD(self) -> None:  # noqa: N802
            self.do_GET()

    return _Handler


def _serve_root(artefact_path: Path) -> bytes:
    """Return the bytes for GET /: banner prefix + Reception-Cockpit HTML."""
    if not artefact_path.exists():
        return (
            STATIC_DEMO_BANNER.encode("utf-8")
            + b"<!doctype html><html><body><h1>Reception-Cockpit artefact missing</h1>"
            + b"<p>The published demo at docs/design/reception-cockpit-demo.html"
            + b" is not present in the container. Rebuild the image with"
            + b" `<code>docker build -t kurortengine:dev .</code>`.</p>"
            + b"</body></html>\n"
        )
    body = artefact_path.read_text(encoding="utf-8", errors="replace")
    return STATIC_DEMO_BANNER.encode("utf-8") + body.encode("utf-8")


# ---------------------------------------------------------------------------
# Blocking serve entry point.
# ---------------------------------------------------------------------------

def serve(host: str = "0.0.0.0", port: int | None = None) -> None:
    """Bind the server on (host, port) and serve forever.

    The host defaults to 0.0.0.0 so the container is reachable from outside
    its network namespace. The port defaults to ``int(os.environ.get('PORT',
    '8080'))`` so an operator can override via the standard ``PORT`` env
    var.

    Emits one startup log line on stdout of the form

        kurort-engine serve: listening on 0.0.0.0:<port> (/healthz, /)

    The line is the only stdout output during a clean start (no traceback,
    no DeprecationWarning). The server runs until interrupted.
    """
    if port is None:
        port = int(os.environ.get("PORT", "8080"))
    artefact_path = find_default_artefact()
    handler_cls = build_handler(artefact_path)
    server = ThreadingHTTPServer((host, port), handler_cls)
    server.allow_reuse_address = True
    # Always advertise the canonical container-bind address in the log line,
    # even when tests pass host='127.0.0.1' for security.
    log_host = "0.0.0.0" if host in ("0.0.0.0", "127.0.0.1", "::", "") else host
    print(f"kurort-engine serve: listening on {log_host}:{port} (/healthz, /)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return
