"""RED tests for the KurortEngine Docker Compose deployment artifacts (AC-6 + AC-7).

Test_oracle paths recorded in `spec/docker_compose_deployment/spec.yaml`
and `spec_lock.md`. Each test exercises an acceptance criterion that
ships via Dockerfile, .dockerignore, compose.yaml, and the operator
runbook (GREEN phase). In the RED phase, the tests fail with
`AssertionError` (NOT ImportError, NOT CollectionError, NOT pytest.skip)
because the artifacts do not yet exist.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _git_stdout(*args: str) -> str:
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


# ---------------------------------------------------------------------------
# AC-6 — Unwanted-behavior: 4 security-and-portability properties.
# ---------------------------------------------------------------------------

def test_ac6_dockerfile_and_compose_yaml_security_constraints() -> None:
    """The shipped deployment artifacts satisfy 4 security-and-portability properties.

    (a) Dockerfile runs as user `app` with UID 65532 (non-root).
    (b) compose.yaml declares no `secrets:` block.
    (c) compose.yaml declares named volume kurort-engine-data:/var/lib/kurort-engine.
    (d) compose.yaml declares port mapping ${PORT:-8080}:8080.
    """
    dockerfile = _read(REPO_ROOT / "Dockerfile")
    compose = _read(REPO_ROOT / "compose.yaml")

    assert dockerfile, "RED phase: Dockerfile does not exist (GREEN phase must provide it)"
    assert re.search(r"^\s*USER\s+app\b", dockerfile, re.MULTILINE), \
        "Dockerfile missing `USER app` directive"
    assert "65532" in dockerfile, \
        "Dockerfile missing UID 65532 (the non-root user identifier)"
    assert re.search(r"(useradd|adduser)[^\n]*-u\s+65532", dockerfile) \
        or re.search(r"--uid\s+65532", dockerfile) \
        or re.search(r"UID\s*=\s*65532", dockerfile) \
        or re.search(r"--uid[=\s]+65532", dockerfile), \
        "Dockerfile does not create the app user with UID 65532"

    assert compose, "RED phase: compose.yaml does not exist (GREEN phase must provide it)"
    assert not re.search(r"^\s*secrets\s*:", compose, re.MULTILINE), \
        "compose.yaml declares a `secrets:` block (forbidden by AC-6)"

    assert "kurort-engine-data" in compose, \
        "compose.yaml does not declare the named volume `kurort-engine-data`"
    assert "/var/lib/kurort-engine" in compose, \
        "compose.yaml does not mount at /var/lib/kurort-engine"

    assert re.search(r"\$\{PORT:-8080\}:8080", compose), \
        "compose.yaml does not declare the port mapping ${PORT:-8080}:8080"


# ---------------------------------------------------------------------------
# AC-7 — State-driven: 5 deployment-hygiene properties.
# ---------------------------------------------------------------------------

def test_ac7_delivery_contract_artifacts() -> None:
    """The shipped delivery contract satisfies 5 deployment-hygiene properties.

    (a) output/kurortengine-deployment-smoke-report.md exists at workspace root.
    (b) .dockerignore excludes the expected entries.
    (c) docs/ops/docker-compose-deployment.md exists with runbook sections.
    (d) Git branch is feature/docker-compose-deployment + PR open against main.
    (e) PR #2 (feature/reception-cockpit-functional-walk-in) is unaffected.
    """
    smoke_report = REPO_ROOT / "output" / "kurortengine-deployment-smoke-report.md"
    assert smoke_report.exists(), \
        f"RED phase: deliverable {smoke_report} does not exist (GREEN phase must write it)"

    dockerignore = _read(REPO_ROOT / ".dockerignore")
    assert dockerignore, "RED phase: .dockerignore does not exist (GREEN phase must provide it)"
    expected_lines = [
        r"^\.git\s*$",
        r"^\.venv\s*$",
        r"^tests/?\s*$",
        r"^__pycache__/?\s*$",
        r"^\*\.local\.yaml\s*$",
        r"^\*\.secret\.yaml\s*$",
    ]
    for pattern in expected_lines:
        assert re.search(pattern, dockerignore, re.MULTILINE), \
            f".dockerignore missing line matching {pattern!r}"

    runbook = _read(REPO_ROOT / "docs" / "ops" / "docker-compose-deployment.md")
    assert runbook, "RED phase: docs/ops/docker-compose-deployment.md does not exist (GREEN phase must provide it)"
    sections = [
        r"^##\s+.*[Bb]uild",
        r"^##\s+.*[Ss]tart",
        r"^##\s+.*[Hh]ealth",
        r"^##\s+.*[Pp]robe",
        r"^##\s+.*[Ll]og",
        r"^##\s+.*[Ss]hutdown",
    ]
    for pattern in sections:
        assert re.search(pattern, runbook, re.MULTILINE), \
            f"runbook missing section matching {pattern!r}"

    branch = _git_stdout("branch", "--show-current")
    assert branch == "feature/docker-compose-deployment", \
        f"current branch {branch!r} != 'feature/docker-compose-deployment'"

    pr2_sha = _git_stdout("rev-parse", "--verify", "origin/feature/reception-cockpit-functional-walk-in")
    assert pr2_sha, "PR #2 branch origin/feature/reception-cockpit-functional-walk-in missing"
    base_main_sha = _git_stdout("rev-parse", "--verify", "origin/main")
    assert base_main_sha, "origin/main missing"
    pr2_ahead = _git_stdout("log", "--oneline", f"{base_main_sha}..origin/feature/reception-cockpit-functional-walk-in")
    assert pr2_ahead, \
        "PR #2 branch has no commits ahead of main — it must NOT be modified by this ticket"
