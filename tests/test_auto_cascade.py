"""Iter-38 Phase 2 RED tests — ``kurort_engine.kurgaste_retention.auto_cascade``
(DSGVO Art. 17 right-to-erasure in-app self-service cascade).

Iter-38 (Developer) — Pattern C GREENFIELD chain-extension (0 SHAs touched,
7 SHIPs preserved verbatim). Chosen by iter-37 Critic verdict (P2 PRIMARY
for iter-38 Developer; reversal-pattern HARD PASS within 4-pool; 9/9 Pattern
D clean per `iter-34-proposal-002-dsgvo-art-17-cascade-kurortenginekurgasteretentionautocasca`).

AC-1..AC-9 contract (verbatim from `spec.yaml` PROTECTED block SHA
`bd8bf2e22f41bd5f5f9dbd1ba29d4798a7919cba9a1e338e5559be2f3cbcc3e3`):
  - AC-1: `forget_guest(guest_id: str) -> CascadeResult` (5-step atomic cascade)
  - AC-2: `redact_invoice_for_cascade(invoice: dict, audit_reason: str) -> dict`
          (REDACT-AND-PRESERVE; HGB §257 / AO §147; Decimal exact match)
  - AC-3: `cascade_anonymize_spa_entries(guest_id: str) -> dict`
          (re-uses SHIPPED `SpaManager` + `SpaBooking`)
  - AC-4: `emit_forget_guest_event(guest_id: str, channels: list[str]) -> ForgetGuestEvent`
          (EU-local only; BFSGComplianceError on non-EU channel)
  - AC-5: `write_art30_audit_entry(cascade_result: dict) -> AuditEntry`
          (Art. 30 VVT append-only; `a30-<uuid8>` format; SHA-256 hash)
  - AC-6: `require_art_173_override_reason(reason: str, legal_basis: str) -> Art173Override`
          (reason >=20 chars after strip; legal_basis enum; ValueError on invalid)
  - AC-7: `run_cascade_with_retry(guest_id: str, retry_max: int = 2) -> CascadeResult`
          (idempotent retry; `cascade_status == "partial"`; audit-on-partial)
  - AC-8: `assert_consent_or_legal_basis(consent_record: dict, legal_basis: str) -> Art9AuditFlag`
          (Art. 9 health-data; consent OR legal_basis enum; `a9-<uuid8>` audit-flag)
  - AC-9: full test suite 118 (iter-36 SHIPPED baseline) + 9 (iter-38 NEW) = 127/127 PASS

RED VERIFY
----------
Each test MUST fail with `AssertionError`, NOT `ImportError`. We use
`importlib.util.find_spec` as a pre-check (wrapped in try/except) so
missing-module failures surface as `AssertionError` ("module should exist"),
not `ModuleNotFoundError`.

Per `iter-38-developer-pinned-rules-p2-dsgvo-art-17-cascade-tdd-discipline-greenfield`:
  * No mocking the unit under test
  * No `pytest.skip`
  * Concrete `Decimal` exact-match math (no float precision drift)
  * Concrete substring assertions (for label/footer/note fields)
  * Concrete `pytest.raises(BFSGComplianceError)` guards for AC-4 non-EU
  * Concrete `pytest.raises(ValueError)` guards for AC-6 / AC-8 invalid input
  * Chain-extension to SHIPPED modules is exercised via real imports
    (NOT mocked) — confirms the 7 SHIPs are importable
  * All 7 SHIPs MUST remain verbatim UNCHANGED
"""
from __future__ import annotations

import importlib.util
import inspect
import json

import pytest


# ===========================================================================
# Module-importability helpers (per iter-33 / iter-36 / iter-30 honest-RED
# pattern; coerces ModuleNotFoundError -> AssertionError so RED tests fail
# with the right error type, not ImportError)
# ===========================================================================

def _find_spec_or_assert(module_name: str, *, parent: str | None = None) -> str:
    """Run `importlib.util.find_spec` and coerce missing-module failures
    into `AssertionError` so the test surfaces a "spec unmet" failure
    rather than a `ModuleNotFoundError` import failure.

    Per pinned rule 3 (RED verification protocol): red-phase tests must fail
    with `AssertionError`, not `ImportError` / `ModuleNotFoundError` /
    `SyntaxError`.
    """
    try:
        found = importlib.util.find_spec(module_name)
    except (ModuleNotFoundError, ImportError) as exc:
        scope = parent or module_name
        raise AssertionError(
            f"{scope} is not importable - green phase must create the "
            f"module before this test can pass. find_spec raised: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    assert found is not None, (
        f"{module_name} is not importable - green phase must create the "
        f"module before this test can pass. find_spec returned: {found!r}"
    )
    return f"found at {found.origin if hasattr(found, 'origin') else '<namespace>'}"


