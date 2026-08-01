# Repro 003: compute_anti_drift_sha's BFSGComplianceError message lists 6 SHIPPED modules that the
# function does NOT actually read (only 4 predicate_filing modules are SHA'd).
#
# Run: pytest output/repros/003_anti_drift_sha_misleading_diagnostic.py -v
# Expected: this test should pass after the bug is fixed.
#
# Bug: error message accuracy. The diagnostic at kurort_engine.predicate_filing.2026_attestation.py
# lines 248-256 says:
#     "The 6 SHIPPED modules (esg + esg.report + kurpaket_orchestrator + kurkarte_wallet + spa_wellness +
#      ev_charging) AND the iter-33 SHIPPED predicate_filing MUST remain verbatim UNCHANGED."
# but the function only iterates over `_ITER33_CHAIN_EXTENSION_MODULES` (4 modules: predicate_packet_assembler,
# kurgaste_health_data_aggregator, heilbad_2036_narrative_generator, predicate_filing_export). The 6
# anti-drift SHAs (esg/__init__.py, esg/report/__init__.py, kurpaket_orchestrator.py, kurkarte_wallet/__init__.py,
# spa_wellness/__init__.py, ev_charging/__init__.py) are NOT in the SHA envelope. So if any of the 6 SHAs
# drift, the SHA might still match (they're not in the envelope) — the anti-drift check passes — and
# the error message is misleading when the drift is in those 6 modules.
"""Repro 003 — anti-drift SHA diagnostic message mentions modules not actually checked."""

from __future__ import annotations

import os
import re

import pytest

from kurort_engine.predicate_filing import compute_anti_drift_sha


# Module path (resolved via env-relative, since the file may be checked out
# at either /home/agent-host/workspace/repo/src or relative to CWD).
def _resolve_module_source() -> str:
    candidates = [
        "repo/src/kurort_engine/predicate_filing/2026_attestation.py",
        "src/kurort_engine/predicate_filing/2026_attestation.py",
        "/home/agent-host/workspace/repo/src/kurort_engine/predicate_filing/2026_attestation.py",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    raise FileNotFoundError(f"Could not locate 2026_attestation.py; tried {candidates!r}")


def test_repro_003_diagnostic_lists_only_modules_actually_shaed() -> None:
    """The BFSGComplianceError message lists 6 modules the function does NOT check."""
    from kurort_engine.kurkarte_wallet import BFSGComplianceError

    profile = {"attestation_template_id": "bad_orb_2026_v1",
               "satzung_date": "2026-07-01",
               "bundesland": "hessen", "kurort": "bad_orb"}

    # Read the source of 2026_attestation.py to identify the actual SHA envelope modules
    src_path = _resolve_module_source()
    with open(src_path) as fh:
        src = fh.read()

    m_iter33 = re.search(
        r"_ITER33_CHAIN_EXTENSION_MODULES\s*:\s*tuple\[str,\s*\.\.\.\]\s*=\s*\(([^)]+)\)",
        src,
        re.DOTALL,
    )
    assert m_iter33 is not None, (
        f"Could not locate _ITER33_CHAIN_EXTENSION_MODULES in {src_path}"
    )
    listed_in_tuple = tuple(
        s.strip().strip('"').strip("'")
        for s in m_iter33.group(1).split(",")
        if s.strip()
    )

    # Trigger the anti-drift error
    with pytest.raises(BFSGComplianceError) as excinfo:
        compute_anti_drift_sha(profile, baseline_sha="0" * 64)
    msg = str(excinfo.value)
    msg_low = msg.lower()

    # Per the AC-4 contract (spec.yaml PROTECTED AC-4): the function MUST use
    # `kurort_engine.predicate_filing` chain-extension modules in the SHA
    # envelope. The diagnostic message MUST be consistent with the actual envelope.
    #
    # The shipped error message explicitly names these 6 modules:
    #   esg, esg.report, kurpaket_orchestrator, kurkarte_wallet, spa_wellness,
    #   ev_charging.
    # It also says "the iter-33 SHIPPED predicate_filing".
    # But the actual SHA envelope contains only:
    claimed_modules = ("esg", "esg.report", "kurpaket_orchestrator",
                       "kurkarte_wallet", "spa_wellness", "ev_charging")
    inaccurately_claimed = [name for name in claimed_modules if name in msg_low]

    # Modules not actually in the SHA envelope:
    inaccurately_claimed_unlisted = [
        name for name in inaccurately_claimed
        if not any(name in mod for mod in listed_in_tuple)
    ]

    assert not inaccurately_claimed_unlisted, (
        f"BUG: anti-drift diagnostic message references modules the function "
        f"does NOT actually SHA. The actual SHA envelope contains only "
        f"{listed_in_tuple!r}, but the error message claims to verify: "
        f"{inaccurately_claimed_unlisted!r}. The 6 SHAs are protected by the "
        f"anti-drift discipline at the *git-diff* level (per iter-30 SHIPPED "
        f"foundation verify ritual) — they are NOT in the runtime SHA envelope "
        f"of compute_anti_drift_sha. So the diagnostic message is misleading "
        f"and would send an operator on a wild-goose chase to inspect modules "
        f"that are not actually checked at runtime.\n"
        f"Full message:\n  {msg!r}"
    )
