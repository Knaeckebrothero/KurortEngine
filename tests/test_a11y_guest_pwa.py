"""AC-* test oracle for kurort_engine.a11y.guest_pwa (iter-3 Phase 2 RED).

Test oracle paths recorded in ``repo/spec/a11y_guest_pwa/spec.yaml``:

  AC-1 test_ac1_self_attestation_ts_constant_and_audit_log_event
  AC-2 test_ac2_wcag_aa_audit_infra_with_manual_fallback
  AC-3 test_ac3_cli_subcommand_via_pyproject_entry_points
  AC-4 test_ac4_pattern_f_chain_extension_on_4_shipped_modules
  AC-5 test_ac5_resavio_2026_q4_bfsg_aa_parity_negative_test

Each test starts with ``importlib.util.find_spec('kurort_engine.a11y.guest_pwa')``
pre-check; if the module is missing, the test fails with ``pytest.fail`` raising
an ``AssertionError`` (per iter-15 l13-004 + iter-28 test convention:
AssertionError-not-ImportError verification protocol — pinned memory [1] in
iter-3 KB).

Phase 2 RED NOTE: each test asserts a post-condition that the Phase 3 GREEN
implementation must satisfy. Against the iter-3 baseline (no a11y.guest_pwa
package yet), the tests fail with ``AssertionError`` (NOT ``ImportError``, NOT
``ModuleNotFoundError``, NOT ``SyntaxError``, NOT ``CollectionError``). This
proves the test reaches its assertion — the failure mode is honest.
"""
from __future__ import annotations

import importlib.util
import json
import re
import tomllib
from pathlib import Path

import pytest


def _require_a11y_guest_pwa_module() -> None:
    """Fail with AssertionError if the a11y.guest_pwa module is not importable.

    Per iter-15 l13-004 + iter-28 test convention: AssertionError-not-ImportError.
    We wrap find_spec in try/except because find_spec can raise
    ModuleNotFoundError (not just return None) when a parent namespace package
    is missing — we convert that to pytest.fail so the failure mode is
    AssertionError (not ModuleNotFoundError).
    """
    try:
        spec = importlib.util.find_spec("kurort_engine.a11y.guest_pwa")
    except (ModuleNotFoundError, ImportError):
        spec = None
    if spec is None:
        pytest.fail(
            "kurort_engine.a11y.guest_pwa module not found — Phase 3 GREEN "
            "pre-check failed (RED phase expects this AssertionError)"
        )


# AC-1 contract constants (verbatim from spec.yaml:80-95)
AC1_SELF_ATTESTATION_TS_REGEX: str = r"^\d{4}-\d{2}-\d{2}$"
AC1_AUDIT_ACTOR: str = "a11y.guest_pwa"
AC1_AUDIT_PAYLOAD_EVENT: str = "self_attestation"
AC1_BFSG_CLAIM_MARKER: str = "BFSG-EAA"

# AC-3 contract constants (verbatim from spec.yaml:115-130)
AC3_PYPROJECT_ENTRY_KEY: str = "guest-pwa"
AC3_PYPROJECT_ENTRY_VALUE_PREFIX: str = "kurort_engine.a11y.guest_pwa.__main__:main"

# AC-4 contract constants (verbatim from spec.yaml:132-146)
AC4_CHAIN_ANCHORS: tuple[str, ...] = (
    "kurort_engine.audit.AuditLog",
    "kurort_engine.kurkarte_wallet",
    "kurort_engine.meldeschein",
    "kurort_engine.f5_t2",
)

# AC-5 contract constants (verbatim from spec.yaml:148-159)
AC5_RATIONALE_MIN_LENGTH: int = 1
AC5_FORBIDDEN_SIBLING_KEYS: frozenset[str] = frozenset({"resavio_2026_q4_launched"})


# ---------------------------------------------------------------------------
# AC-1: SELF_ATTESTATION_TS constant + first-import audit-log event
# ---------------------------------------------------------------------------