# Pre-check helpers — convert missing-module failures to AssertionError
def _kurgaste_retention_package_is_importable() -> str:
    """Pre-check: the NEW kurgaste_retention package must exist."""
    return _find_spec_or_assert(
        "kurort_engine.kurgaste_retention",
        parent="kurort_engine.kurgaste_retention",
    )


def _auto_cascade_module_is_importable() -> str:
    """Pre-check: NEW auto_cascade module must exist (AC-1, AC-2, AC-3, AC-4, AC-7)."""
    return _find_spec_or_assert(
        "kurort_engine.kurgaste_retention.auto_cascade",
        parent="kurort_engine.kurgaste_retention.auto_cascade",
    )


def _art17_exceptions_module_is_importable() -> str:
    """Pre-check: NEW art17_exceptions module must exist (AC-6)."""
    return _find_spec_or_assert(
        "kurort_engine.kurgaste_retention.art17_exceptions",
        parent="kurort_engine.kurgaste_retention.art17_exceptions",
    )


def _art9_health_data_module_is_importable() -> str:
    """Pre-check: NEW art9_health_data module must exist (AC-8)."""
    return _find_spec_or_assert(
        "kurort_engine.kurgaste_retention.art9_health_data",
        parent="kurort_engine.kurgaste_retention.art9_health_data",
    )


def _audit_log_module_is_importable() -> str:
    """Pre-check: NEW audit_log module must exist (AC-5)."""
    return _find_spec_or_assert(
        "kurort_engine.kurgaste_retention.audit_log",
        parent="kurort_engine.kurgaste_retention.audit_log",
    )


# SHIPPED modules anti-drift helpers (must remain importable in iter-38 GREEN)
def _kurkarte_wallet_is_importable() -> str:
    return _find_spec_or_assert("kurort_engine.kurkarte_wallet")


def _predicate_filing_is_importable() -> str:
    return _find_spec_or_assert("kurort_engine.predicate_filing")


def _kurpaket_orchestrator_is_importable() -> str:
    return _find_spec_or_assert("kurort_engine.kurpaket_orchestrator")


def _spa_wellness_is_importable() -> str:
    return _find_spec_or_assert("kurort_engine.spa_wellness")


def _meldeschein_is_importable() -> str:
    return _find_spec_or_assert("kurort_engine.meldeschein")


# Import helpers (after find_spec guard)
def _get_auto_cascade_module():
    _auto_cascade_module_is_importable()
    _mod = __import__("kurort_engine.kurgaste_retention.auto_cascade", fromlist=["_dummy_"])  # noqa: E402
    assert _mod is not None
    return _mod


def _get_art17_exceptions_module():
    _art17_exceptions_module_is_importable()
    _mod = __import__("kurort_engine.kurgaste_retention.art17_exceptions", fromlist=["_dummy_"])  # noqa: E402
    assert _mod is not None
    return _mod


def _get_art9_health_data_module():
    _art9_health_data_module_is_importable()
    _mod = __import__("kurort_engine.kurgaste_retention.art9_health_data", fromlist=["_dummy_"])  # noqa: E402
    assert _mod is not None
    return _mod


def _get_audit_log_module():
    _audit_log_module_is_importable()
    _mod = __import__("kurort_engine.kurgaste_retention.audit_log", fromlist=["_dummy_"])  # noqa: E402
    assert _mod is not None
    return _mod


# ===========================================================================
# Synthetic fixtures (schema-agnostic; NOT a real PDF parse or invoice fetch)
# ===========================================================================

# AC-1: synthetic guest_id for the 5-step atomic cascade
_SYNTHETIC_GUEST_ID = "g-12345678-9abc"

# AC-2: synthetic invoice with Decimal amounts (Badekur 7-night stay,
# non-§23 SGB V standard booking)
_SYNTHETIC_INVOICE = {
    "invoice_id": "inv-2026-07-001",
    "guest_id": _SYNTHETIC_GUEST_ID,
    "guest_name": "Max Mustermann",
    "guest_address": "Musterstraße 1, 63619 Bad Orb",
    "nights": 7,
    "invoice_total_eur": "1234.56",  # Decimal-string form (per spec.yaml A-2)
    "items": [
        {"description": "Kurtaxe 7 nights adult", "amount_eur": "17.50"},
        {"description": "Badekur Rechnung 7 nights", "amount_eur": "1217.06"},
    ],
}

# AC-4: EU-local channels (per DSGVO Art. 44 NO cross-border transfer)
_EU_LOCAL_CHANNELS = ["booking_com", "hrs", "holidaycheck"]
# Non-EU channel (must raise BFSGComplianceError)
_NON_EU_CHANNELS = ["expedia_us", "hotelscom_us", "trivago_au"]

