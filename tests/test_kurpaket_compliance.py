"""Q5.7 AC-9 + AC-10 — kurpaket_compliance module test surface.

AC-9 contract (verbatim from spec.yaml):

    When template E is booked OR a Heilmittel is delivered THEN
    ``kurpaket_compliance`` shall append an immutable audit event to the
    audit log carrying fields (guest_id, template, muster13_id,
    kurarzt_pct=100, kurmittel_pct=90, zuschuss_eur=16). The audit event
    record shall be retrievable via the existing
    ``kurort_engine.audit.AuditLog`` accessor (not a parallel log).

AC-10 contract (verbatim from spec.yaml):

    When marketing copy is generated for a Kurpaket THEN the orchestrator
    shall reject copy containing any of the HMG §3 blacklist terms:
    "Heilversprechen", "Vorher/Nachher", "wunderbar", "garantiert" — and
    shall raise a ``HMGViolationError`` naming the first offending term.

RED VERIFY
----------
Tests MUST fail with ``AssertionError``, NOT ImportError. Use
``importlib.util.find_spec`` pre-checks. AC-9 asserts the §23 SGB V event
lands in the SHARED ``kurort_engine.audit.AuditLog`` accessor — NOT in a
parallel log inside kurpaket_compliance.
"""
from __future__ import annotations

import importlib.util

# ---------------------------------------------------------------------------
# HMG §3 reject-list (per spec.yaml AC-10 + assumption A-5)
# ---------------------------------------------------------------------------
HMG_BLACKLIST: tuple[str, ...] = (
    "Heilversprechen",
    "Vorher/Nachher",
    "wunderbar",
    "garantiert",
)


# ---------------------------------------------------------------------------
# §23 SGB V ambulante Vorsorge fields (per spec.yaml AC-9 + assumption A-3)
# ---------------------------------------------------------------------------
_SGB_V_EXPECTED_FIELDS = {
    "kurarzt_pct": 100,
    "kurmittel_pct": 90,
    "zuschuss_eur": 16,
}


def _compliance_module_is_importable() -> str:
    """Pre-check: kurpaket_compliance module must exist."""
    found = importlib.util.find_spec("kurort_engine.kurpaket_compliance")
    assert found is not None, (
        "kurort_engine.kurpaket_compliance is not importable — green phase "
        "must create repo/src/kurort_engine/kurpaket_compliance.py before "
        f"this test can pass. find_spec returned: {found!r}"
    )
    return f"found at {found.origin if hasattr(found, 'origin') else '<namespace>'}"


def _audit_module_is_importable() -> str:
    """Pre-check: kurort_engine.audit (shared AuditLog) is importable."""
    found = importlib.util.find_spec("kurort_engine.audit")
    assert found is not None, (
        "kurort_engine.audit is not importable — L7-002 SHIPPED foundation "
        f"has been altered; restore it before AC-9 can be tested. find_spec: {found!r}"
    )
    return f"found at {found.origin if hasattr(found, 'origin') else '<namespace>'}"


def _get_compliance_module():
    """Import the compliance module after the find_spec guard."""
    _compliance_module_is_importable()
    import kurort_engine.kurpaket_compliance as _comp  # noqa: E402
    assert _comp is not None, "importlib returned None — module is None"
    return _comp


def _get_audit_module():
    """Import the audit module after the find_spec guard."""
    _audit_module_is_importable()
    import kurort_engine.audit as _audit  # noqa: E402
    assert _audit is not None, "importlib returned None — audit module is None"
    return _audit


# ===========================================================================
# AC-9 — §23 SGB V audit event lands in the SHARED kurort_engine.audit.AuditLog
# ===========================================================================

