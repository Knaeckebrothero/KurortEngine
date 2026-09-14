#!/usr/bin/env python3
"""verify_protected_block.py — byte-identity guard for spec_lock.md.

Per the locked-spec convention (see docs/PROVENANCE.md lines 112-117 and the
pinned-discipline notes in the project knowledge base), the PROTECTED AC
block in `spec_lock.md` MUST be byte-identical to the `acceptance_criteria:`
section of `spec.yaml` (lines 4-25 in this spec).

This script:
  1. Reads spec.yaml
  2. Extracts the AC block (lines 4-25, inclusive)
  3. Computes SHA-256 of the full spec.yaml and of the AC block
  4. Reads spec_lock.md
  5. Extracts the AC block from spec_lock.md (between the PROTECTED AC
     block START / END markers)
  6. Asserts byte-identity between the two AC blocks
  7. Prints VERIFIED on success with SHA-256 + byte-length metadata

Exit codes:
  0  byte-identity verified
  1  byte-identity FAILED (drift detected)
  2  file not found or read error
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

SPEC_DIR = Path(__file__).resolve().parent
SPEC_YAML = SPEC_DIR / "spec.yaml"
SPEC_LOCK = SPEC_DIR / "spec_lock.md"

# AC block is spec.yaml lines 4-25 (inclusive): from `acceptance_criteria:`
# through the line before `not_included:`.
AC_BLOCK_START_LINE = 4   # 1-indexed; line 4 is `acceptance_criteria:`
AC_BLOCK_END_LINE = 25    # 1-indexed; line 25 is the AC-7 test_oracle line

# spec_lock.md marker lines
LOCK_START_MARKER = "PROTECTED AC block START"
LOCK_END_MARKER = "PROTECTED AC block END"

# Pinned discipline (per project knowledge base, memory [5]):
# The spec.yaml SHA-256 and byte length are pinned to the known-good baseline.
# The AC block SHA-256 and byte length are computed at verification time and
# must be recorded in spec_lock.md's metadata footer after the first VERIFIED
# run. On every subsequent run, the script re-computes and re-asserts
# byte-identity between spec.yaml's AC block and spec_lock.md's AC block.
EXPECTED_SPEC_SHA = "24abee690c9267d5080f5b6f2796ba04eac8d65a2dd701b82bc793638f4df71a"
EXPECTED_SPEC_BYTES = 9903


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_ac_block_from_spec_yaml(spec_yaml_path: Path) -> bytes:
    """Extract the AC block from spec.yaml as raw bytes (lines 4-25 inclusive)."""
    if not spec_yaml_path.exists():
        print(f"FAIL: {spec_yaml_path} not found", file=sys.stderr)
        sys.exit(2)
    lines = spec_yaml_path.read_text(encoding="utf-8").splitlines(keepends=True)
    # splitlines(keepends=True) preserves \n; lines are 0-indexed but we use 1-indexed ranges
    if len(lines) < AC_BLOCK_END_LINE:
        print(
            f"FAIL: spec.yaml has only {len(lines)} lines, "
            f"expected at least {AC_BLOCK_END_LINE}",
            file=sys.stderr,
        )
        sys.exit(2)
    # Lines 4..25 inclusive (1-indexed) = indices 3..24 (0-indexed)
    block_lines = lines[AC_BLOCK_START_LINE - 1 : AC_BLOCK_END_LINE]
    return b"".join(line.encode("utf-8") for line in block_lines)


def extract_ac_block_from_spec_lock(spec_lock_path: Path) -> bytes:
    """Extract the AC block from spec_lock.md between the START/END markers."""
    if not spec_lock_path.exists():
        print(f"FAIL: {spec_lock_path} not found", file=sys.stderr)
        sys.exit(2)
    text = spec_lock_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if LOCK_START_MARKER in line:
            start_idx = i + 1  # line AFTER the marker
        elif LOCK_END_MARKER in line and start_idx is not None:
            end_idx = i  # line BEFORE the marker
            break
    if start_idx is None or end_idx is None:
        print(
            f"FAIL: spec_lock.md missing PROTECTED AC block markers "
            f"({LOCK_START_MARKER!r} / {LOCK_END_MARKER!r})",
            file=sys.stderr,
        )
        sys.exit(1)
    block_lines = lines[start_idx:end_idx]
    return b"".join(line.encode("utf-8") for line in block_lines)


def main() -> int:
    # Step 1-2: extract AC block from spec.yaml
    ac_from_yaml = extract_ac_block_from_spec_yaml(SPEC_YAML)
    spec_yaml_bytes = SPEC_YAML.read_bytes()
    spec_sha = sha256_of_bytes(spec_yaml_bytes)
    ac_sha = sha256_of_bytes(ac_from_yaml)
    ac_len = len(ac_from_yaml)

    # Step 3-4: extract AC block from spec_lock.md
    ac_from_lock = extract_ac_block_from_spec_lock(SPEC_LOCK)

    # Step 5: assert byte-identity
    if ac_from_yaml != ac_from_lock:
        print("FAIL: PROTECTED block drift detected (spec.yaml != spec_lock.md)", file=sys.stderr)
        print(f"  spec.yaml AC block: {len(ac_from_yaml)} bytes, SHA-256 {sha256_of_bytes(ac_from_yaml)}", file=sys.stderr)
        print(f"  spec_lock.md AC block: {len(ac_from_lock)} bytes, SHA-256 {sha256_of_bytes(ac_from_lock)}", file=sys.stderr)
        return 1

    # Step 6: print VERIFIED with metadata
    print("VERIFIED: PROTECTED block byte-identical between spec.yaml and spec_lock.md")
    print(f"  spec.yaml SHA-256:          {spec_sha}")
    print(f"  AC block SHA-256:           {ac_sha}")
    print(f"  AC block byte length:       {ac_len}")
    print(f"  spec.yaml byte length:      {len(spec_yaml_bytes)}")
    print(f"  spec.yaml path:             {SPEC_YAML}")
    print(f"  spec_lock.md path:          {SPEC_LOCK}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
