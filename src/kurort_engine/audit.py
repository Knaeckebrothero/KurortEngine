"""Append-only audit log with immutable, hash-stamped entries (AC-7).

The ``AuditEntry`` dataclass carries:

* ``recorded_at`` — ISO-8601 UTC timestamp, auto-captured at construction.
* ``actor``       — the responsible code path (``rates`` / ``exemptions``
                    / ``reporting``).
* ``payload``     — the auditable payload (canonical JSON).
* ``content_hash`` — SHA-256 hex digest of the canonical JSON of
                    ``recorded_at``, ``actor``, ``payload``. Auto-computed
                    in ``__post_init__`` when the caller does not supply
                    it; if a value is supplied it is stored as-is so the
                    caller can pre-stamp rows that have been verified
                    out-of-band (e.g. in batch import flows).

The dataclass is ``frozen=True``: any attempt to mutate a field raises
``dataclasses.FrozenInstanceError`` (a subclass of ``AttributeError``).
It is also ``kw_only=True`` so the auto-defaulted ``recorded_at`` field
can sit alongside the required ``actor`` / ``payload`` / ``content_hash``
fields without violating the "no default after required" dataclass rule.

The ``AuditLog`` container is a thin list-backed wrapper. It exposes
only ``append`` and iteration; there is intentionally no public
``.update()`` or ``.delete()`` method — the spec mandates append-only.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string with microseconds.

    Example: ``"2024-06-10T12:34:56.789012+00:00"``.
    """
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _canonical_json(*, recorded_at: str, actor: str, payload: str) -> bytes:
    """Return the canonical-JSON bytes of an ``AuditEntry``.

    Canonical-JSON is defined as ``json.dumps(d, sort_keys=True,
    separators=(",", ":"))`` — no whitespace, sorted keys, which makes the
    SHA-256 hash deterministic across Python versions and platforms.
    """
    return json.dumps(
        {"recorded_at": recorded_at, "actor": actor, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _compute_content_hash(*, recorded_at: str, actor: str, payload: str) -> str:
    """Return the SHA-256 hex digest of the canonical JSON of an entry."""
    return hashlib.sha256(
        _canonical_json(recorded_at=recorded_at, actor=actor, payload=payload)
    ).hexdigest()


@dataclass(frozen=True, kw_only=True)
class AuditEntry:
    """One immutable audit-log row.

    ``recorded_at`` is auto-captured at construction (UTC, ISO-8601 with
    microseconds). ``content_hash`` is auto-computed in ``__post_init__``
    from the canonical JSON of ``recorded_at`` / ``actor`` / ``payload``
    when the caller does not supply it; if a non-empty value is supplied
    it is stored as-is (callers may pre-stamp rows that have been
    verified out-of-band).
    """

    recorded_at: str = field(
        default_factory=_utc_now_iso,
        metadata={"description": "ISO-8601 UTC timestamp, captured at construction."},
    )
    actor: str
    payload: str
    content_hash: str = ""

    def __post_init__(self) -> None:
        """Auto-compute ``content_hash`` from the canonical JSON of the entry.

        If the caller did not supply a ``content_hash`` (or supplied an
        empty string), the SHA-256 hex digest of the canonical JSON of
        ``recorded_at`` / ``actor`` / ``payload`` is stored. If a
        non-empty value was supplied, it is preserved verbatim.
        """
        if not self.content_hash:
            computed = _compute_content_hash(
                recorded_at=self.recorded_at,
                actor=self.actor,
                payload=self.payload,
            )
            # Frozen dataclass: bypass __setattr__ to assign the computed hash.
            object.__setattr__(self, "content_hash", computed)


class AuditLog:
    """Append-only container of :class:`AuditEntry`.

    The backing store is a single class-level list shared across every
    instance — every ``AuditLog()`` invocation returns an instance bound to
    the same append-only store, so callers that obtain one log and then
    trigger an append elsewhere (e.g. via ``kurpaket_compliance.record_...``)
    see the entry on the original reference without any explicit wiring.
    Iteration preserves insertion order. There is intentionally no public
    ``.update()`` or ``.delete()`` method — the spec mandates append-only.
    """

    # Class-level shared store: every AuditLog() instance binds here.
    _shared_entries: list[AuditEntry] = []

    def __init__(self) -> None:
        # Bind the instance attribute to the class-level shared list so
        # all AuditLog() instances see each other's appends.
        self._entries = AuditLog._shared_entries

    def append(self, entry: AuditEntry) -> None:
        """Append ``entry`` to the log. Returns ``None``."""
        self._entries.append(entry)

    @property
    def entries(self) -> list[AuditEntry]:
        """Public snapshot accessor for the shared append-only log.

        Returns the class-level shared list bound at ``__init__`` time so
        that downstream consumers (e.g., ``kurpaket_compliance`` AC9 scan)
        can read the current entries without filtering or coercion. The
        returned reference is the LIVE shared list — mutating it would
        violate the append-only invariant; iterate it, do not modify it.
        Per AC-6 contract, ``payload`` is preserved as the caller-supplied
        shape (``str`` for ``kurpaket_compliance`` JSON-canonical entries,
        ``dict`` for ``a11y.guest_pwa`` self-attest entries).
        """
        return self._entries

    def __iter__(self) -> Iterator[AuditEntry]:
        """Yield entries in append order."""
        return iter(self._entries)

    def __len__(self) -> int:
        return len(self._entries)