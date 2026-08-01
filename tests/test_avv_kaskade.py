"""AC-* test oracle for kurort_engine.avv_kaskade (iter-28 Phase 3 RED).

Test oracle paths recorded in ``repo/spec/avv_kaskade/spec.yaml``:

  AC-1   test_ac1_register_processor_happy_path
  AC-1.1 test_ac11_register_processor_expired_avv_rejected
  AC-2   test_ac2_geeignetheitspruefung_report_complete
  AC-2.1 test_ac21_vendor_non_coop_flagged_in_report
  AC-3   test_ac3_attestor_dsk_kp13_packet_shape
  AC-4   test_ac4_export_audit_packet_3state
  AC-5   test_ac5_nis2_bsig_evidence_locker

Each test starts with ``importlib.util.find_spec('kurort_engine.avv_kaskade')``
pre-check; if the module is missing, the test fails with ``pytest.fail`` raising
an ``AssertionError`` (per iter-38 test convention: AssertionError-not-ImportError
verification protocol — pinned memory [2] in iter-28 KB).

Phase 3 RED NOTE: each test asserts a post-condition that the GREEN-phase
implementation must satisfy. Against the iter-28 Phase 3 stub modules the
tests fail with ``AssertionError`` (NOT ``ImportError``, NOT
``ModuleNotFoundError``, NOT ``SyntaxError``, NOT ``CollectionError``). This
proves the test reaches its assertion — the failure mode is honest.
"""
from __future__ import annotations

import importlib.util

import pytest


def _require_avv_kaskade_module() -> None:
    """Fail with AssertionError if the avv_kaskade module is not importable.

    Per iter-38 test convention: AssertionError-not-ImportError. If the module
    is missing, the test fails fast with a clear message instead of cascading
    into ImportError chain.
    """
    if importlib.util.find_spec("kurort_engine.avv_kaskade") is None:
        pytest.fail(
            "kurort_engine.avv_kaskade module not found — Phase 3 RED pre-check failed"
        )


# ---------------------------------------------------------------------------
# AC-1: register_processor happy path
# ---------------------------------------------------------------------------


def test_ac1_register_processor_happy_path() -> None:
    """AC-1: register_processor appends a Processor to the registry.

    EARS (spec.yaml AC-1):
      When register_processor(processor) is called with a Processor dataclass
      whose avv_signed_date < avv_expiry_date, the system shall compute
      avv_hash = sha256(avv_pdf_bytes).hexdigest() and append the processor
      to an append-only registry.
    """
    _require_avv_kaskade_module()

    from datetime import date

    from kurort_engine.avv_kaskade import Processor, register_processor

    processor = Processor(
        processor_id="cm-booking-com",
        controller_name="Hotel Rheinland GmbH",
        controller_address="Kurparkstrasse 12, 63619 Bad Orb",
        avv_signed_date=date(2026, 1, 15),
        avv_expiry_date=date(2028, 1, 15),
        avv_pdf_bytes=b"%PDF-1.4\n%fake avv pdf content for cm-booking-com\n",
    )

    register_processor(processor)

    # Post-conditions (stub returns None; processor.registered remains False):
    # - processor.registered is True (or registry length == 1)
    # - processor.avv_hash is a 64-char SHA-256 hex string
    assert (
        processor.registered is True
    ), f"AC-1: processor.registered should be True after register_processor, got {processor.registered}"
    assert isinstance(processor.avv_hash, str) and len(processor.avv_hash) == 64, (
        f"AC-1: processor.avv_hash should be a 64-char SHA-256 hex string, "
        f"got {processor.avv_hash!r}"
    )


# ---------------------------------------------------------------------------
# AC-1.1: register_processor expired AVV rejection
# ---------------------------------------------------------------------------


def test_ac11_register_processor_expired_avv_rejected() -> None:
    """AC-1.1: register_processor raises ValueError for expired AVV.

    EARS (spec.yaml AC-1.1):
      If register_processor(processor) is called with a Processor whose
      avv_signed_date >= avv_expiry_date, then the system shall raise
      ValueError citing the date constraint and shall NOT append the
      processor to the registry.
    """
    _require_avv_kaskade_module()

    from datetime import date

    from kurort_engine.avv_kaskade import Processor, register_processor

    expired_processor = Processor(
        processor_id="expired-vendor",
        controller_name="Expired Hotel GmbH",
        controller_address="Expiredstrasse 1, 00000 Expired City",
        avv_signed_date=date(2020, 1, 1),
        avv_expiry_date=date(2019, 12, 31),  # signed_date >= expiry_date
        avv_pdf_bytes=b"%PDF-1.4\n%expired avv\n",
    )

    # The stub returns None (no raise, no registration). Post-condition:
    # register_processor MUST raise ValueError citing the date constraint.
    # Use try/except so the failure mode is AssertionError (not pytest.Failed).
    raised_value_error = False
    error_message = ""
    try:
        register_processor(expired_processor)
    except ValueError as exc:
        raised_value_error = True
        error_message = str(exc).lower()

    assert raised_value_error, (
        f"AC-1.1: register_processor must raise ValueError for expired AVV "
        f"(avv_signed_date >= avv_expiry_date), but no exception was raised"
    )
    # The ValueError message MUST cite the date constraint per EARS.
    assert (
        "date" in error_message
        or "signed" in error_message
        or "expir" in error_message
    ), f"AC-1.1: ValueError must cite the date constraint, got: {error_message!r}"
    assert expired_processor.registered is False, (
        f"AC-1.1: expired processor must NOT be registered, "
        f"got registered={expired_processor.registered}"
    )