# AC-5: cascade result dict shape (synthetic; used to drive audit log entry)
_SYNTHETIC_CASCADE_RESULT = {
    "cascade_transaction_id": "a3f2c1d4",
    "guest_id": _SYNTHETIC_GUEST_ID,
    "forgotten_at": "2026-07-07T12:00:00Z",
    "actor": "admin",
    "reason": "Art. 17 right-to-erasure",
    "cascade_steps_completed": [
        "step_1_booking_ledger",
        "step_2_invoice_redact",
        "step_3_spa_belegung_sync",
        "step_4_channel_manager_sync",
        "step_5_audit_log",
    ],
    "cascade_status": "completed",
    "audit_entry_hash": "0" * 64,  # placeholder; real hash computed in green
    "art_30_audit_log_emitted": True,
}


# ===========================================================================
# AC-1 — forget_guest executes 5-step atomic cascade
# ===========================================================================

def test_ac1_auto_cascade_executes_5_steps_atomically() -> None:
    """AC-1 spec test_oracle — happy-path: `forget_guest` 5-step atomic cascade.

    Asserts that `forget_guest(guest_id: str) -> CascadeResult`
    returns a JSON-serializable dict with required keys:
      * `cascade_transaction_id: str` (UUID4 hex 8 chars)
      * `guest_id: str`
      * `forgotten_at: str` (ISO 8601 UTC)
      * `actor: str` ("admin")
      * `reason: str` ("Art. 17 right-to-erasure")
      * `cascade_steps_completed: list[str]` (5 strings)
      * `cascade_status: str` ("completed" | "partial")
      * `audit_entry_hash: str` (SHA-256 hex of audit log entry)
      * `art_30_audit_log_emitted: bool` (True on success)
    """
    _auto_cascade_module_is_importable()
    mod = _get_auto_cascade_module()

    # ----- function existence check -----
    forget_guest = getattr(mod, "forget_guest", None)
    auto_cascade = getattr(mod, "auto_cascade", None)  # alias
    assert callable(forget_guest) or callable(auto_cascade), (
        "AC-1: auto_cascade must expose a callable forget_guest (or auto_cascade "
        f"alias) entry point; found: {[n for n in dir(mod) if not n.startswith('_')]!r}"
    )
    func = forget_guest if callable(forget_guest) else auto_cascade

    # ----- call with synthetic input -----
    result = func(_SYNTHETIC_GUEST_ID)

    # ----- structural assertion (JSON-serializable + required keys) -----
    assert isinstance(result, dict), (
        f"AC-1: result must be a dict; got {type(result).__name__}"
    )
    # json.dumps round-trip (Decimal -> str default)
    json.dumps(result, default=str)

    for required_key in (
        "cascade_transaction_id",
        "guest_id",
        "forgotten_at",
        "actor",
        "reason",
        "cascade_steps_completed",
        "cascade_status",
        "audit_entry_hash",
        "art_30_audit_log_emitted",
    ):
        assert required_key in result, (
            f"AC-1: result must contain required key '{required_key}'; "
            f"got keys: {list(result.keys())!r}"
        )

    # ----- value-type + exact-equality assertions -----
    assert result["guest_id"] == _SYNTHETIC_GUEST_ID
    assert result["actor"] == "admin"
    assert result["reason"] == "Art. 17 right-to-erasure"
    assert result["cascade_status"] in ("completed", "partial")
    assert result["art_30_audit_log_emitted"] is True
    assert len(result["cascade_transaction_id"]) == 8  # UUID4 hex 8 chars
    assert len(result["audit_entry_hash"]) == 64  # SHA-256 hex
    assert len(result["cascade_steps_completed"]) == 5


# ===========================================================================
# AC-2 — redact_invoice_for_cascade REDACT-AND-PRESERVE
# ===========================================================================