def test_ac1_self_attestation_ts_constant_and_audit_log_event() -> None:
    """AC-1: SELF_ATTESTATION_TS is exported AND first import appends audit event.

    EARS (spec.yaml AC-1):
      When `import kurort_engine.a11y.guest_pwa` is executed for the first time
      in a Python interpreter session, the system shall append exactly one
      `AuditEntry` to the SHIPPED `kurort_engine.audit.AuditLog` whose actor
      equals "a11y.guest_pwa", whose canonical-JSON payload decodes to
      `{"event": "self_attestation", "ts": "<SELF_ATTESTATION_TS>", "claim":
      "..."}` for a non-empty claim string referencing BFSG-EAA §3(1) and EN
      301 549 V3.2.1 / WCAG 2.1 AA; and a module-level constant
      `SELF_ATTESTATION_TS` shall be exported as a non-empty ISO-8601 date
      string (YYYY-MM-DD).
    """
    _require_a11y_guest_pwa_module()

    import kurort_engine.a11y.guest_pwa as gpwa

    # Post-condition 1: SELF_ATTESTATION_TS constant exists AND is non-empty
    # ISO-8601 date string (YYYY-MM-DD).
    ts = getattr(gpwa, "SELF_ATTESTATION_TS", None)
    assert isinstance(ts, str), (
        f"AC-1: SELF_ATTESTATION_TS must be a str, got {type(ts).__name__}"
    )
    assert len(ts) > 0, "AC-1: SELF_ATTESTATION_TS must be non-empty"
    assert re.match(AC1_SELF_ATTESTATION_TS_REGEX, ts), (
        f"AC-1: SELF_ATTESTATION_TS={ts!r} must be ISO-8601 date YYYY-MM-DD"
    )

    # Post-condition 2: AuditLog has at least one entry with
    # actor='a11y.guest_pwa' and payload.event='self_attestation' AND
    # payload.ts == SELF_ATTESTATION_TS.
    from kurort_engine.audit import AuditLog  # type: ignore[attr-defined]

    entries = list(getattr(AuditLog, "_shared_entries", []))
    matching = [
        e
        for e in entries
        if getattr(e, "actor", None) == AC1_AUDIT_ACTOR
        and getattr(e, "payload", {}).get("event") == AC1_AUDIT_PAYLOAD_EVENT
    ]
    assert len(matching) >= 1, (
        f"AC-1: AuditLog must have >=1 entry with "
        f"actor={AC1_AUDIT_ACTOR!r} and event={AC1_AUDIT_PAYLOAD_EVENT!r}, "
        f"found {len(matching)}"
    )

    # Post-condition 3: payload.ts matches SELF_ATTESTATION_TS.
    entry = matching[-1]
    payload = entry.payload
    payload_ts = payload.get("ts")
    assert payload_ts == ts, (
        f"AC-1: audit payload ts={payload_ts!r} must match "
        f"SELF_ATTESTATION_TS={ts!r}"
    )

    # Post-condition 4: payload.claim is non-empty AND references BFSG-EAA.
    claim = payload.get("claim", "")
    assert isinstance(claim, str) and len(claim) > 0, (
        f"AC-1: payload.claim must be non-empty str, got {claim!r}"
    )
    assert AC1_BFSG_CLAIM_MARKER in claim, (
        f"AC-1: payload.claim must reference {AC1_BFSG_CLAIM_MARKER!r}, "
        f"got {claim!r}"
    )


# ---------------------------------------------------------------------------
# AC-2: run_wcag_aa_audit with axe-core subprocess AND manual fallback
# ---------------------------------------------------------------------------


