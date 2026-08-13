"""Iter-28 Phase 1 spec verification script - byte-identity check of the PROTECTED AC block.

Per pinned memory [1] and [2]: the protected block in spec_lock.md must be byte-identical
to the acceptance_criteria block in spec.yaml. Run this script after any update to
either file to verify integrity.
"""
import hashlib
import re
import sys
from pathlib import Path


def main() -> int:
    base = Path(__file__).parent
    spec_yaml = base / "spec.yaml"
    spec_lock = base / "spec.lock.md"

    if not spec_yaml.exists():
        print(f"FAIL: {spec_yaml} not found")
        return 1
    if not spec_lock.exists():
        print(f"FAIL: {spec_lock} not found")
        return 1

    with open(spec_yaml, "rb") as f:
        spec_yaml_bytes = f.read()

    pattern = rb"acceptance_criteria:.*?(?=\nnot_included:|\ndone_when:|\nassumptions:|\Z)"
    m = re.search(pattern, spec_yaml_bytes, re.DOTALL)
    if m is None:
        print("FAIL: AC block not found in spec.yaml")
        return 1
    spec_ac_block = m.group(0).rstrip(b"\n")

    with open(spec_lock, "rb") as f:
        lock_md_bytes = f.read()

    lock_ac_marker = b"acceptance_criteria:\n"
    lock_idx = lock_md_bytes.find(lock_ac_marker)
    if lock_idx == -1:
        print("FAIL: AC block not found in spec.lock.md")
        return 1
    end_marker = b"\n```"
    lock_end = lock_md_bytes.find(end_marker, lock_idx)
    if lock_end == -1:
        print("FAIL: End of fenced block not found in spec.lock.md")
        return 1
    lock_ac_block = lock_md_bytes[lock_idx:lock_end].rstrip(b"\n")

    print(f"spec.yaml AC block length:    {len(spec_ac_block)} bytes")
    print(f"spec.lock.md AC block length: {len(lock_ac_block)} bytes")
    if spec_ac_block == lock_ac_block:
        print("PROTECTED block byte-identity: VERIFIED")
        print(f"AC block SHA-256: {hashlib.sha256(spec_ac_block).hexdigest()}")
        return 0
    print("FAIL: PROTECTED block byte-identity VIOLATED")
    if len(spec_ac_block) != len(lock_ac_block):
        print(f"  length mismatch: spec={len(spec_ac_block)} lock={len(lock_ac_block)}")
    for i, (a, b) in enumerate(zip(spec_ac_block, lock_ac_block)):
        if a != b:
            print(f"  first diff at byte {i}: spec={bytes([a])!r} lock={bytes([b])!r}")
            break
    return 1


if __name__ == "__main__":
    sys.exit(main())