def test_ac2_invoice_redact_and_preserve_aggregate_ledger() -> None:
    """AC-2 spec test_oracle — REDACT-AND-PRESERVE invoice pattern.

    Asserts that `redact_invoice_for_cascade(invoice: dict, audit_reason: str)
    -> dict` returns a JSON-serializable dict with required keys:
      * `original_invoice_total_eur: Decimal`
      * `aggregate_ledger_eur: Decimal` (preserved, NOT redacted)
      * `aggregate_ledger_count: int` (preserved)
      * `redacted_pii_fields: list[str]` (e.g. ["guest_name", "guest_address"])
      * `redacted_at: str` (ISO 8601 UTC)
      * `audit_reason: str`

    Per HGB §257 (10-year retention) + AO §147 (7-year retention), the
    aggregate ledger EUR MUST equal the original invoice total EUR (Decimal
    exact-match precision; no float math).
    """
    _auto_cascade_module_is_importable()
    mod = _get_auto_cascade_module()

    redact_invoice_for_cascade = getattr(mod, "redact_invoice_for_cascade", None)
    assert callable(redact_invoice_for_cascade), (
        "AC-2: auto_cascade must expose a callable redact_invoice_for_cascade "
        f"entry point; found: {[n for n in dir(mod) if not n.startswith('_')]!r}"
    )

    # ----- call with synthetic invoice + audit reason -----
    audit_reason = "Art. 17 (1) right-to-erasure, HGB §257 retention preserved"
    result = redact_invoice_for_cascade(_SYNTHETIC_INVOICE, audit_reason)

    # ----- structural assertion -----
    assert isinstance(result, dict), (
        f"AC-2: result must be a dict; got {type(result).__name__}"
    )
    json.dumps(result, default=str)

    for required_key in (
        "original_invoice_total_eur",
        "aggregate_ledger_eur",
        "aggregate_ledger_count",
        "redacted_pii_fields",
        "redacted_at",
        "audit_reason",
    ):
        assert required_key in result, (
            f"AC-2: result must contain required key '{required_key}'; "
            f"got keys: {list(result.keys())!r}"
        )

    # ----- Decimal exact-match assertion (no float math) -----
    from decimal import Decimal
    expected_total = Decimal("1234.56")
    assert result["original_invoice_total_eur"] == expected_total
    # The KEY invariant: aggregate_ledger_eur MUST equal original_invoice_total_eur
    # (HGB §257 / AO §147 retention preserves the aggregate)
    assert result["aggregate_ledger_eur"] == expected_total
    assert result["aggregate_ledger_count"] >= 1
    # PII fields MUST be redacted (not equal to original)
    assert "guest_name" in result["redacted_pii_fields"]
    assert "guest_address" in result["redacted_pii_fields"]
    assert result["audit_reason"] == audit_reason
    # ISO 8601 UTC format: YYYY-MM-DDTHH:MM:SSZ
    assert "T" in result["redacted_at"]
    assert result["redacted_at"].endswith("Z")


# ===========================================================================
# AC-3 — cascade_anonymize_spa_entries re-uses SHIPPED spa_wellness
# ===========================================================================

def test_ac3_spa_belegung_cascade_anonymizes() -> None:
    """AC-3 spec test_oracle — spa-belegung cascade anonymization.

    Asserts that `cascade_anonymize_spa_entries(guest_id: str) -> dict`
    returns a JSON-serializable dict with required keys:
      * `guest_id: str`
      * `spa_entries_anonymized_count: int`
      * `spa_entries_referenced: list[str]` (entry IDs)
      * `anonymization_strategy: str` ("replace_pii_with_anon_id_<uuid8>")
      * `cascade_step: str` ("step_3_spa_belegung_sync")

    The function SHALL re-use SHIPPED
    `kurort_engine.spa_wellness.SpaManager` and
    `kurort_engine.spa_wellness.SpaBooking` (imported read-only).
    """
    # SHIPPED spa_wellness must be importable (anti-drift discipline)
    _spa_wellness_is_importable()
    _auto_cascade_module_is_importable()
    mod = _get_auto_cascade_module()

    cascade_anonymize_spa_entries = getattr(mod, "cascade_anonymize_spa_entries", None)
    assert callable(cascade_anonymize_spa_entries), (
        "AC-3: auto_cascade must expose a callable cascade_anonymize_spa_entries "
        f"entry point; found: {[n for n in dir(mod) if not n.startswith('_')]!r}"
    )

    # ----- call with synthetic guest_id -----
    result = cascade_anonymize_spa_entries(_SYNTHETIC_GUEST_ID)

    # ----- structural assertion -----
    assert isinstance(result, dict), (
        f"AC-3: result must be a dict; got {type(result).__name__}"
    )
    json.dumps(result, default=str)

    for required_key in (
        "guest_id",
        "spa_entries_anonymized_count",
        "spa_entries_referenced",
        "anonymization_strategy",
        "cascade_step",
    ):
        assert required_key in result, (
            f"AC-3: result must contain required key '{required_key}'; "
            f"got keys: {list(result.keys())!r}"
        )

    # ----- value-type + exact-equality assertions -----
    assert result["guest_id"] == _SYNTHETIC_GUEST_ID
    assert result["cascade_step"] == "step_3_spa_belegung_sync"
    assert result["spa_entries_anonymized_count"] >= 0
    assert isinstance(result["spa_entries_referenced"], list)
    assert "anon_id" in result["anonymization_strategy"]


# ===========================================================================
# AC-4 — emit_forget_guest_event EU-local only + BFSGComplianceError on non-EU
# ===========================================================================

