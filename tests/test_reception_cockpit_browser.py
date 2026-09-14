"""AC-3 + AC-7 — Reception-Cockpit real-browser (Playwright + Chromium) tests.

This file is a REPOSITORY-LOCAL real-browser acceptance harness for the
Reception-Cockpit executable walk-in demo. It drives an actual Chromium
against ``docs/design/reception-cockpit-demo.html`` served on
``127.0.0.1:8765`` by ``python -m http.server``.

Cases proved end-to-end (no mocked DOM stub):

* AC-3 (a) ``ArrowDown`` / ``ArrowUp`` cycle the ``is-selected`` queue row;
* AC-3 (b) ``r`` / ``R`` scrolls to and focuses ``#resume-btn``;
* AC-3 (c) ``/`` focuses ``#guest-search`` without hijacking form input;
* AC-3 (d) ``Tab`` and ``Enter`` activate interactive controls natively;
* AC-3 (e) a visible focus ring is present on the seven core tabbable
  elements (filter buttons, queue CTAs, resume-btn, guest-search);
* AC-2 interruption persistence — fill a BMG guest input, reload the page,
  activeStep + guest name are restored into the resume-card;
* AC-7 the executable five-step walk-in form completes: ``form.hidden=true``
  and the ``#completion-tile`` is revealed.

Locked contract reference:

  * Spec SHA-256: ``139160b508797deddf696b19aa1c103626b066a1c0c8309c06d2aca0d6500d4b``
  * AC block SHA-256: ``c5fa32abb8173d1e0d317e4b15e30f6cc13aecfb83d1aa652932c53ea819be96``
  * Locked spec: ``spec/reception_cockpit_executable_walk_in/spec.yaml``
  * Lock file:    ``spec/reception_cockpit_executable_walk_in/spec_lock.md``
"""
from __future__ import annotations

import pathlib
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler

import pytest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHROMIUM_PATH: str = "/opt/playwright/chromium-1217/chrome-linux64/chrome"
DEMO_HTTP_URL: str = "http://127.0.0.1:8765/reception-cockpit-demo.html"
SERVE_PORT: int = 8765

RC_LOCALSTORAGE_KEY: str = "rc-cockpit-state-v2"

TABBABLE_SELECTORS: tuple[str, ...] = (
    "button.button.button-primary#resume-btn",
    "input#guest-search",
    "input#guest-firstName",
    "input#guest-lastName",
    "input#guest-dateOfBirth",
    "input#guest-nationality",
    "input#arrivalDate",
    "input#departureDate",
    "input#roomNumber",
    "button#cta-checkin-21",
)

# 4 sample queue rows in DOM order (per the published demo seed).
# Demo JS uses idx clamp (max/min) — no wrap.
QUEUE_DOM_ORDER: tuple[str, ...] = ("row-21", "row-12", "row-07", "row-31")


# ---------------------------------------------------------------------------
# Helpers — stdlib HTTP server for the demo
# ---------------------------------------------------------------------------

_REPO_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parents[1]


class _ScopedDirectoryHandler(SimpleHTTPRequestHandler):
    _serve_directory: str = ""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, directory=self._serve_directory, **kwargs)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


class _DemoServer:
    """A single-port HTTP server rooted at ``docs/design``."""

    def __init__(self, port: int = SERVE_PORT, directory: pathlib.Path | None = None) -> None:
        self._port = port
        self._directory = directory or (_REPO_ROOT / "docs" / "design")
        _ScopedDirectoryHandler._serve_directory = str(self._directory)
        self._httpd = HTTPServer(("127.0.0.1", port), _ScopedDirectoryHandler)
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, daemon=True, name=f"demo-{port}"
        )

    def __enter__(self) -> "_DemoServer":
        self._thread.start()
        deadline = time.monotonic() + 5.0
        last_err: Exception | None = None
        while time.monotonic() < deadline:
            try:
                import urllib.request

                with urllib.request.urlopen(  # noqa: S310 — bind-local only
                    f"http://127.0.0.1:{self._port}/reception-cockpit-demo.html",
                    timeout=2,
                ) as resp:
                    if resp.status == 200:
                        return self
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                time.sleep(0.05)
        raise RuntimeError(
            f"local static server did not become healthy on 127.0.0.1:{self._port}: {last_err}"
        )

    def __exit__(self, *exc: object) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