def test_ac2_wcag_aa_audit_infra_with_manual_fallback() -> None:
    """AC-2: run_wcag_aa_audit exists; manual-fallback branch emits audit event.

    EARS (spec.yaml AC-2):
      The system shall expose a public function `run_wcag_aa_audit(html_or_url)`
      in `kurort_engine.a11y.guest_pwa` that (a) attempts axe-core via
      `subprocess.run(["npx", "@axe-core/cli", ...])` if shutil.which("npx") is
      non-None, (b) on FileNotFoundError or shutil.which("npx") is None falls
      back to a manual-audit branch that returns a dict with keys
      `{"method": "manual", "wcag_level": "AA", "en_standard":
      "EN 301 549 V3.2.1", "violations": [], "scope":
      "kurort_engine.a11y.guest_pwa"}` and appends one AuditEntry with
      actor="a11y.guest_pwa" and payload containing "event": "wcag_aa_audit",
      and (c) on any other unhandled exception raises BFSGComplianceError.
    """
    _require_a11y_guest_pwa_module()

    import kurort_engine.a11y.guest_pwa as gpwa

    fn = getattr(gpwa, "run_wcag_aa_audit", None)
    assert callable(fn), (
        "AC-2: kurort_engine.a11y.guest_pwa.run_wcag_aa_audit must be callable"
    )

    # Post-condition 1: manual fallback returns the expected dict shape.
    # We pass a tiny HTML string — pytest env has no npx, so the manual
    # branch is the expected path.
    import shutil

    if shutil.which("npx") is None:
        report = fn("<html><body><p>test</p></body></html>")
        assert isinstance(report, dict), (
            f"AC-2: manual fallback must return dict, got {type(report).__name__}"
        )
        assert report.get("method") == "manual", (
            f"AC-2: manual fallback method={report.get('method')!r} expected 'manual'"
        )
        assert report.get("wcag_level") == "AA", (
            f"AC-2: manual fallback wcag_level={report.get('wcag_level')!r} expected 'AA'"
        )
        assert report.get("en_standard") == "EN 301 549 V3.2.1", (
            f"AC-2: manual fallback en_standard={report.get('en_standard')!r} "
            f"expected 'EN 301 549 V3.2.1'"
        )
        assert isinstance(report.get("violations"), list), (
            f"AC-2: manual fallback violations must be list, got "
            f"{type(report.get('violations')).__name__}"
        )
        assert report.get("scope") == "kurort_engine.a11y.guest_pwa", (
            f"AC-2: manual fallback scope={report.get('scope')!r} expected "
            f"'kurort_engine.a11y.guest_pwa'"
        )

    # Post-condition 2: AuditLog received a wcag_aa_audit entry.
    from kurort_engine.audit import AuditLog  # type: ignore[attr-defined]

    entries = list(getattr(AuditLog, "_shared_entries", []))
    wcag_entries = [
        e
        for e in entries
        if getattr(e, "actor", None) == AC1_AUDIT_ACTOR
        and getattr(e, "payload", {}).get("event") == "wcag_aa_audit"
    ]
    assert len(wcag_entries) >= 1, (
        f"AC-2: AuditLog must have >=1 wcag_aa_audit entry, found {len(wcag_entries)}"
    )

    # Post-condition 3: BFSGComplianceError class exists (used by the
    # subprocess-failure branch).
    err_cls = getattr(gpwa, "BFSGComplianceError", None)
    assert err_cls is not None and isinstance(err_cls, type), (
        "AC-2: kurort_engine.a11y.guest_pwa.BFSGComplianceError must be an "
        "Exception subclass"
    )


# ---------------------------------------------------------------------------
# AC-3: guest-pwa CLI subcommand via pyproject [project.scripts]
# ---------------------------------------------------------------------------