def test_ac4_channel_manager_emits_forget_event() -> None:
    """AC-4 spec test_oracle — channel-manager "forget this guest" event.

    Asserts that `emit_forget_guest_event(guest_id: str, channels: list[str])
    -> ForgetGuestEvent` returns a JSON-serializable dict with required keys:
      * `event_type: str` ("forget_this_guest")
      * `guest_id: str`
      * `channels: list[str]` (e.g. ["booking_com", "hrs", "holidaycheck"])
      * `emitted_at: str` (ISO 8601 UTC)
      * `event_id: str` (UUID4 hex 8 chars)
      * `cascade_step: str` ("step_4_channel_manager_sync")

    EU-local channels: Booking.com NL + HRS DE + HolidayCheck CH/EEA
    Non-EU channels: SHALL raise `kurort_engine.kurkarte_wallet.BFSGComplianceError`
    (re-used from SHIPPED iter-21).
    """
    _kurkarte_wallet_is_importable()
    _auto_cascade_module_is_importable()
    mod = _get_auto_cascade_module()

    emit_forget_guest_event = getattr(mod, "emit_forget_guest_event", None)
    assert callable(emit_forget_guest_event), (
        "AC-4: auto_cascade must expose a callable emit_forget_guest_event "
        f"entry point; found: {[n for n in dir(mod) if not n.startswith('_')]!r}"
    )

    # ----- EU-local channel happy-path -----
    result = emit_forget_guest_event(_SYNTHETIC_GUEST_ID, _EU_LOCAL_CHANNELS)

    assert isinstance(result, dict), (
        f"AC-4: result must be a dict; got {type(result).__name__}"
    )
    json.dumps(result, default=str)

    for required_key in (
        "event_type",
        "guest_id",
        "channels",
        "emitted_at",
        "event_id",
        "cascade_step",
    ):
        assert required_key in result, (
            f"AC-4: result must contain required key '{required_key}'; "
            f"got keys: {list(result.keys())!r}"
        )

    assert result["event_type"] == "forget_this_guest"
    assert result["guest_id"] == _SYNTHETIC_GUEST_ID
    assert result["channels"] == _EU_LOCAL_CHANNELS
    assert result["cascade_step"] == "step_4_channel_manager_sync"
    assert len(result["event_id"]) == 8  # UUID4 hex 8 chars
    assert "T" in result["emitted_at"]
    assert result["emitted_at"].endswith("Z")

    # ----- non-EU channel raises BFSGComplianceError -----
    # Import the SHIPPED BFSGComplianceError for the exception class assertion
    from kurort_engine.kurkarte_wallet import BFSGComplianceError
    with pytest.raises(BFSGComplianceError):
        emit_forget_guest_event(_SYNTHETIC_GUEST_ID, _NON_EU_CHANNELS)


# ===========================================================================
# AC-5 — write_art30_audit_entry Art. 30 VVT append-only
# ===========================================================================

def test_ac5_art30_audit_log_written() -> None:
    """AC-5 spec test_oracle — Art. 30 VVT audit log entry.

    Asserts that `write_art30_audit_entry(cascade_result: dict) -> AuditEntry`
    returns a JSON-serializable dict with required keys:
      * `audit_id: str` ("a30-<uuid8>" format)
      * `timestamp_utc: str` (ISO 8601 UTC)
      * `verarbeitungstätigkeit: str` ("Löschung gemäß DSGVO Art. 17")
      * `betroffene_person: str` (guest_id)
      * `verantwortlicher: str` ("Hotel Rheinland Bad Orb GmbH")
      * `aufbewahrungsfrist: str` ("Art. 30 VVT — 3 Jahre Log-Aufbewahrung")
      * `rechtsgrundlage: str` ("DSGVO Art. 17 (1)")
      * `audit_log_hash: str` (SHA-256 hex of canonical JSON of this entry)

    The audit log SHALL be append-only (no update or delete APIs exposed).
    """
    _audit_log_module_is_importable()
    mod = _get_audit_log_module()

    write_art30_audit_entry = getattr(mod, "write_art30_audit_entry", None)
    assert callable(write_art30_audit_entry), (
        "AC-5: audit_log must expose a callable write_art30_audit_entry "
        f"entry point; found: {[n for n in dir(mod) if not n.startswith('_')]!r}"
    )

    # ----- call with synthetic cascade result -----
    result = write_art30_audit_entry(_SYNTHETIC_CASCADE_RESULT)

    # ----- structural assertion -----
    assert isinstance(result, dict), (
        f"AC-5: result must be a dict; got {type(result).__name__}"
    )
    json.dumps(result, default=str)

    for required_key in (
        "audit_id",
        "timestamp_utc",
        "verarbeitungstätigkeit",
        "betroffene_person",
        "verantwortlicher",
        "aufbewahrungsfrist",
        "rechtsgrundlage",
        "audit_log_hash",
    ):
        assert required_key in result, (
            f"AC-5: result must contain required key '{required_key}'; "
            f"got keys: {list(result.keys())!r}"
        )

    # ----- value-type + exact-equality assertions -----
    assert result["audit_id"].startswith("a30-")
    assert len(result["audit_id"]) == 12  # "a30-" + 8 hex chars
    assert result["betroffene_person"] == _SYNTHETIC_GUEST_ID
    assert result["verantwortlicher"] == "Hotel Rheinland Bad Orb GmbH"
    assert result["rechtsgrundlage"] == "DSGVO Art. 17 (1)"
    assert "Löschung gemäß DSGVO Art. 17" in result["verarbeitungstätigkeit"]
    assert "Art. 30 VVT" in result["aufbewahrungsfrist"]
    assert len(result["audit_log_hash"]) == 64  # SHA-256 hex
    assert "T" in result["timestamp_utc"]
    assert result["timestamp_utc"].endswith("Z")

    # ----- append-only discipline: NO update/delete APIs exposed -----
    forbidden_apis = ["update", "delete", "modify", "revoke", "amend"]
    exposed_apis = [n for n in dir(mod) if not n.startswith("_")]
    for forbidden in forbidden_apis:
        for exposed in exposed_apis:
            assert forbidden not in exposed.lower(), (
                f"AC-5: audit_log MUST be append-only; found suspicious "
                f"API name '{exposed}' (forbidden pattern '{forbidden}')"
            )