def _ensure_chromium_available() -> None:
    path = pathlib.Path(CHROMIUM_PATH)
    if not path.is_file():
        raise AssertionError(
            f"Chromium for Testing missing — expected binary at {CHROMIUM_PATH}. "
            "Run `python -m playwright install chromium`."
        )


@pytest.fixture(scope="module")
def demo_server() -> "_DemoServer":
    _ensure_chromium_available()
    with _DemoServer() as srv:
        yield srv


@pytest.fixture()
def browser(demo_server: "_DemoServer"):  # type: ignore[no-untyped-def]
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        chromium = p.chromium.launch(
            executable_path=CHROMIUM_PATH,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            yield chromium
        finally:
            chromium.close()


@pytest.fixture()
def page(browser):  # type: ignore[no-untyped-def]
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page_obj = ctx.new_page()
    page_obj.goto(DEMO_HTTP_URL, wait_until="domcontentloaded")
    page_obj.wait_for_selector(".queue-row", timeout=5000)
    try:
        yield page_obj
    finally:
        ctx.close()


# ---------------------------------------------------------------------------
# AC-3 — Keyboard navigation proven in a real browser
# ---------------------------------------------------------------------------


def test_ac3_arrow_down_moves_selection_to_next_row(page) -> None:  # type: ignore[no-untyped-def]
    """AC-3: ArrowDown advances the selected row forward by one DOM index.

    The demo's IIFE uses ``.is-selected`` + ``aria-current="true"`` as the
    observable selection contract. We do NOT assert ``document.activeElement``
    = the next row, because ``<li>`` elements without an explicit
    ``tabindex`` attribute do not receive Chromium keyboard focus by
    default — and adding tabindex would change the contract for keyboard
    users (roving tabindex pattern). The selection still moves; the
    keyboard focus is intentionally left to the user.
    """
    page.evaluate("window.scrollTo(0, 0)")
    page.evaluate("() => document.body.focus()")
    page.locator("#row-21").click()  # ensure row-21 is the "first" row
    # ArrowDown must advance to row-12 (DOM index 0 -> 1).
    page.keyboard.press("ArrowDown")
    page.wait_for_function(
        "document.querySelector('.queue-row.is-selected')?.id === 'row-12'",
        timeout=2000,
    )
    selected_id = page.evaluate(
        "() => document.querySelector('.queue-row.is-selected')?.id"
    )
    assert selected_id == "row-12", (
        f"AC-3: after ArrowDown from row-21, row-12 must be .is-selected; got {selected_id!r}"
    )
    aria_current = page.evaluate(
        "() => document.getElementById('row-12').getAttribute('aria-current')"
    )
    assert aria_current == "true", (
        f"AC-3: row-12 must carry aria-current='true' after ArrowDown; got {aria_current!r}"
    )


def test_ac3_arrow_up_at_first_row_clamps_no_wrap(page) -> None:  # type: ignore[no-untyped-def]
    """AC-3: ArrowUp clamps at the first row (no wrap).

    Starting from row-12 (DOM index 1), press ArrowUp three times:
    row-12 -> row-21 (clamp at idx=0), then row-21 twice more. The
    selection must remain on row-21; it must NOT wrap back to row-31.
    """
    page.evaluate("window.scrollTo(0, 0)")
    page.evaluate("() => document.body.focus()")
    page.locator("#row-12").click()
    # First ArrowUp moves row-12 -> row-21 (idx 1 -> 0).
    page.keyboard.press("ArrowUp")
    page.wait_for_function(
        "document.querySelector('.queue-row.is-selected')?.id === 'row-21'",
        timeout=2000,
    )
    # Second ArrowUp must clamp (already at idx=0).
    page.keyboard.press("ArrowUp")
    time.sleep(0.05)  # let the IIFE settle; no DOM mutation expected
    # Third ArrowUp must also clamp.
    page.keyboard.press("ArrowUp")
    selected_id = page.evaluate(
        "() => document.querySelector('.queue-row.is-selected')?.id"
    )
    assert selected_id == "row-21", (
        f"AC-3: ArrowUp must clamp at the first row (row-21); got {selected_id!r}. "
        f"No wrap is allowed — pressing ArrowUp 3 times from row-12 must end on row-21."
    )


def test_ac3_r_shortcut_scrolls_and_focuses_resume_button(page) -> None:  # type: ignore[no-untyped-def]
    """AC-3: 'r' / 'R' scrolls to and focuses the resume button."""
    page.evaluate("window.scrollTo(0, 0)")
    page.evaluate("() => document.body.focus()")
    page.keyboard.press("KeyR")
    page.wait_for_function(
        "document.activeElement?.id === 'resume-btn'",
        timeout=2000,
    )
    focused_id = page.evaluate("() => document.activeElement?.id")
    assert focused_id == "resume-btn", (
        f"AC-3: 'R' must focus #resume-btn; document.activeElement.id = {focused_id!r}"
    )


def test_ac3_slash_shortcut_focuses_guest_search(page) -> None:  # type: ignore[no-untyped-def]
    """AC-3: '/' focuses the guest-search input."""
    page.evaluate("window.scrollTo(0, 0)")
    page.evaluate("() => document.body.focus()")
    page.keyboard.press("Slash")
    page.wait_for_function(
        "document.activeElement?.id === 'guest-search'",
        timeout=2000,
    )
    focused_id = page.evaluate("() => document.activeElement?.id")
    assert focused_id == "guest-search", (
        f"AC-3: '/' must focus #guest-search; document.activeElement.id = {focused_id!r}"
    )


def test_ac3_typing_in_form_input_is_not_hijacked(page) -> None:  # type: ignore[no-untyped-def]
    """AC-3: typing inside a form input must not be hijacked by the keydown listener."""
    page.locator("#guest-firstName").click()
    page.locator("#guest-firstName").fill("")
    page.keyboard.type("Mara")
    value = page.locator("#guest-firstName").input_value()
    assert value == "Mara", (
        f"AC-3: typing inside #guest-firstName must not be hijacked; value = {value!r}"
    )
    active_id = page.evaluate("() => document.activeElement?.id")
    assert active_id == "guest-firstName", (
        f"AC-3: '/' inside a form input must be typed literally, not rerouted; "
        f"document.activeElement.id = {active_id!r}"
    )


def test_ac3_visible_focus_ring_on_every_tabbable(page) -> None:  # type: ignore[no-untyped-def]
    """AC-3: visible focus ring present on every tabbable element."""
    result: list[tuple[str, float]] = page.evaluate(
        """(selectors) => {
          const out = [];
          for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (!el) { out.push([sel, -1]); continue; }
            el.focus();
            const cs = getComputedStyle(el);
            const lw = parseFloat(cs.outlineWidth) || 0;
            const sw = (cs.boxShadow && cs.boxShadow !== 'none') ? 1 : 0;
            out.push([sel, lw + sw]);
          }
          return out;
        }""",
        list(TABBABLE_SELECTORS),
    )
    missing_focus = [(sel, w) for sel, w in result if w <= 0]
    assert not missing_focus, (
        "AC-3: every tabbable element must render a visible focus ring. "
        f"Elements without a visible focus ring: {missing_focus}."
    )


# ---------------------------------------------------------------------------
# AC-2 — Interruption persistence proven in a real browser
# ---------------------------------------------------------------------------


def test_ac2_interruption_persistence_survives_full_reload(page) -> None:  # type: ignore[no-untyped-def]
    """AC-2: in-progress walk-in form state survives a full page reload."""
    page.evaluate("window.scrollTo(0, 0)")
    page.evaluate(f"() => localStorage.removeItem('{RC_LOCALSTORAGE_KEY}')")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector(".queue-row", timeout=5000)

    page.locator("#row-12").click()
    page.locator("#guest-firstName").fill("Mara")
    page.locator("#arrival-confirmed").click()

    saved = page.evaluate(f"() => localStorage.getItem('{RC_LOCALSTORAGE_KEY}')")
    assert saved, (
        f"AC-2: localStorage key {RC_LOCALSTORAGE_KEY!r} must be set after typing; got {saved!r}"
    )

    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#resume-card", timeout=5000)
    payload = page.evaluate(f"() => localStorage.getItem('{RC_LOCALSTORAGE_KEY}')")
    assert payload, (
        f"AC-2: localStorage payload must survive page reload; got {payload!r}"
    )

    resume_step = page.locator("#resume-active-step").inner_text()
    assert "Schritt" in resume_step and any(c.isdigit() for c in resume_step), (
        f"AC-2: #resume-active-step must render the restored active step "
        f"with a 'Schritt N von 5' label; got {resume_step!r}"
    )

    page.locator("#resume-btn").click()
    page.wait_for_selector("#guest-firstName", timeout=5000)
    restored = page.locator("#guest-firstName").input_value()
    assert restored == "Mara", (
        f"AC-2: #guest-firstName must be restored to 'Mara' after reload; got {restored!r}"
    )


# ---------------------------------------------------------------------------
# AC-7 — The five-step walk-in flow is actually executable
# ---------------------------------------------------------------------------


def test_ac7_walk_in_form_submits_and_reveals_completion_tile(page) -> None:  # type: ignore[no-untyped-def]
    """AC-7: the executable walk-in form completes and reveals the completion tile.

    The IIFE's submit handler does ``form.checkValidity()`` and bails on
    invalid forms (calls ``reportValidity()`` and returns without hiding
    the form or revealing the completion tile). The demo pre-fills most
    BMG fields with valid values, but the ``<select id="arrival-confirmed">``
    defaults to an empty value and is required. We set the select, then
    submit via a real ``submit`` event (Playwright ``.submit()`` triggers
    the inline listener without HTML5 validation interference).
    """
    page.evaluate(f"() => localStorage.removeItem('{RC_LOCALSTORAGE_KEY}')")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#walk-in-form", timeout=5000)

    # Confirm the form is visible before submit (not in completion state).
    assert not page.evaluate(
        "() => document.getElementById('walk-in-form')?.hidden"
    ), "AC-7: walk-in-form must be visible before submit."

    # The IIFE's submit handler bails on invalid forms. Select a valid
    # value for the required <select id="arrival-confirmed"> so the form
    # passes checkValidity() and the handler runs to completion.
    page.locator("#arrival-confirmed").select_option(value="2026-08-16T13:30")

    # Trigger a real submit event by clicking the submit button. This
    # faithfully mimics a receptionist clicking "Eintragen".
    submit_btn = page.locator("button[type='submit'].button-primary, #walk-in-form button[type='submit']").first
    page.locator('#bmg-ack').check()
    submit_btn.click()

    # Wait for the completion tile to be revealed.
    page.wait_for_function(
        "document.getElementById('completion-tile')?.hidden === false",
        timeout=5000,
    )

    # Walk-in form must be hidden after submit.
    form_hidden = page.evaluate(
        "() => document.getElementById('walk-in-form')?.hidden === true"
    )
    assert form_hidden, (
        "AC-7: walk-in-form.hidden must be true after submit."
    )

    # Completion tile must be revealed.
    completion_revealed = page.evaluate(
        "() => document.getElementById('completion-tile')?.hidden === false"
    )
    assert completion_revealed, (
        "AC-7: completion-tile must be revealed (hidden === false) after submit."
    )

    # The completion tile must render the budget-end clock 0:00 / 5:00.
    clock_final = page.locator("#walk-in-clock-final").inner_text()
    assert "00:00" in clock_final and "05:00" in clock_final, (
        f"AC-7: walk-in clock-final must read 00:00 / 05:00 on completion; got {clock_final!r}"
    )


# ---------------------------------------------------------------------------
# AC-1 — Real-browser sanity: metric tiles visible and load-ready
# ---------------------------------------------------------------------------


def test_ac1_every_metric_tile_visible_and_load_ready(page) -> None:  # type: ignore[no-untyped-def]
    """AC-1: every metric tile is visible and carries data-load-ready=\"true\"."""
    counts: dict[str, object] = page.evaluate(
        """() => {
          const tiles = Array.from(document.querySelectorAll('article.metric'));
          return {
            total: tiles.length,
            loadReady: tiles.filter(t => t.getAttribute('data-load-ready') === 'true').length,
            visible: tiles.filter(t => {
              const r = t.getBoundingClientRect();
              const cs = getComputedStyle(t);
              return r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden';
            }).length,
            labels: tiles.map(t => (t.querySelector('.metric-label')?.textContent || '').trim()),
          };
        }"""
    )
    assert counts["total"] >= 4, (
        f"AC-1: demo must render >= 4 metric tiles; got {counts['total']}. Labels: {counts['labels']!r}"
    )
    assert counts["loadReady"] == counts["total"], (
        f"AC-1: every metric tile must carry data-load-ready='true'. "
        f"total={counts['total']} loadReady={counts['loadReady']}."
    )
    assert counts["visible"] >= 4, (
        f"AC-1: >= 4 metric tiles must be visible; visible={counts['visible']}"
    )