# ---------------------------------------------------------------------------
# AC-2: run_geeignetheitspruefung report completeness
# ---------------------------------------------------------------------------


def test_ac2_geeignetheitspruefung_report_complete() -> None:
    """AC-2: run_geeignetheitspruefung returns a complete report.

    EARS (spec.yaml AC-2):
      While a processor is registered in the avv_kaskade registry, the system
      shall expose run_geeignetheitspruefung(processor_id) which returns a
      GeeignetheitspruefungReport containing:
        (a) ISO 27001 control coverage >= 0.80
        (b) sub_processor_disclosure_completeness == 1.0
        (c) avv_signature_verified == True
        (d) tom_evidence_index per data_category of every sub_processor
    """
    _require_avv_kaskade_module()

    from kurort_engine.avv_kaskade import run_geeignetheitspruefung

    report = run_geeignetheitspruefung("cm-booking-com")

    # Stub returns dict with all 4 keys set to None; GREEN must populate.
    assert isinstance(report, dict), f"AC-2: report must be dict, got {type(report).__name__}"
    for required_key in (
        "iso27001_coverage",
        "completeness",
        "vendor_non_coop_complete",
        "report_hash",
    ):
        assert required_key in report, f"AC-2: report missing required key {required_key!r}"

    # Check iso27001_coverage is numeric AND >= 0.80 (order matters: None >= 0.80
    # would raise TypeError, so we check is not None first).
    iso_coverage = report["iso27001_coverage"]
    assert iso_coverage is not None, (
        f"AC-2: iso27001_coverage must not be None, got {iso_coverage!r}"
    )
    assert isinstance(iso_coverage, (int, float)), (
        f"AC-2: iso27001_coverage must be numeric, got {type(iso_coverage).__name__}"
    )
    assert iso_coverage >= 0.80, (
        f"AC-2: ISO 27001 control coverage must be >= 0.80, got {iso_coverage}"
    )
    assert report["completeness"] == 1.0, (
        f"AC-2: sub_processor_disclosure_completeness must be 1.0, got {report['completeness']}"
    )
    report_hash = report["report_hash"]
    assert isinstance(report_hash, str) and len(report_hash) == 64, (
        f"AC-2: report_hash must be 64-char SHA-256 hex, got {report_hash!r}"
    )


# ---------------------------------------------------------------------------
# AC-2.1: vendor_non_cooperation flagged (binding contract mitigation 3)
# ---------------------------------------------------------------------------


def test_ac21_vendor_non_coop_flagged_in_report() -> None:
    """AC-2.1: vendor_non_cooperation flagged in report gaps + < 1.0 completeness.

    EARS (spec.yaml AC-2.1):
      If a registered processor has a sub_processor with
      vendor_non_cooperation == True, then the system shall produce a
      GeeignetheitspruefungReport with vendor_non_coop_complete < 1.0 and
      flag the sub_processor in the report's gaps list.

    BINDING CONTRACT MITIGATION 3: the assertion
    ``assert vendor_non_coop_complete is not None and vendor_non_coop_complete < 1.0``
    MUST be present so AssertionError fires when the stub returns None.
    """
    _require_avv_kaskade_module()

    from datetime import date

    from kurort_engine.avv_kaskade import (
        Processor,
        SubProcessor,
        register_processor,
        run_geeignetheitspruefung,
    )

    # Build a processor with a non-cooperating sub-processor.
    non_coop_sub = SubProcessor(
        sub_processor_id="non-coop-vendor",
        vendor_name="Non Coop Vendor GmbH",
        data_categories=["guest_pii"],
        vendor_non_cooperation=True,
    )
    processor = Processor(
        processor_id="non-coop-host",
        controller_name="Non Coop Host GmbH",
        controller_address="Noncoopstrasse 1, 00000 Noncoop City",
        avv_signed_date=date(2026, 1, 15),
        avv_expiry_date=date(2028, 1, 15),
        avv_pdf_bytes=b"%PDF-1.4\n%non-coop avv\n",
        sub_processors=[non_coop_sub],
    )
    register_processor(processor)

    report = run_geeignetheitspruefung("non-coop-host")
    vendor_non_coop_complete = report["vendor_non_coop_complete"]

    # BINDING CONTRACT MITIGATION 3 — must produce AssertionError on None.
    assert (
        vendor_non_coop_complete is not None
        and vendor_non_coop_complete < 1.0
    ), f"got {vendor_non_coop_complete}"

    # The non-cooperating sub-processor MUST be flagged in the report's gaps list.
    gaps = report.get("gaps")
    assert isinstance(gaps, list), (
        f"AC-2.1: report.gaps must be a list, got {type(gaps).__name__}"
    )
    assert any("non-coop-vendor" in str(g) for g in gaps), (
        f"AC-2.1: non-cooperating sub-processor must appear in gaps list, "
        f"got gaps={gaps!r}"
    )