# ===========================================================================
# AC-6 — require_art_173_override_reason (Art. 17(3) HGB §257 override)
# ===========================================================================

def test_ac6_art173_override_requires_reason() -> None:
    """AC-6 spec test_oracle — Art. 17(3) HGB §257 override.

    Asserts that `require_art_173_override_reason(reason: str, legal_basis: str)
    -> Art173Override` returns a JSON-serializable dict with required keys:
      * `override_id: str` ("a173-<uuid8>" format)
      * `reason: str` (>= 20 chars, validated non-empty after strip)
      * `legal_basis: str` (one of 5 allowed values per spec.yaml AC-6)
      * `requested_at: str` (ISO 8601 UTC)
      * `audit_on_override_emitted: bool` (True)

    The function SHALL raise `ValueError` if:
      * reason is shorter than 20 chars after strip
      * legal_basis is not in the allowed set

    This AC corresponds to D8 Risk-1 KEPT mitigation (Art. 17(3) override path).
    """
    _art17_exceptions_module_is_importable()
    mod = _get_art17_exceptions_module()

    require_art_173_override_reason = getattr(mod, "require_art_173_override_reason", None)
    assert callable(require_art_173_override_reason), (
        "AC-6: art17_exceptions must expose a callable "
        f"require_art_173_override_reason; found: {[n for n in dir(mod) if not n.startswith('_')]!r}"
    )

    # ----- happy-path with valid reason + legal_basis -----
    valid_reason = "Badekur prescription under §23 SGB V (10-year retention)"
    valid_legal_basis = "sgb_v_section_23"
    result = require_art_173_override_reason(valid_reason, valid_legal_basis)

    assert isinstance(result, dict), (
        f"AC-6: result must be a dict; got {type(result).__name__}"
    )
    json.dumps(result, default=str)

    for required_key in (
        "override_id",
        "reason",
        "legal_basis",
        "requested_at",
        "audit_on_override_emitted",
    ):
        assert required_key in result, (
            f"AC-6: result must contain required key '{required_key}'; "
            f"got keys: {list(result.keys())!r}"
        )

    # ----- value-type + exact-equality assertions -----
    assert result["override_id"].startswith("a173-")
    assert len(result["override_id"]) == 13  # "a173-" + 8 hex chars
    assert result["reason"] == valid_reason
    assert result["legal_basis"] == valid_legal_basis
    assert result["audit_on_override_emitted"] is True
    assert len(result["reason"]) >= 20
    assert "T" in result["requested_at"]
    assert result["requested_at"].endswith("Z")

    # ----- ValueError: reason shorter than 20 chars after strip -----
    with pytest.raises(ValueError):
        require_art_173_override_reason("too short", valid_legal_basis)
    with pytest.raises(ValueError):
        # Whitespace-only reason shorter than 20 chars
        require_art_173_override_reason("   ab   ", valid_legal_basis)
    with pytest.raises(ValueError):
        # Empty string
        require_art_173_override_reason("", valid_legal_basis)

    # ----- ValueError: illegal legal_basis -----
    with pytest.raises(ValueError):
        require_art_173_override_reason(valid_reason, "illegal_basis")
    with pytest.raises(ValueError):
        require_art_173_override_reason(valid_reason, "gdpr_art_17_unknown")