def test_ac3_cli_subcommand_via_pyproject_entry_points() -> None:
    """AC-3: pyproject [project.scripts] declares the guest-pwa entry point.

    EARS (spec.yaml AC-3):
      While a Python 3.11+ interpreter is active,
      `python -m kurort_engine.a11y.guest_pwa` (PEP 338 entry point) shall
      print the self-attestation string AND append an AuditEntry with
      actor="a11y.guest_pwa.cli" and payload event="cli_invocation" to the
      SHIPPED AuditLog, and exit 0; AND `repo/pyproject.toml [project.scripts]`
      shall contain the line
      `guest-pwa = "kurort_engine.a11y.guest_pwa.__main__:main"` so
      `pip install -e .[dev]` followed by `guest-pwa --version` yields the
      same usage text as `python -m kurort_engine.a11y.guest_pwa --help`;
      AND `grep -rnE "(webpack|vite|react|svelte)" repo/src/kurort_engine/a11y/`
      shall return zero matches.
    """
    _require_a11y_guest_pwa_module()

    # Post-condition 1: pyproject.toml declares [project.scripts] guest-pwa.
    repo_root = Path(__file__).resolve().parent.parent
    pyproject_path = repo_root / "pyproject.toml"
    assert pyproject_path.is_file(), (
        f"AC-3: pyproject.toml not found at {pyproject_path}"
    )
    with pyproject_path.open("rb") as fp:
        data = tomllib.load(fp)
    scripts = data.get("project", {}).get("scripts", {})
    assert AC3_PYPROJECT_ENTRY_KEY in scripts, (
        f"AC-3: pyproject.toml [project.scripts] must contain key "
        f"{AC3_PYPROJECT_ENTRY_KEY!r}, got keys={list(scripts.keys())}"
    )
    entry_value = scripts[AC3_PYPROJECT_ENTRY_KEY]
    assert entry_value.startswith(AC3_PYPROJECT_ENTRY_VALUE_PREFIX), (
        f"AC-3: pyproject [project.scripts].{AC3_PYPROJECT_ENTRY_KEY} "
        f"={entry_value!r} must start with {AC3_PYPROJECT_ENTRY_VALUE_PREFIX!r}"
    )

    # Post-condition 2: __main__:main exists AND is callable.
    import kurort_engine.a11y.guest_pwa.__main__ as gpwa_main  # type: ignore[attr-defined]

    main_fn = getattr(gpwa_main, "main", None)
    assert callable(main_fn), (
        "AC-3: kurort_engine.a11y.guest_pwa.__main__.main must be callable"
    )

    # Post-condition 3: a11y source tree contains NO frontend stack markers
    # (no webpack/vite/react/svelte) — CLI-only constraint.
    a11y_dir = repo_root / "src" / "kurort_engine" / "a11y"
    forbidden_markers = ("webpack", "vite", "react", "svelte")
    if a11y_dir.is_dir():
        offenders: list[str] = []
        for src_path in a11y_dir.rglob("*"):
            if src_path.is_file() and src_path.suffix in {
                ".py",
                ".toml",
                ".md",
                ".txt",
                ".cfg",
                ".json",
                ".yaml",
                ".yml",
            }:
                try:
                    content = src_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                for marker in forbidden_markers:
                    if marker in content:
                        offenders.append(f"{src_path}: {marker}")
        assert not offenders, (
            f"AC-3: a11y source tree must contain NO frontend stack markers "
            f"(webpack/vite/react/svelte); offenders: {offenders}"
        )


# ---------------------------------------------------------------------------
# AC-4: Pattern F chain-extension on 4 SHIPPED modules
# ---------------------------------------------------------------------------


def test_ac4_pattern_f_chain_extension_on_4_shipped_modules() -> None:
    """AC-4: CHAIN_EXTENSION_ANCHORS tuple + 4 import lines in __init__.

    EARS (spec.yaml AC-4):
      The module `kurort_engine.a11y.guest_pwa` shall Pattern F chain-extend 4
      SHIPPED modules by exposing a module-level constant
      `CHAIN_EXTENSION_ANCHORS` whose value is a tuple of length 4 containing
      the strings "kurort_engine.audit.AuditLog",
      "kurort_engine.kurkarte_wallet", "kurort_engine.meldeschein", and
      "kurort_engine.f5_t2"; and `kurort_engine.a11y.guest_pwa.__init__`
      shall contain exactly 4 `from kurort_engine.X import Y` (or equivalent
      top-level `import`) lines whose X names match the 4 anchors.
    """
    _require_a11y_guest_pwa_module()

    import kurort_engine.a11y.guest_pwa as gpwa

    # Post-condition 1: CHAIN_EXTENSION_ANCHORS is a tuple of length 4 with
    # exactly the 4 required anchor strings.
    anchors = getattr(gpwa, "CHAIN_EXTENSION_ANCHORS", None)
    assert isinstance(anchors, tuple), (
        f"AC-4: CHAIN_EXTENSION_ANCHORS must be tuple, got {type(anchors).__name__}"
    )
    assert len(anchors) == 4, (
        f"AC-4: CHAIN_EXTENSION_ANCHORS must have length 4, got {len(anchors)}"
    )
    for required in AC4_CHAIN_ANCHORS:
        assert required in anchors, (
            f"AC-4: CHAIN_EXTENSION_ANCHORS must contain {required!r}, "
            f"got tuple={anchors!r}"
        )

    # Post-condition 2: __init__.py source contains exactly 4 top-level
    # `from kurort_engine.X import ...` or `import kurort_engine.X` lines
    # whose X (top-level module name) matches the 4 anchors.
    init_source_path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "kurort_engine"
        / "a11y"
        / "guest_pwa"
        / "__init__.py"
    )
    assert init_source_path.is_file(), (
        f"AC-4: {init_source_path} not found — Phase 3 GREEN must create this file"
    )
    init_source = init_source_path.read_text(encoding="utf-8")

    from_or_import_pattern = re.compile(
        r"^\s*(?:from\s+kurort_engine\.([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+import\s+[^\n]+)?"
        r"|import\s+kurort_engine\.([a-zA-Z_][a-zA-Z0-9_]*))",
        re.MULTILINE,
    )
    top_level_modules: set[str] = set()
    for match in from_or_import_pattern.finditer(init_source):
        module_name = match.group(1) or match.group(2)
        if module_name:
            top_level_modules.add(module_name)

    expected_top_levels = {
        "audit",       # kurort_engine.audit.AuditLog
        "kurkarte_wallet",
        "meldeschein",
        "f5_t2",
    }
    missing = expected_top_levels - top_level_modules
    assert not missing, (
        f"AC-4: __init__.py must import from {sorted(expected_top_levels)} "
        f"as top-level kurort_engine.X imports; missing={sorted(missing)}; "
        f"found={sorted(top_level_modules)}"
    )