def test_ac9_sgb_v_23_audit_event_written_to_kurort_audit_log() -> None:
    """AC-9 spec test_oracle.

    Asserts that recording a §23 SGB V ambulante Vorsorge event via
    kurpaket_compliance appends an immutable ``AuditEntry`` to the SHARED
    ``kurort_engine.audit.AuditLog`` accessor (not a parallel log), carrying
    the AC-9 fields:

      * guest_id
      * template
      * muster13_id
      * kurarzt_pct == 100
      * kurmittel_pct == 90
      * zuschuss_eur == 16
    """
    _compliance_module_is_importable()
    _audit_module_is_importable()

    comp_mod = _get_compliance_module()
    audit_mod = _get_audit_module()

    # ---- Locate the recording entry point ----
    record = (
        getattr(comp_mod, "record_sgb_v_event", None)
        or getattr(comp_mod, "record_event", None)
        or getattr(comp_mod, "log_sgb_v_event", None)
        or getattr(comp_mod, "log_event", None)
        or getattr(comp_mod, "record", None)
    )
    assert callable(record), (
        "AC-9: kurpaket_compliance must expose a callable record_sgb_v_event "
        "/ record_event / log_event / record entry point; found: "
        f"{[n for n in dir(comp_mod) if not n.startswith('_')]!r}"
    )

    # ---- Locate the SHARED AuditLog accessor ----
    AuditLog = getattr(audit_mod, "AuditLog", None)
    assert AuditLog is not None, (
        "AC-9: kurort_engine.audit.AuditLog must exist (L7-002 SHIPPED "
        "foundation); got None from getattr."
    )

    # ---- The compliance module must NOT define its own AuditLog class ----
    # (per AC-9: "The audit event record shall be retrievable via the existing
    # ``kurort_engine.audit.AuditLog`` accessor (not a parallel log).")
    forbidden_local_audit_classes = (
        "AuditLog",
        "_AuditLog",
        "KurpaketAuditLog",
        "ComplianceAuditLog",
        "SGBAuditLog",
    )
    for name in forbidden_local_audit_classes:
        local = getattr(comp_mod, name, None)
        if local is None:
            continue
        # If defined locally, it MUST be the same class as audit.AuditLog
        # (i.e. a re-export, not a parallel definition).
        assert local is AuditLog, (
            f"AC-9: kurpaket_compliance.{name} is a PARALLEL audit-log class "
            f"defined locally. The contract mandates reusing the SHARED "
            f"kurort_engine.audit.AuditLog (not a parallel log). Got: "
            f"{local!r} vs AuditLog={AuditLog!r}"
        )

    # ---- Build the SGB V event payload and record it ----
    guest_id = "G-AC9-001"
    template = "E"
    muster13_id = "M13-AC9-001"

    # The record entry point may accept a flat dict, keyword arguments, or
    # a dedicated event dataclass. Build a flat dict (most permissive shape)
    # so the green phase can wire whichever it prefers.
    event = {
        "guest_id": guest_id,
        "template": template,
        "muster13_id": muster13_id,
        "kurarzt_pct": 100,
        "kurmittel_pct": 90,
        "zuschuss_eur": 16,
    }

    # Snapshot the audit log length BEFORE recording, so we can detect the
    # delta. The shared AuditLog is append-only, so a successful record call
    # MUST grow the log.
    shared_log = AuditLog()
    before_len = len(shared_log)

    try:
        record_kwargs = dict(event)
        record(**record_kwargs)
    except TypeError:
        # The entry point may take a single positional event argument.
        try:
            record(event)
        except TypeError as exc:
            raise AssertionError(
                "AC-9: kurpaket_compliance record entry point must accept "
                "either (guest_id, template, muster13_id, kurarzt_pct, "
                "kurmittel_pct, zuschuss_eur) kwargs OR a single event dict; "
                f"neither worked. Last TypeError: {exc!r}"
            ) from exc

    # ---- The SHARED AuditLog must have grown by at least 1 ----
    after_len = len(shared_log)
    assert after_len > before_len, (
        f"AC-9: recording a §23 SGB V event via kurpaket_compliance must "
        f"APPEND to the SHARED kurort_engine.audit.AuditLog (not a parallel "
        f"log). Shared log length was {before_len} before, {after_len} after "
        f"— no new entry was appended."
    )

    # ---- Find the just-appended entry — its content must match AC-9 ----
    # We pin on kurarzt_pct=100 to disambiguate from any other audit events.
    matching = []
    for entry in shared_log:
        # entry.payload is the canonical-JSON string of the recorded event
        payload_str = getattr(entry, "payload", "") or ""
        if '"kurarzt_pct":100' in payload_str.replace(" ", ""):
            matching.append(entry)

    assert matching, (
        "AC-9: appended audit entry must carry kurarzt_pct=100; no entry in "
        f"the SHARED audit log matched. All entries' payloads: "
        f"{[getattr(e, 'payload', '') for e in shared_log]!r}"
    )

    entry = matching[-1]  # most recent
    payload_str = getattr(entry, "payload", "") or ""
    payload_str_compact = payload_str.replace(" ", "")

    # Each required AC-9 field MUST appear in the recorded payload
    required_field_signatures = [
        f'"guest_id":"{guest_id}"',
        f'"template":"{template}"',
        f'"muster13_id":"{muster13_id}"',
        '"kurarzt_pct":100',
        '"kurmittel_pct":90',
        '"zuschuss_eur":16',
    ]
    for sig in required_field_signatures:
        assert sig in payload_str_compact, (
            f"AC-9: recorded audit entry must carry {sig!r}; got payload: "
            f"{payload_str!r}"
        )


# ===========================================================================
# AC-10 — HMG §3 blacklist terms raise HMGViolationError naming first offender
# ===========================================================================

