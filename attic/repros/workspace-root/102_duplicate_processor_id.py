"""Repro 102 — conflicting registrations share one stable processor ID.

Run from the workspace root:
    PYTHONPATH=repo/src repo/.venv/bin/pytest \
        output/repros/102_duplicate_processor_id.py -v

The test is intentionally RED on shipped code. A correct implementation may
reject the conflicting second registration or expose only one unambiguous
active/attested record for the stable ID.
"""

from __future__ import annotations

from datetime import date

import pytest

from kurort_engine.avv_kaskade import Processor, attest_chain, register_processor
from kurort_engine.avv_kaskade.processor import _reset_registry


@pytest.fixture(autouse=True)
def isolated_avv_registry():
    _reset_registry()
    yield
    _reset_registry()


def test_repro_102_conflicting_duplicate_processor_id_is_not_ambiguous() -> None:
    stable_id = "repro-102-duplicate-vendor"
    first = Processor(
        processor_id=stable_id,
        controller_name="Controller Alpha GmbH",
        controller_address="Alphaweg 1",
        avv_signed_date=date(2026, 1, 1),
        avv_expiry_date=date(2028, 1, 1),
        avv_pdf_bytes=b"%PDF-1.4\nAlpha AVV evidence\n",
    )
    second = Processor(
        processor_id=stable_id,
        controller_name="Controller Beta GmbH",
        controller_address="Betaweg 2",
        avv_signed_date=date(2026, 2, 1),
        avv_expiry_date=date(2029, 2, 1),
        avv_pdf_bytes=b"%PDF-1.7\nConflicting Beta AVV evidence\n",
    )

    register_processor(first)
    try:
        register_processor(second)
    except (TypeError, ValueError):
        return  # Rejecting a conflicting stable ID is a valid resolution.

    packet = attest_chain(format="dsk-kp13")
    matching_records = [
        record
        for record in packet["auftragsverarbeiter"]
        if record.get("processor_id") == stable_id
    ]
    matching_hashes = [
        digest
        for digest in packet["avv_hash_chain"]
        if digest in {first.avv_hash, second.avv_hash}
    ]

    assert len(matching_records) <= 1 and len(matching_hashes) <= 1, (
        "BUG: one documented stable processor_id identifies two conflicting, "
        "simultaneously attested registrations. Registration should reject the "
        "conflict or retain one unambiguous active record. "
        f"records={matching_records!r}, hashes={matching_hashes!r}"
    )
