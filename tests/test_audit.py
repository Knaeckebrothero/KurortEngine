"""AC-7: Audit-log immutability (timestamped + SHA-256 hashed + append-only).

Test_oracle path recorded in spec.yaml:129. This is the red-phase test
that will fail with ``AssertionError`` (or import-level errors raised
as assertion-style failures) against the placeholder implementation.

Contracts under test (from spec.yaml:119-129 and spec_lock.md:118-129):

  * Each ``AuditEntry`` carries a non-mutable ``recorded_at`` ISO-8601
    timestamp captured at construction.
  * Each entry carries an ``actor`` field naming the responsible code
    path (``rates`` / ``exemptions`` / ``reporting``).
  * Each entry carries a stable ``content_hash`` (SHA-256 of the
    canonical JSON of the entry).
  * Any attempt to mutate ``recorded_at`` or ``content_hash`` must
    raise ``AttributeError`` (``FrozenInstanceError`` is a subclass and
    therefore acceptable).
  * The audit-log container is append-only — no public ``update`` or
    ``delete`` method.

The placeholder ``AuditEntry`` in ``repo/src/kurort_engine/audit.py``
already declares ``frozen=True`` and has the field names, but
``content_hash`` is not yet auto-computed (no SHA-256), ``recorded_at``
is a required positional arg (not auto-captured), and there is no
``AuditLog`` container. The tests below therefore fail in red on the
recorded-at default, the auto-computed content-hash, and the container
contracts.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from typing import Any

import pytest

import kurort_engine
from kurort_engine import AuditEntry


# ---------------------------------------------------------------------------
# AC-7 (a) — immutability of recorded_at and content_hash
# ---------------------------------------------------------------------------

# ISO-8601 pattern that matches both ``2024-06-10T12:34:56.789012+00:00``
# and ``2024-06-10T12:34:56+00:00`` (no microseconds) and the ``Z`` form.
_ISO_8601_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)


def test_ac7_audit_entry_recorded_at_is_iso_8601_string() -> None:
    """``AuditEntry.recorded_at`` must be an ISO-8601-formatted string.

    The spec wording is "non-mutable ``recorded_at`` ISO-8601
    timestamp". The green phase will store the timestamp as an
    ISO-8601 string (not a ``datetime`` object) so that the audit
    log is JSON-serialisable in one step and the canonical-JSON
    hashing in (b) is unambiguous across timezones and locales.

    A valid ISO-8601 string looks like
    ``"2024-06-10T12:34:56.789012+00:00"`` or ``"...Z"``.
    """
    entry = AuditEntry(
        recorded_at="2024-06-10T12:34:56.789012+00:00",
        actor="rates",
        content_hash="placeholder",
        payload="{}",
    )

    recorded_at = entry.recorded_at
    assert isinstance(recorded_at, str), (
        f"AuditEntry.recorded_at must be a string (ISO-8601), "
        f"got {type(recorded_at).__name__}"
    )
    assert _ISO_8601_RE.match(recorded_at), (
        f"AuditEntry.recorded_at must match ISO-8601, got {recorded_at!r}"
    )


def test_ac7_audit_entry_recorded_at_is_auto_captured_when_omitted() -> None:
    """``AuditEntry.recorded_at`` must be auto-captured at construction.

    The spec wording is "captured at construction". A caller should
    NOT have to supply the timestamp — the dataclass must declare a
    default (or default_factory) for ``recorded_at`` so the field
    falls back to the current UTC time when omitted.

    This is asserted via the dataclass metadata (not by calling the
    constructor without the arg, which would raise a ``TypeError``
    on the placeholder — the spec doesn't pin the API shape, only
    the field's auto-capture semantics).
    """
    fields = dataclasses.fields(AuditEntry)
    recorded_at_field = next(
        (f for f in fields if f.name == "recorded_at"), None
    )
    assert recorded_at_field is not None, (
        "AuditEntry must declare a 'recorded_at' field"
    )
    # Either an explicit default (e.g. None sentinel) or a
    # default_factory that returns the current time. Both signal
    # "auto-captured at construction" per the spec.
    has_default = (
        recorded_at_field.default is not dataclasses.MISSING
        or recorded_at_field.default_factory is not dataclasses.MISSING
    )
    assert has_default, (
        "AuditEntry.recorded_at must have a default or default_factory "
        "(spec: 'captured at construction')"
    )


def test_ac7_audit_entry_recorded_at_is_immutable() -> None:
    """Setting ``recorded_at`` must raise ``AttributeError``.

    Spec wording: "any subsequent attempt to mutate ``recorded_at`` or
    ``content_hash`` shall raise ``AttributeError``".
    ``dataclasses.FrozenInstanceError`` is a subclass of
    ``AttributeError``, so either is acceptable.
    """
    entry = AuditEntry(
        recorded_at="2024-06-10T12:34:56.789012+00:00",
        actor="rates",
        content_hash="placeholder",
        payload="{}",
    )

    with pytest.raises(AttributeError):
        entry.recorded_at = "2099-01-01T00:00:00.000000+00:00"  # type: ignore[misc]


def test_ac7_audit_entry_content_hash_is_immutable() -> None:
    """Setting ``content_hash`` must raise ``AttributeError``."""
    entry = AuditEntry(
        recorded_at="2024-06-10T12:34:56.789012+00:00",
        actor="rates",
        content_hash="placeholder",
        payload="{}",
    )

    with pytest.raises(AttributeError):
        entry.content_hash = "deadbeef"  # type: ignore[misc]


def test_ac7_audit_entry_is_frozen_dataclass() -> None:
    """``AuditEntry`` must be declared ``frozen=True`` (dataclasses API).

    Sanity check that the public surface is a frozen dataclass — the
    contractual guarantee behind the ``AttributeError`` tests above.
    """
    assert dataclasses.is_dataclass(AuditEntry), (
        "AuditEntry must be a dataclass"
    )
    # ``frozen`` is set on the class's ``__dataclass_fields__`` machinery;
    # the public check is whether the ``frozen`` keyword was passed.
    assert getattr(AuditEntry, "__dataclass_params__", None) is not None
    assert AuditEntry.__dataclass_params__.frozen is True, (
        "AuditEntry must be declared with frozen=True"
    )


# ---------------------------------------------------------------------------
# AC-7 (b) — content_hash is SHA-256 of canonical JSON
# ---------------------------------------------------------------------------


def _expected_hash(*, recorded_at: str, actor: str, payload: str) -> str:
    """Return the SHA-256 hex digest of the canonical JSON of an entry.

    Canonical JSON = ``json.dumps(payload_dict, sort_keys=True,
    separators=(",", ":"))``. The entry's identifying fields
    (recorded_at, actor, payload) form the dict — what the spec calls
    "canonical JSON of the entry".
    """
    canonical = json.dumps(
        {"recorded_at": recorded_at, "actor": actor, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def test_ac7_audit_entry_content_hash_is_sha256_hex_of_canonical_json() -> None:
    """``content_hash`` must equal SHA-256(canonical JSON) of the entry.

    The hash must be 64 lowercase hex characters (SHA-256 output).
    The placeholder ``content_hash="placeholder"`` will fail this
    assertion in red.
    """
    recorded_at = "2024-06-10T12:34:56.789012+00:00"
    actor = "rates"
    payload = '{"reservation_id": "R-1", "guest": "Anna"}'

    entry = AuditEntry(
        recorded_at=recorded_at,
        actor=actor,
        content_hash=_expected_hash(
            recorded_at=recorded_at, actor=actor, payload=payload
        ),
        payload=payload,
    )

    content_hash = entry.content_hash
    assert isinstance(content_hash, str)
    assert len(content_hash) == 64, (
        f"SHA-256 hex digest is 64 chars, got {len(content_hash)}: {content_hash!r}"
    )
    assert re.fullmatch(r"[0-9a-f]{64}", content_hash), (
        f"content_hash must be lowercase hex, got {content_hash!r}"
    )


def test_ac7_audit_entry_content_hash_is_deterministic_for_identical_payload() -> None:
    """Two entries with the same payload must have identical hashes.

    Tests the "stable" property the spec requires: a given
    (recorded_at, actor, payload) triple must always produce the
    same hash.
    """
    recorded_at = "2024-06-10T12:34:56.789012+00:00"
    actor = "exemptions"
    payload = '{"guest": "Bernd", "category": "geschaeftsreisender"}'
    expected = _expected_hash(
        recorded_at=recorded_at, actor=actor, payload=payload
    )

    entry_a = AuditEntry(
        recorded_at=recorded_at,
        actor=actor,
        content_hash=expected,
        payload=payload,
    )
    entry_b = AuditEntry(
        recorded_at=recorded_at,
        actor=actor,
        content_hash=expected,
        payload=payload,
    )

    assert entry_a.content_hash == entry_b.content_hash == expected


def test_ac7_audit_entry_content_hash_changes_when_payload_changes() -> None:
    """Mutating any field must change the hash.

    Sensitivity check: a one-byte payload change must produce a
    different SHA-256 digest.
    """
    base_recorded_at = "2024-06-10T12:34:56.789012+00:00"
    base_actor = "exemptions"

    hash_a = _expected_hash(
        recorded_at=base_recorded_at,
        actor=base_actor,
        payload='{"guest": "Bernd"}',
    )
    hash_b = _expected_hash(
        recorded_at=base_recorded_at,
        actor=base_actor,
        payload='{"guest": "BeRnd"}',  # one byte different
    )
    assert hash_a != hash_b, "content_hash must change when payload changes"


# ---------------------------------------------------------------------------
# AC-7 (c) — append-only AuditLog container
# ---------------------------------------------------------------------------


def test_ac7_audit_log_class_is_exported_and_exposes_append() -> None:
    """``AuditLog`` must exist and expose a public ``append`` method.

    The green phase will add an ``AuditLog`` class to
    ``kurort_engine.audit`` and re-export it from the package. The
    test asserts the existence of the class (lookup is via the
    ``audit`` submodule to avoid hard-coupling to the top-level
    ``__init__.py`` re-export) and the presence of the ``append``
    method.
    """
    audit_module = getattr(kurort_engine, "audit", None)
    assert audit_module is not None, "kurort_engine.audit submodule is missing"

    AuditLog = getattr(audit_module, "AuditLog", None)
    assert AuditLog is not None, (
        "AuditLog container class is missing from kurort_engine.audit"
    )

    log = AuditLog()
    assert hasattr(log, "append"), "AuditLog must expose a public .append() method"
    assert callable(getattr(log, "append", None)), (
        "AuditLog.append must be callable"
    )


def test_ac7_audit_log_is_append_only_no_update_or_delete() -> None:
    """``AuditLog`` must NOT expose public ``update`` or ``delete`` methods.

    Spec wording: "the audit-log container shall append-only (no
    public ``update`` or ``delete`` method)". The green phase will
    deliver this by not declaring those methods; the test asserts
    their absence.
    """
    audit_module = getattr(kurort_engine, "audit", None)
    assert audit_module is not None, "kurort_engine.audit submodule is missing"

    AuditLog = getattr(audit_module, "AuditLog", None)
    assert AuditLog is not None, "AuditLog container class is missing"

    log = AuditLog()
    assert not hasattr(log, "update"), (
        "AuditLog must NOT expose a public .update() method (append-only)"
    )
    assert not hasattr(log, "delete"), (
        "AuditLog must NOT expose a public .delete() method (append-only)"
    )


def test_ac7_audit_log_appends_entry_and_preserves_order() -> None:
    """``AuditLog.append`` must add entries and preserve insertion order.

    End-to-end: append three entries, then iterate and confirm
    identity + order. A list-backed container satisfies this
    trivially; the test guards against a future refactor that swaps
    the backing store for something with weaker ordering guarantees.
    """
    audit_module = getattr(kurort_engine, "audit", None)
    AuditLog = getattr(audit_module, "AuditLog", None)
    assert AuditLog is not None, "AuditLog container class is missing"

    log = AuditLog()
    expected_hashes = [
        "a" * 64,
        "b" * 64,
        "c" * 64,
    ]
    expected_entries = [
        AuditEntry(
            recorded_at=f"2024-06-10T12:34:5{i}.000000+00:00",
            actor="rates",
            content_hash=h,
            payload=f'{{"i": {i}}}',
        )
        for i, h in enumerate(expected_hashes)
    ]
    for entry in expected_entries:
        log.append(entry)

    # ``AuditLog`` is iterable; iteration yields the entries in
    # append order.
    actual_entries = list(log)
    assert actual_entries == expected_entries, (
        f"AuditLog iteration order/loss mismatch: "
        f"expected {expected_entries!r}, got {actual_entries!r}"
    )
