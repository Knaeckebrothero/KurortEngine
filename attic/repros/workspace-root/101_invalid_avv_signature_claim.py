"""Repro 101 — invalid AVV bytes are silently treated as fully suitable.

Run from the workspace root:
    PYTHONPATH=repo/src repo/.venv/bin/pytest \
        output/repros/101_invalid_avv_signature_claim.py -v

The test is intentionally RED on the shipped implementation. It accepts any
correct implementation strategy: reject invalid evidence during registration,
or explicitly report the accepted evidence as unverified/incomplete.
"""

from __future__ import annotations

from datetime import date

import pytest

from kurort_engine.avv_kaskade import (
    Processor,
    register_processor,
    run_geeignetheitspruefung,
)
from kurort_engine.avv_kaskade.processor import _reset_registry


@pytest.fixture(autouse=True)
def isolated_avv_registry():
    """Prevent the process-global AVV registry from contaminating this repro."""
    _reset_registry()
    yield
    _reset_registry()


def test_repro_101_invalid_avv_evidence_cannot_be_fully_suitable() -> None:
    """AC-2's signature-verification claim must not be fabricated for junk bytes."""
    invalid_cases = {
        "empty-avv": b"",
        "plain-text-avv": b"This is not a PDF document or AVV",
        "header-only-avv": b"%PDF-",
    }
    silently_suitable: list[tuple[str, dict[str, object]]] = []

    for case_name, invalid_bytes in invalid_cases.items():
        processor = Processor(
            processor_id=f"repro-101-{case_name}",
            controller_name="Hotel Rheinland GmbH",
            controller_address="Kurparkstrasse 12, 63619 Bad Orb",
            avv_signed_date=date(2026, 1, 15),
            avv_expiry_date=date(2028, 1, 15),
            avv_pdf_bytes=invalid_bytes,
        )

        try:
            register_processor(processor)
        except (TypeError, ValueError):
            # Rejection is a valid implementation response to invalid evidence.
            continue

        report = run_geeignetheitspruefung(processor.processor_id)
        explicitly_unverified = report.get("avv_signature_verified") is False
        explicitly_incomplete = (
            report.get("iso27001_coverage", 1.0) < 0.80
            or report.get("completeness", 1.0) < 1.0
            or report.get("vendor_non_coop_complete", 1.0) < 1.0
            or bool(report.get("gaps"))
        )

        if processor.registered and not explicitly_unverified and not explicitly_incomplete:
            silently_suitable.append((case_name, report))

    assert not silently_suitable, (
        "BUG: invalid AVV evidence was accepted and silently treated as fully "
        "suitable even though AC-2 promises avv_signature_verified=True. "
        "A correct implementation may reject the evidence or explicitly mark "
        "it unverified/incomplete. Unsafe cases: "
        f"{silently_suitable!r}"
    )