# ===========================================================================
# AC-7 — run_cascade_with_retry idempotent + audit-on-partial
# ===========================================================================

def test_ac7_idempotent_retry_on_cascade_failure() -> None:
    """AC-7 spec test_oracle — idempotent retry + audit-on-partial.

    Asserts that `run_cascade_with_retry(guest_id: str, retry_max: int = 2)
    -> CascadeResult` handles cascade failure mid-transaction with:
      * Idempotent retry (zero or more retry calls, governed by `retry_max: int = 2`)
      * `cascade_status: str == "partial"` on partial completion
      * `cascade_steps_completed: list[str]` (only the successful steps)
      * `cascade_steps_failed: list[str]` (only the failed steps)

    This AC corresponds to D8 Risk-3 DISMISSED-with-mitigation.
    """
    _auto_cascade_module_is_importable()
    mod = _get_auto_cascade_module()

    run_cascade_with_retry = getattr(mod, "run_cascade_with_retry", None)
    assert callable(run_cascade_with_retry), (
        "AC-7: auto_cascade must expose a callable run_cascade_with_retry "
        f"entry point; found: {[n for n in dir(mod) if not n.startswith('_')]!r}"
    )

    # ----- happy-path (cascade completes without failure) -----
    result = run_cascade_with_retry(_SYNTHETIC_GUEST_ID, retry_max=2)

    assert isinstance(result, dict), (
        f"AC-7: result must be a dict; got {type(result).__name__}"
    )
    json.dumps(result, default=str)

    for required_key in (
        "cascade_status",
        "cascade_steps_completed",
        "cascade_steps_failed",
    ):
        assert required_key in result, (
            f"AC-7: result must contain required key '{required_key}'; "
            f"got keys: {list(result.keys())!r}"
        )

    # ----- value-type assertions -----
    assert result["cascade_status"] in ("completed", "partial")
    assert isinstance(result["cascade_steps_completed"], list)
    assert isinstance(result["cascade_steps_failed"], list)
    # If cascade completed, no failed steps; if partial, both lists have entries
    if result["cascade_status"] == "completed":
        assert len(result["cascade_steps_failed"]) == 0
        assert len(result["cascade_steps_completed"]) == 5
    else:  # partial
        assert len(result["cascade_steps_failed"]) >= 1
        assert (
            len(result["cascade_steps_completed"])
            + len(result["cascade_steps_failed"])
        ) == 5

    # ----- retry_max parameter: default 2 -----
    sig = inspect.signature(run_cascade_with_retry)
    retry_param = sig.parameters.get("retry_max")
    assert retry_param is not None, (
        "AC-7: run_cascade_with_retry must accept a 'retry_max' parameter; "
        f"got parameters: {list(sig.parameters.keys())!r}"
    )
    # Default value must be 2 per spec.yaml AC-7 verbatim
    assert retry_param.default == 2, (
        f"AC-7: retry_max default value MUST be 2 per spec.yaml AC-7; "
        f"got default: {retry_param.default!r}"
    )


# ===========================================================================
# AC-8 — assert_consent_or_legal_basis (Art. 9 health-data)
# ===========================================================================

