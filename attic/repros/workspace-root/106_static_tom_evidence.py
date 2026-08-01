"""Repro 106 — TOM evidence ignores processor evidence and registration state.

Run from the workspace root:
    PYTHONPATH=repo/src repo/.venv/bin/pytest \
        output/repros/106_static_tom_evidence.py -v

The test is intentionally RED on shipped code. A correct implementation must
derive meaningful processor/registration provenance: evidence-rich and
evidence-free registrations cannot be indistinguishable, and an unknown ID
must be rejected or clearly differ from registered evidence.
"""

from __future__ import annotations

from datetime import date

import pytest

from kurort_engine.avv_kaskade import (
    Processor,
    SubProcessor,
    build_tom_evidence_index,
    register_processor,
)
from kurort_engine.avv_kaskade.processor import _reset_registry


@pytest.fixture(autouse=True)
def isolated_avv_registry():
    _reset_registry()
    yield
    _reset_registry()


def _fingerprint(index: object) -> tuple[object, object, object]:
    return (
        getattr(index, "control_set", None),
        getattr(index, "entries", None),
        getattr(index, "evidence_chain_hash", None),
    )


def test_repro_106_tom_evidence_depends_on_processor_and_registration() -> None:
    rich_sub = SubProcessor(
        sub_processor_id="repro-106-rich-sub",
        vendor_name="Evidence Rich Vendor GmbH",
        data_categories=["guest_pii", "payment_data"],
        tom_evidence_index={
            "guest_pii": {"control": "A.5.15", "artifact": "annual-rbac-review.pdf"},
            "payment_data": {"control": "A.8.24", "artifact": "tls-configuration.json"},
        },
    )
    empty_sub = SubProcessor(
        sub_processor_id="repro-106-empty-sub",
        vendor_name="Evidence Free Vendor GmbH",
        data_categories=["guest_pii", "payment_data"],
        tom_evidence_index={},
    )
    rich = Processor(
        processor_id="repro-106-evidence-rich",
        controller_name="Hotel Rheinland GmbH",
        controller_address="Kurparkstrasse 12, 63619 Bad Orb",
        avv_signed_date=date(2026, 5, 1),
        avv_expiry_date=date(2028, 5, 1),
        avv_pdf_bytes=b"%PDF-1.4\nEvidence-rich AVV\n",
        sub_processors=[rich_sub],
    )
    empty = Processor(
        processor_id="repro-106-evidence-empty",
        controller_name="Hotel Rheinland GmbH",
        controller_address="Kurparkstrasse 12, 63619 Bad Orb",
        avv_signed_date=date(2026, 6, 1),
        avv_expiry_date=date(2028, 6, 1),
        avv_pdf_bytes=b"%PDF-1.4\nEvidence-free AVV\n",
        sub_processors=[empty_sub],
    )
    register_processor(rich)
    register_processor(empty)

    rich_index = build_tom_evidence_index(rich.processor_id)
    empty_index = build_tom_evidence_index(empty.processor_id)
    rich_fingerprint = _fingerprint(rich_index)
    empty_fingerprint = _fingerprint(empty_index)

    unknown_rejected = False
    unknown_fingerprint: tuple[object, object, object] | None = None
    try:
        unknown_fingerprint = _fingerprint(
            build_tom_evidence_index("repro-106-not-registered")
        )
    except (KeyError, LookupError, TypeError, ValueError):
        unknown_rejected = True

    registered_evidence_is_distinguishable = rich_fingerprint != empty_fingerprint
    unknown_is_not_fabricated_registered_evidence = unknown_rejected or (
        unknown_fingerprint != rich_fingerprint
        and unknown_fingerprint != empty_fingerprint
    )

    assert (
        registered_evidence_is_distinguishable
        and unknown_is_not_fabricated_registered_evidence
    ), (
        "BUG: evidence-rich, evidence-free, and unknown processor IDs receive "
        "indistinguishable static TOM entries and evidence-chain hashes. The "
        "processor_id lookup and supplied registration evidence do not affect "
        "the returned evidence. "
        f"rich={rich_fingerprint!r}, empty={empty_fingerprint!r}, "
        f"unknown={unknown_fingerprint!r}, unknown_rejected={unknown_rejected}"
    )