# ---------------------------------------------------------------------------
# AC-3: attest_chain DSK-KP13 packet shape
# ---------------------------------------------------------------------------


def test_ac3_attestor_dsk_kp13_packet_shape() -> None:
    """AC-3: attest_chain emits a DSK-Kurzpapier Nr. 13 packet with 5 keys.

    EARS (spec.yaml AC-3):
      When attest_chain(format="dsk-kp13") is called, the system shall emit
      a JSON packet whose top-level keys are:
        verantwortlicher, auftragsverarbeiter, toms, sub_processors, avv_hash_chain
      and whose verantwortlicher block contains:
        controller_name + controller_address + attestation_date
      and the avv_hash_chain shall be a list of SHA-256 hex strings matching
      the avv_hash of each registered processor in registration order.
    """
    _require_avv_kaskade_module()

    from datetime import date

    from kurort_engine.avv_kaskade import (
        Processor,
        attest_chain,
        register_processor,
    )

    # Register a processor so the registry is non-empty.
    processor = Processor(
        processor_id="cm-booking-com",
        controller_name="Hotel Rheinland GmbH",
        controller_address="Kurparkstrasse 12, 63619 Bad Orb",
        avv_signed_date=date(2026, 1, 15),
        avv_expiry_date=date(2028, 1, 15),
        avv_pdf_bytes=b"%PDF-1.4\n%avv for cm-booking-com\n",
    )
    register_processor(processor)

    packet = attest_chain(format="dsk-kp13")

    # Stub returns empty dict; GREEN must emit the 5-key packet.
    assert isinstance(packet, dict), f"AC-3: packet must be dict, got {type(packet).__name__}"

    dsk_kp13_keys = {
        "verantwortlicher",
        "auftragsverarbeiter",
        "toms",
        "sub_processors",
        "avv_hash_chain",
    }
    missing = dsk_kp13_keys - set(packet.keys())
    assert not missing, f"AC-3: packet missing DSK-KP13 keys: {sorted(missing)}"

    # The verantwortlicher block MUST contain controller_name + address + date.
    verantwortlicher = packet["verantwortlicher"]
    assert isinstance(verantwortlicher, dict), (
        f"AC-3: verantwortlicher must be dict, got {type(verantwortlicher).__name__}"
    )
    for required_field in ("controller_name", "controller_address", "attestation_date"):
        assert required_field in verantwortlicher, (
            f"AC-3: verantwortlicher missing required field {required_field!r}"
        )

    # avv_hash_chain MUST be a list of 64-char SHA-256 hex strings.
    avv_hash_chain = packet["avv_hash_chain"]
    assert isinstance(avv_hash_chain, list), (
        f"AC-3: avv_hash_chain must be list, got {type(avv_hash_chain).__name__}"
    )
    assert len(avv_hash_chain) >= 1, "AC-3: avv_hash_chain must contain >= 1 registered processor"
    for hash_entry in avv_hash_chain:
        assert isinstance(hash_entry, str) and len(hash_entry) == 64, (
            f"AC-3: avv_hash_chain entries must be 64-char SHA-256 hex, got {hash_entry!r}"
        )


# ---------------------------------------------------------------------------
# AC-4: export_audit_packet 3-state PDF (DEFERRED per binding contract)
# ---------------------------------------------------------------------------