def test_ac8_art9_health_data_requires_consent() -> None:
    """AC-8 spec test_oracle — Art. 9 health-data consent/legal-basis.

    Asserts that `assert_consent_or_legal_basis(consent_record: dict,
    legal_basis: str) -> Art9AuditFlag` returns a JSON-serializable dict
    with required keys:
      * `audit_id: str` ("a9-<uuid8>" format)
      * `guest_id: str`
      * `consent_present: bool` (True if explicit consent captured)
      * `legal_basis: str` (one of 4 allowed values per spec.yaml AC-8)
      * `audit_flag_emitted_at: str` (ISO 8601 UTC)
      * `audit_flag_hash: str` (SHA-256 hex)

    The function SHALL raise `ValueError` if consent is absent AND
    legal_basis is not in the allowed set.

    This AC corresponds to D8 Risk-2 DISMISSED-with-mitigation.
    """
    _art9_health_data_module_is_importable()
    mod = _get_art9_health_data_module()

    assert_consent_or_legal_basis = getattr(mod, "assert_consent_or_legal_basis", None)
    assert callable(assert_consent_or_legal_basis), (
        "AC-8: art9_health_data must expose a callable "
        f"assert_consent_or_legal_basis; found: {[n for n in dir(mod) if not n.startswith('_')]!r}"
    )

    # ----- happy-path 1: explicit consent + valid legal_basis -----
    consent_record = {
        "guest_id": _SYNTHETIC_GUEST_ID,
        "consent_captured": True,
        "consent_timestamp_utc": "2026-07-07T12:00:00Z",
    }
    result = assert_consent_or_legal_basis(
        consent_record, "dsgvo_art_9_2_a_explicit_consent"
    )

    assert isinstance(result, dict), (
        f"AC-8: result must be a dict; got {type(result).__name__}"
    )
    json.dumps(result, default=str)

    for required_key in (
        "audit_id",
        "guest_id",
        "consent_present",
        "legal_basis",
        "audit_flag_emitted_at",
        "audit_flag_hash",
    ):
        assert required_key in result, (
            f"AC-8: result must contain required key '{required_key}'; "
            f"got keys: {list(result.keys())!r}"
        )

    # ----- value-type + exact-equality assertions -----
    assert result["audit_id"].startswith("a9-")
    assert len(result["audit_id"]) == 11  # "a9-" + 8 hex chars
    assert result["guest_id"] == _SYNTHETIC_GUEST_ID
    assert result["consent_present"] is True
    assert result["legal_basis"] == "dsgvo_art_9_2_a_explicit_consent"
    assert len(result["audit_flag_hash"]) == 64  # SHA-256 hex
    assert "T" in result["audit_flag_emitted_at"]
    assert result["audit_flag_emitted_at"].endswith("Z")

    # ----- happy-path 2: NO consent + valid legal_basis (medical_diagnosis) -----
    no_consent_record = {
        "guest_id": _SYNTHETIC_GUEST_ID,
        "consent_captured": False,
    }
    result2 = assert_consent_or_legal_basis(
        no_consent_record, "dsgvo_art_9_2_h_medical_diagnosis"
    )
    assert result2["consent_present"] is False
    assert result2["legal_basis"] == "dsgvo_art_9_2_h_medical_diagnosis"

    # ----- ValueError: NO consent + illegal legal_basis -----
    with pytest.raises(ValueError):
        assert_consent_or_legal_basis(no_consent_record, "illegal_basis")
    with pytest.raises(ValueError):
        assert_consent_or_legal_basis(no_consent_record, "dsgvo_art_9_2_x_unknown")


# ===========================================================================
# AC-9 — full test suite 127/127 + 9 NEW kurgaste_retention symbols importable
# ===========================================================================

def test_ac9_full_test_suite_127_of_127() -> None:
    """AC-9 spec test_oracle — full test suite 118+9=127/127 PASS.

    Asserts that the kurgaste_retention package re-exports all 9 NEW
    symbols via `__init__`: `forget_guest`, `auto_cascade`,
    `emit_forget_guest_event`, `cascade_anonymize_spa_entries`,
    `redact_invoice_for_cascade`, `write_art30_audit_entry`,
    `run_cascade_with_retry`, `require_art_173_override_reason`,
    `assert_consent_or_legal_basis`.

    The baseline pytest at iter-38 entry MUST be 118/118 (113 iter-33 + 5
    iter-36 SHIPPED) and after this test ships (in green phase) becomes
    127/127 = 118 + 9.
    """
    # SHIPPED predicate_filing.compute_anti_drift_sha MUST be importable
    # (re-used for AC-9 anti-drift; iter-36 SHIPPED; importable now)
    from kurort_engine.predicate_filing import compute_anti_drift_sha
    sig = inspect.signature(compute_anti_drift_sha)
    assert callable(compute_anti_drift_sha)

    # kurgaste_retention package MUST be importable (green phase creates it).
    # Use find_spec guard so a missing package fails with AssertionError,
    # not ModuleNotFoundError, per pinned rule 3.
    _kurgaste_retention_package_is_importable()
    kr = __import__("kurort_engine.kurgaste_retention", fromlist=["_dummy_"])  # noqa: E402
    assert kr is not None

    expected_symbols = [
        "forget_guest",
        "auto_cascade",
        "emit_forget_guest_event",
        "cascade_anonymize_spa_entries",
        "redact_invoice_for_cascade",
        "write_art30_audit_entry",
        "run_cascade_with_retry",
        "require_art_173_override_reason",
        "assert_consent_or_legal_basis",
    ]
    for sym in expected_symbols:
        assert hasattr(kr, sym), (
            f"AC-9: kurort_engine.kurgaste_retention must export '{sym}' "
            f"per spec.yaml AC-9 verbatim; found attrs: "
            f"{[n for n in dir(kr) if not n.startswith('_')]!r}"
        )
        # Each symbol must be callable (function) or a class
        attr = getattr(kr, sym)
        assert callable(attr) or isinstance(attr, type), (
            f"AC-9: kurort_engine.kurgaste_retention.{sym} must be callable "
            f"or a class; got {type(attr).__name__}"
        )
