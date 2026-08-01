"""Repro 103 — post-registration mutation leaves a stale attested AVV hash.

Run from the workspace root:
    PYTHONPATH=repo/src repo/.venv/bin/pytest \
        output/repros/103_post_registration_mutation.py -v

The test is intentionally RED on shipped code. It accepts immutable records,
integrity-error rejection, or an attestation hash recomputed from the displayed
live registration snapshot.
"""

from __future__ import annotations

from datetime import date
from hashlib import sha256

import pytest

from kurort_engine.avv_kaskade import Processor, attest_chain, register_processor
from kurort_engine.avv_kaskade.processor import _reset_registry


@pytest.fixture(autouse=True)
def isolated_avv_registry():
    _reset_registry()
    yield
    _reset_registry()


def test_repro_103_attested_hash_matches_post_mutation_evidence_snapshot() -> None:
    processor = Processor(
        processor_id="repro-103-original",
        controller_name="Original Controller GmbH",
        controller_address="Originalstrasse 3",
        avv_signed_date=date(2026, 3, 1),
        avv_expiry_date=date(2028, 3, 1),
        avv_pdf_bytes=b"%PDF-1.4\nOriginal signed AVV snapshot\n",
    )
    register_processor(processor)
    original_hash = processor.avv_hash
    mutated_bytes = b"%PDF-1.7\nAttacker-controlled replacement evidence\n"

    try:
        processor.processor_id = "repro-103-mutated"
        processor.controller_name = "Attacker Controlled GmbH"
        processor.controller_address = "Changedweg 99"
        processor.avv_pdf_bytes = mutated_bytes
    except (AttributeError, TypeError, ValueError):
        return  # Immutable registered identity/evidence is a valid resolution.

    expected_live_hash = sha256(mutated_bytes).hexdigest()
    try:
        packet = attest_chain(format="dsk-kp13")
    except (RuntimeError, TypeError, ValueError):
        return  # Refusing to attest an integrity violation is also valid.

    records = packet["auftragsverarbeiter"]
    matching_indexes = [
        index
        for index, record in enumerate(records)
        if record.get("processor_id") == "repro-103-mutated"
    ]
    if not matching_indexes:
        return  # An invalidated live object was not represented as attested.

    attested_hash = packet["avv_hash_chain"][matching_indexes[0]]
    assert attested_hash == expected_live_hash and attested_hash != original_hash, (
        "BUG: the attestation displays the post-registration mutated identity "
        "but retains the pre-mutation AVV hash. The hash therefore does not "
        "prove the live evidence snapshot beside it. "
        f"original_hash={original_hash!r}, live_hash={expected_live_hash!r}, "
        f"attested_hash={attested_hash!r}, record={records[matching_indexes[0]]!r}"
    )