def test_ac4_export_audit_packet_3state() -> None:
    """AC-4: export_audit_packet emits a 3-state PDF.

    EARS (spec.yaml AC-4):
      When export_audit_packet(processor_id, format) is called with format in
      {"lfa-baylda", "lfdi-bw", "hbdi-he"}, the system shall return a packet
      object whose payload bytes start with b"%PDF-" and whose
      metadata["state_format"] equals the requested format; and the system
      shall raise ValueError for any format not in the three supported state
      formats.

    DEFERRED to BFSG-AA reviewer pool per binding contract mitigation 1
    (STALE_PENDING_FLAG in spec.lock.md). The test still runs; if the GREEN
    implementation is not available, the test fails with AssertionError on
    the payload bytes / state_format discrimination.
    """
    _require_avv_kaskade_module()

    from datetime import date

    from kurort_engine.avv_kaskade import (
        Processor,
        export_audit_packet,
        register_processor,
    )

    # Register a processor so the registry is non-empty.
    processor = Processor(
        processor_id="cm-booking-com",
        controller_name="Hotel Rheinland GmbH",
        controller_address="Kurparkstrasse 12, 63619 Bad Orb",
        avv_signed_date=date(2026, 1, 15),
        avv_expiry_date=date(2028, 1, 15),
        avv_pdf_bytes=b"%PDF-1.4\n%avv for cm-booking-com\n",
    )
    register_processor(processor)

    # AC-4 happy path: lfa-baylda format.
    baylda_packet = export_audit_packet("cm-booking-com", format="lfa-baylda")
    assert baylda_packet is not None, "AC-4: lfa-baylda packet must not be None"

    payload = getattr(baylda_packet, "payload", None) or (
        baylda_packet.get("payload") if isinstance(baylda_packet, dict) else None
    )
    metadata = getattr(baylda_packet, "metadata", None) or (
        baylda_packet.get("metadata") if isinstance(baylda_packet, dict) else None
    )
    assert payload is not None and payload.startswith(b"%PDF-"), (
        f"AC-4: payload must start with b'%PDF-', got {payload[:8]!r}"
    )
    assert isinstance(metadata, dict) and metadata.get("state_format") == "lfa-baylda", (
        f"AC-4: metadata['state_format'] must equal 'lfa-baylda', got {metadata!r}"
    )

    # AC-4 negative: unknown format raises ValueError.
    # Use try/except so the failure mode is AssertionError (not pytest.Failed).
    raised_value_error = False
    try:
        export_audit_packet("cm-booking-com", format="unknown-state-format")
    except ValueError:
        raised_value_error = True
    assert raised_value_error, (
        f"AC-4: export_audit_packet must raise ValueError for unknown format, "
        f"but no exception was raised"
    )


# ---------------------------------------------------------------------------
# AC-5: NIS2 §38 BSIG BSI Grundschutz 2026 TOM evidence locker
# ---------------------------------------------------------------------------


def test_ac5_nis2_bsig_evidence_locker() -> None:
    """AC-5: build_tom_evidence_index returns NIS2 §38 BSIG BSI Grundschutz 2026 index.

    EARS (spec.yaml AC-5):
      When build_tom_evidence_index(processor_id, control_set="bsi-grundschutz-2026")
      is called, the system shall return a TomEvidenceIndex whose
      control_set == "bsi-grundschutz-2026", whose entries list one TOM-evidence
      record per ISO 27001 Annex A control mapped to the BSI Grundschutz 2026
      Bausteine, and whose evidence_chain_hash is a SHA-256 hex of the
      canonical-JSON serialization of the entries in registry-registration order.
    """
    _require_avv_kaskade_module()

    from datetime import date

    from kurort_engine.avv_kaskade import (
        Processor,
        build_tom_evidence_index,
        register_processor,
    )

    # Register a processor so the registry is non-empty.
    processor = Processor(
        processor_id="cm-booking-com",
        controller_name="Hotel Rheinland GmbH",
        controller_address="Kurparkstrasse 12, 63619 Bad Orb",
        avv_signed_date=date(2026, 1, 15),
        avv_expiry_date=date(2028, 1, 15),
        avv_pdf_bytes=b"%PDF-1.4\n%avv for cm-booking-com\n",
    )
    register_processor(processor)

    index = build_tom_evidence_index("cm-booking-com", control_set="bsi-grundschutz-2026")

    # Stub returns empty list; GREEN must return a TomEvidence index object.
    # We accept either a list of entries or a TomEvidence object with .entries.
    if isinstance(index, list):
        entries = index
        control_set = "bsi-grundschutz-2026"
        evidence_chain_hash = None
    else:
        entries = getattr(index, "entries", [])
        control_set = getattr(index, "control_set", None)
        evidence_chain_hash = getattr(index, "evidence_chain_hash", None)

    assert control_set == "bsi-grundschutz-2026", (
        f"AC-5: control_set must be 'bsi-grundschutz-2026', got {control_set!r}"
    )
    assert isinstance(entries, list) and len(entries) >= 1, (
        f"AC-5: entries must be non-empty list (>=1 TOM-evidence record), "
        f"got entries={entries!r}"
    )
    assert isinstance(evidence_chain_hash, str) and len(evidence_chain_hash) == 64, (
        f"AC-5: evidence_chain_hash must be 64-char SHA-256 hex, "
        f"got {evidence_chain_hash!r}"
    )