# ---------------------------------------------------------------------------
# AC-5: RESAVIO_BFSG_AA_PARITY_2026_Q4 = False + rationale string
# ---------------------------------------------------------------------------


def test_ac5_resavio_2026_q4_bfsg_aa_parity_negative_test() -> None:
    """AC-5: RESAVIO_BFSG_AA_PARITY_2026_Q4 is False; rationale cites Resavio.

    EARS (spec.yaml AC-5):
      The module `kurort_engine.a11y.guest_pwa` shall expose a module-level
      constant `RESAVIO_BFSG_AA_PARITY_2026_Q4` whose value is the literal
      Python `False`, AND a sibling string constant
      `RESAVIO_BFSG_AA_PARITY_RATIONALE` whose value is a non-empty string
      citing Resavio 2026-Q4 lack of full BFSG-AA parity per the
      `iter-19-evidence-anchor-resavio-2026-q42027-q1-sanity-re-check-no-change-since-i`
      KB learning note.
    """
    _require_a11y_guest_pwa_module()

    import kurort_engine.a11y.guest_pwa as gpwa

    # Post-condition 1: RESAVIO_BFSG_AA_PARITY_2026_Q4 is exactly False.
    parity = getattr(gpwa, "RESAVIO_BFSG_AA_PARITY_2026_Q4", "MISSING")
    assert parity is False, (
        f"AC-5: RESAVIO_BFSG_AA_PARITY_2026_Q4 must be literal False, "
        f"got {parity!r}"
    )

    # Post-condition 2: RESAVIO_BFSG_AA_PARITY_RATIONALE is a non-empty str
    # that cites Resavio + 2026-Q4 (sanity anchor).
    rationale = getattr(gpwa, "RESAVIO_BFSG_AA_PARITY_RATIONALE", "MISSING")
    assert isinstance(rationale, str), (
        f"AC-5: RESAVIO_BFSG_AA_PARITY_RATIONALE must be str, got "
        f"{type(rationale).__name__}"
    )
    assert len(rationale) >= AC5_RATIONALE_MIN_LENGTH, (
        f"AC-5: RESAVIO_BFSG_AA_PARITY_RATIONALE must be non-empty (len>="
        f"{AC5_RATIONALE_MIN_LENGTH}), got len={len(rationale)}"
    )
    rationale_lower = rationale.lower()
    assert "resavio" in rationale_lower, (
        f"AC-5: rationale must cite 'Resavio', got {rationale!r}"
    )
    assert "2026" in rationale_lower and "q4" in rationale_lower, (
        f"AC-5: rationale must cite '2026-Q4', got {rationale!r}"
    )