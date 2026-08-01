"""Repro 104 — partial per-category TOM evidence is certified complete.

Run from the workspace root:
    PYTHONPATH=repo/src repo/.venv/bin/pytest \
        output/repros/104_vacuous_disclosure_completeness.py -v

The test is intentionally RED on shipped code. A correct implementation may
reject the malformed disclosure, or return the promised per-category TOM index
while explicitly reporting the missing category as incomplete/a gap.
"""

from __future__ import annotations

from datetime import date

import pytest

from kurort_engine.avv_kaskade import (
    Processor,
    SubProcessor,
    register_processor,
    run_geeignetheitspruefung,
)
from kurort_engine.avv_kaskade.processor import _reset_registry


@pytest.fixture(autouse=True)
def isolated_avv_registry():
    _reset_registry()
    yield
    _reset_registry()


def test_repro_104_partial_tom_disclosure_is_not_certified_complete() -> None:
    sub_processor = SubProcessor(
        sub_processor_id="repro-104-sub-vendor",
        vendor_name="Partial Evidence Vendor GmbH",
        data_categories=["guest_pii", "payment_data"],
        tom_evidence_index={"guest_pii": {"control": "A.5.1"}},
    )
    processor = Processor(
        processor_id="repro-104-host",
        controller_name="Hotel Rheinland GmbH",
        controller_address="Kurparkstrasse 12, 63619 Bad Orb",
        avv_signed_date=date(2026, 4, 1),
        avv_expiry_date=date(2028, 4, 1),
        avv_pdf_bytes=b"%PDF-1.4\nPartial disclosure AVV\n",
        sub_processors=[sub_processor],
    )

    try:
        register_processor(processor)
    except (TypeError, ValueError):
        return  # Rejecting an incomplete disclosure is a valid resolution.

    report = run_geeignetheitspruefung(processor.processor_id)
    tom_index = report.get("tom_evidence_index")
    missing_category_is_reported = (
        report.get("completeness", 1.0) < 1.0
        or report.get("vendor_non_coop_complete", 1.0) < 1.0
        or any("payment_data" in str(gap) for gap in report.get("gaps", []))
    )
    promised_index_is_complete = (
        isinstance(tom_index, dict)
        and "guest_pii" in tom_index
        and "payment_data" in tom_index
    )

    assert promised_index_is_complete and missing_category_is_reported, (
        "BUG: AC-2 requires a TOM evidence index for every data category, but "
        "a sub-processor with evidence only for guest_pii and none for "
        "payment_data is certified complete with no category gap, and the "
        "promised index is absent/incomplete. "
        f"report={report!r}"
    )
