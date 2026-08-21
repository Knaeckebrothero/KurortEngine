"""verify_protected_block.py — byte-identity check for PR #3 entrypoint fix spec.

This script re-verifies that the PROTECTED ## Acceptance Criteria block in
spec/pr3_entrypoint_fix/spec_lock.md is byte-identical to the AC block in
spec/pr3_entrypoint_fix/spec.yaml. It mirrors the existing PR #3
spec/docker_compose_deployment/verify_protected_block.py companion.

Run:
    python spec/pr3_entrypoint_fix/verify_protected_block.py
Exit code:
    0 — PROTECTED block byte-identical (PASS)
    1 — PROTECTED block drift detected (FAIL)
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path


# Locked spec.yaml SHA-256 (recorded in spec_lock.md).
EXPECTED_SPEC_SHA = "497aa23f07457962c86376bd4bb51b8915369714091258887b81aa1ea786e050"
EXPECTED_AC_BYTES = 5247
EXPECTED_AC_SHA = "65d5171c4e92f836214c2cabbac3ff2b9a5be9c0d60cc4803aa919ddf8bbe50c"


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPEC_YAML = REPO_ROOT / "spec" / "pr3_entrypoint_fix" / "spec.yaml"
SPEC_LOCK = REPO_ROOT / "spec" / "pr3_entrypoint_fix" / "spec_lock.md"


def _extract_ac_block_from_spec_yaml() -> bytes:
    """Return the AC block bytes from spec.yaml.

    The AC block is the line range between the `## Acceptance criteria (EARS)`
    header and the next top-level `## ` section at column 0. PyYAML is not
    required; the line-slicing is byte-stable because the AC block does not
    contain any YAML re-encoding or round-trip.
    """
    text = SPEC_YAML.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if line.startswith("## Acceptance criteria (EARS)"):
            start_idx = i + 1
        elif start_idx is not None and i > start_idx and line.startswith("## "):
            end_idx = i
            break
    if start_idx is None:
        raise RuntimeError("spec.yaml: '## Acceptance criteria (EARS)' header not found")
    if end_idx is None:
        raise RuntimeError("spec.yaml: no following '## ' section to bound the AC block")
    return "".join(lines[start_idx:end_idx]).encode("utf-8")


def _extract_ac_block_from_spec_lock() -> bytes:
    """Return the AC block bytes from spec_lock.md PROTECTED markers.

    The AC block in spec_lock.md is the verbatim content between the
    `PROTECTED BLOCK BEGIN` marker and the `PROTECTED BLOCK END` marker,
    byte-for-byte (no trimming or re-encoding). The end marker sits on
    its own line immediately after the AC block's final newline, so the
    extracted bytes match the spec.yaml AC block exactly.
    """
    text = SPEC_LOCK.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if "PROTECTED BLOCK BEGIN" in line:
            start_idx = i + 1
        elif start_idx is not None and "PROTECTED BLOCK END" in line:
            end_idx = i
            break
    if start_idx is None or end_idx is None:
        raise RuntimeError("spec_lock.md: PROTECTED BLOCK markers not found")
    # No rstrip / strip — the block must be byte-identical to the spec.yaml AC block.
    return "".join(lines[start_idx:end_idx]).encode("utf-8")


def main() -> int:
    # 1. Verify spec.yaml SHA-256
    spec_bytes = SPEC_YAML.read_bytes()
    spec_sha = hashlib.sha256(spec_bytes).hexdigest()
    if spec_sha != EXPECTED_SPEC_SHA:
        print(
            f"FAIL: spec.yaml SHA-256 mismatch "
            f"(expected {EXPECTED_SPEC_SHA}, got {spec_sha})",
            file=sys.stderr,
        )
        return 1

    # 2. Extract AC block from spec.yaml
    spec_ac_bytes = _extract_ac_block_from_spec_yaml()
    spec_ac_sha = hashlib.sha256(spec_ac_bytes).hexdigest()

    # 3. Extract AC block from spec_lock.md
    lock_ac_bytes = _extract_ac_block_from_spec_lock()
    lock_ac_sha = hashlib.sha256(lock_ac_bytes).hexdigest()

    # 4. Verify byte-identity (raw, no normalisation)
    byte_identity = spec_ac_bytes == lock_ac_bytes

    # 5. Verify expected SHA matches
    sha_match = (
        spec_ac_sha == EXPECTED_AC_SHA and lock_ac_sha == EXPECTED_AC_SHA
    )
    bytes_match = len(spec_ac_bytes) == EXPECTED_AC_BYTES

    print(f"spec.yaml bytes: {len(spec_bytes)}")
    print(f"spec.yaml SHA-256: {spec_sha}")
    print(f"AC block (from spec.yaml) bytes: {len(spec_ac_bytes)}")
    print(f"AC block (from spec.yaml) SHA-256: {spec_ac_sha}")
    print(f"AC block (from spec_lock.md) bytes: {len(lock_ac_bytes)}")
    print(f"AC block (from spec_lock.md) SHA-256: {lock_ac_sha}")
    print(f"EXPECTED AC bytes: {EXPECTED_AC_BYTES}")
    print(f"EXPECTED AC SHA-256: {EXPECTED_AC_SHA}")
    print(f"AC bytes match expected: {bytes_match}")
    print(f"AC SHA matches expected: {sha_match}")
    print(f"BYTE_IDENTITY (AC block raw): {byte_identity}")

    if byte_identity and sha_match and bytes_match:
        print("PROTECTED block byte-identical — PASS")
        return 0
    print("PROTECTED block drift detected (spec.yaml != spec_lock.md) — FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
