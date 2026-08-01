"""Repro 105 — one DSK-KP13 packet silently mixes controller identities.

Run from the workspace root:
    PYTHONPATH=repo/src repo/.venv/bin/pytest \
        output/repros/105_cross_controller_attestation.py -v

The test is intentionally RED on shipped code. A correct implementation may
reject cross-controller registration, require a controller-scoped attestation,
or partition output so every packet has exactly one controller identity.
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


def test_repro_105_one_verantwortlicher_cannot_wrap_multiple_controllers() -> None:
    first = Processor(
        processor_id="repro-105-vendor-alpha",
        controller_name="Hotel Rheinland GmbH",
        controller_address="Kurparkstrasse 12, 63619 Bad Orb",
        avv_signed_date=date(2026, 1, 1),
        avv_expiry_date=date(2028, 1, 1),
        avv_pdf_bytes=b"%PDF-1.4\nHotel Rheinland AVV\n",
    )
    second = Processor(
        processor_id="repro-105-vendor-beta",
        controller_name="Unrelated Clinic AG",
        controller_address="Fremdweg 99, 60311 Frankfurt",
        avv_signed_date=date(2026, 2, 1),
        avv_expiry_date=date(2028, 2, 1),
        avv_pdf_bytes=b"%PDF-1.4\nUnrelated Clinic AVV\n",
    )

    register_processor(first)
    try:
        register_processor(second)
    except (TypeError, ValueError):
        return  # Enforcing one controller boundary is a valid resolution.

    try:
        packet = attest_chain(format="dsk-kp13")
    except (RuntimeError, TypeError, ValueError):
        return  # Refusing an ambiguous cross-controller attestation is valid.

    controller_identities = {
        (record.get("controller_name"), record.get("controller_address"))
        for record in packet["auftragsverarbeiter"]
    }
    verantwortlicher = packet["verantwortlicher"]
    responsible_identity = (
        verantwortlicher.get("controller_name"),
        verantwortlicher.get("controller_address"),
    )

    assert len(controller_identities) == 1 and controller_identities == {
        responsible_identity
    }, (
        "BUG: a DSK-KP13 packet with one singular Verantwortlicher silently "
        "includes processors belonging to different controller identities, "
        "and attributes the combined packet to the first registration. "
        f"verantwortlicher={verantwortlicher!r}, "
        f"controller_identities={controller_identities!r}, packet={packet!r}"
    )