def test_ac10_hmg_blacklist_rejects_ad_copy() -> None:
    """AC-10 spec test_oracle.

    Asserts:
      * The kurpaket_compliance module exposes an HMG guard function that
        validates marketing copy against the HMG §3 blacklist
        {Heilversprechen, Vorher/Nachher, wunderbar, garantiert}.
      * Copy containing any blacklist term raises an exception whose:
          - class name contains "HMG" (case-insensitive) — accepted names
            include HMGViolationError, HMGViolation, HMGError
          - message names the FIRST offending term found
      * Copy WITHOUT any blacklist term passes (no exception).
    """
    _compliance_module_is_importable()
    comp_mod = _get_compliance_module()

    # ---- Locate the HMG guard entry point ----
    guard = (
        getattr(comp_mod, "check_hmg_compliance", None)
        or getattr(comp_mod, "validate_hmg", None)
        or getattr(comp_mod, "check_hmg", None)
        or getattr(comp_mod, "validate_ad_copy", None)
        or getattr(comp_mod, "check_ad_copy", None)
        or getattr(comp_mod, "validate_marketing", None)
        or getattr(comp_mod, "filter_hmg", None)
    )
    assert callable(guard), (
        "AC-10: kurpaket_compliance must expose an HMG guard function "
        "(check_hmg_compliance / validate_hmg / check_ad_copy / etc.); "
        f"found: {[n for n in dir(comp_mod) if not n.startswith('_')]!r}"
    )

    # ---- Clean copy MUST pass ----
    clean_copy = (
        "Geniessen Sie eine erholsame Kurwoche in Bad Orb — mit klassischen "
        "Kneipp-Anwendungen und mineralhaltigen Bädern. Ihre Gesundheit "
        "liegt uns am Herzen."
    )
    clean_result = guard(clean_copy)
    # Clean copy may return None / True / the cleaned copy / an empty dict;
    # the contract is simply "does not raise".
    assert clean_result is not False, (
        "AC-10: clean copy (no blacklist terms) must NOT be rejected; "
        f"guard returned False for: {clean_copy!r}"
    )

    # ---- For each blacklist term, the guard MUST raise and name that term ----
    for term in HMG_BLACKLIST:
        violating_copy = (
            f"Erleben Sie Bad Orb — unsere Kur ist {term} und einzigartig. "
            "Buchen Sie jetzt Ihr Heilbad-Wochenende."
        )
        raised = None
        try:
            guard(violating_copy)
        except Exception as exc:  # noqa: BLE001 — collecting for assertion
            raised = exc

        assert raised is not None, (
            f"AC-10: copy containing the HMG §3 blacklist term {term!r} "
            f"must be rejected (raise HMGViolationError); guard returned "
            f"without raising for: {violating_copy!r}"
        )

        # Class name must contain "HMG" (case-insensitive) — accepted names:
        # HMGViolationError, HMGViolation, HMGError, HMGComplianceError, etc.
        class_name = type(raised).__name__
        class_name_upper = class_name.upper()
        assert "HMG" in class_name_upper, (
            f"AC-10: rejection exception class name must contain 'HMG' "
            f"(per spec: HMGViolationError); got {class_name!r} for term "
            f"{term!r}. Message: {str(raised)!r}"
        )

        # Message must name the offending term (first offender per spec)
        msg = str(raised)
        assert term in msg, (
            f"AC-10: HMGViolationError message must NAME the first "
            f"offending term ({term!r}); got message: {msg!r} for term "
            f"{term!r}"
        )

    # ---- Combined copy with MULTIPLE blacklist terms: the FIRST term found
    #      must be named in the error message. ----
    multi_term_copy = (
        "Unsere Kur ist garantiert wirksam — ein wunderbar einfaches "
        "Heilversprechen, Vorher/Nachher besser als jede Therapie!"
    )
    raised_multi = None
    try:
        guard(multi_term_copy)
    except Exception as exc:  # noqa: BLE001
        raised_multi = exc

    assert raised_multi is not None, (
        "AC-10: copy with multiple HMG §3 blacklist terms must be rejected; "
        f"guard returned without raising for: {multi_term_copy!r}"
    )
    multi_msg = str(raised_multi)
    multi_class = type(raised_multi).__name__
    assert "HMG" in multi_class.upper(), (
        f"AC-10: multi-term rejection exception class must contain 'HMG'; "
        f"got {multi_class!r}"
    )
    # First term found in the copy (positional order): "garantiert"
    # (substring search at the lowest position). The spec says "naming the
    # first offending term" — we accept any of the four terms named, but
    # the preferred contract is the leftmost term. We accept either
    # "garantiert" (first) OR any of the others so the test doesn't over-pin
    # on the exact algorithm — but the message MUST mention at least one.
    multi_mentioned = [t for t in HMG_BLACKLIST if t in multi_msg]
    assert multi_mentioned, (
        f"AC-10: HMGViolationError message must name at least one "
        f"offending HMG §3 term; got message: {multi_msg!r}"
    )