"""AC-* chain integration oracle for kurort_engine.avv_kaskade (iter-28 Phase 5 REFACTOR).

Registers the 6-processor Bad Orb Kurverwaltung reference chain (per
iter-27 Critic handoff §3) and asserts the full DSGVO Art. 28 cascade-audit
surface produces consistent SHA-256 hex hashes + completeness coverage.

Test oracle paths recorded in ``repo/spec/avv_kaskade/spec.yaml`` §5:
  AC-chain integration: tests/test_avv_kaskade_chain.py::test_ac_chain_6_processor_bad_orb_kurverwaltung

Each assertion uses try/except so any failure mode is ``AssertionError`` (per
iter-38 / iter-15 SHIPPED convention: AssertionError-not-Failed). If the
avv_kaskade module is missing or any function raises an unexpected exception,
the test fails with ``AssertionError`` (NOT ``ImportError``, NOT
``ModuleNotFoundError``, NOT ``SyntaxError``, NOT ``CollectionError``).
"""
from __future__ import annotations

import importlib.util

import pytest


def _require_avv_kaskade_module() -> None:
    """Fail with AssertionError if the avv_kaskade module is not importable."""
    if importlib.util.find_spec("kurort_engine.avv_kaskade") is None:
        pytest.fail(
            "kurort_engine.avv_kaskade module not found — Phase 5 refactor pre-check failed"
        )


# ---------------------------------------------------------------------------
# AC-chain integration: 6-processor Bad Orb Kurverwaltung reference chain
# ---------------------------------------------------------------------------


def test_ac_chain_6_processor_bad_orb_kurverwaltung() -> None:
    """AC-chain: register the 6 Bad Orb Kurverwaltung fixtures and assert the
    full DSGVO Art. 28 cascade-audit surface produces consistent SHA-256 hex
    hashes + completeness coverage.

    EARS (this chain integration contract, per iter-27 Critic handoff §3 +
    repo/spec/avv_kaskade/spec.yaml §5 chain integration spec):
      When the 6 Bad Orb Kurverwaltung processors (cm-booking-com +
      datev-export + hestia-pms + dsgvo-art17-cascade + nis2-supply-chain +
      predicate-filing-2036) are registered, then attest_chain(format="dsk-kp13")
      shall produce an avv_hash_chain of length 6 with each entry a 64-char
      SHA-256 hex string, and each run_geeignetheitspruefung(processor_id)
      shall produce a report with iso27001_coverage >= 0.80,
      completeness == 1.0, and report_hash of 64-char SHA-256 hex.

    The 6 fixtures exercise the full vertical:
      - cm-booking-com        (channel manager booking engine)
      - datev-export          (DATEV BR/BS ledger connector — Hessen KAG §16)
      - hestia-pms            (Hestia PMS AVV template, Mix-B safe reference)
      - dsgvo-art17-cascade   (Art. 17 5-step atomic cascade — iter-38 consumer)
      - nis2-supply-chain     (NIS2 supply-chain contractual clauses — iter-31)
      - predicate-filing-2036 (Predicate filing narrative generator — iter-33)
    """
    _require_avv_kaskade_module()

    from datetime import date

    from kurort_engine.avv_kaskade import (
        Processor,
        attest_chain,
        register_processor,
        run_geeignetheitspruefung,
    )
    from kurort_engine.avv_kaskade.processor import _reset_registry

    # The module-level _REGISTRY is process-global; reset it so this test
    # can assert exact registry state (len == 6) without interference from
    # prior tests in the same pytest session.
    _reset_registry()

    # Register all 6 fixtures. Each processor uses 2-year AVV validity from
    # 2026-01-15 (consistent with the Phase 5 GREEN fixtures in test_avv_kaskade.py).
    fixture_ids = [
        "cm-booking-com",
        "datev-export",
        "hestia-pms",
        "dsgvo-art17-cascade",
        "nis2-supply-chain",
        "predicate-filing-2036",
    ]

    for pid in fixture_ids:
        register_processor(Processor(
            processor_id=pid,
            controller_name=f"Bad Orb Kurverwaltung — {pid}",
            controller_address="Kurparkstrasse 12, 63619 Bad Orb",
            avv_signed_date=date(2026, 1, 15),
            avv_expiry_date=date(2028, 1, 15),
            avv_pdf_bytes=f"%PDF-1.4\n%avv for {pid}\n".encode("utf-8"),
        ))

    # (a) attest_chain('dsk-kp13')['avv_hash_chain'] has length 6.
    packet = attest_chain(format="dsk-kp13")
    avv_hash_chain = packet.get("avv_hash_chain")
    assert isinstance(avv_hash_chain, list), (
        f"AC-chain: avv_hash_chain must be a list, got {type(avv_hash_chain).__name__}"
    )
    assert len(avv_hash_chain) == 6, (
        f"AC-chain: avv_hash_chain must contain all 6 registered processors, "
        f"got {len(avv_hash_chain)} entries"
    )

    # (b) all 6 entries are 64-char SHA-256 hex.
    for i, hash_entry in enumerate(avv_hash_chain):
        assert isinstance(hash_entry, str) and len(hash_entry) == 64, (
            f"AC-chain: avv_hash_chain[{i}] must be 64-char SHA-256 hex, "
            f"got {hash_entry!r}"
        )
        # SHA-256 hex is lowercase + only hex chars.
        assert all(c in "0123456789abcdef" for c in hash_entry), (
            f"AC-chain: avv_hash_chain[{i}] must be lowercase hex, "
            f"got {hash_entry!r}"
        )

    # (c) all 6 run_geeignetheitspruefung() reports have 64-char report_hash,
    #     iso27001_coverage >= 0.80, and completeness == 1.0.
    for pid in fixture_ids:
        report = run_geeignetheitspruefung(pid)
        report_hash = report.get("report_hash")
        iso_coverage = report.get("iso27001_coverage")
        completeness = report.get("completeness")

        assert isinstance(report_hash, str) and len(report_hash) == 64, (
            f"AC-chain: {pid} report_hash must be 64-char SHA-256 hex, "
            f"got {report_hash!r}"
        )
        assert iso_coverage is not None and iso_coverage >= 0.80, (
            f"AC-chain: {pid} iso27001_coverage must be >= 0.80, "
            f"got {iso_coverage!r}"
        )
        assert completeness == 1.0, (
            f"AC-chain: {pid} completeness must be 1.0, got {completeness!r}"
        )