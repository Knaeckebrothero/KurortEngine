"""Self-attestation dataclass + factory for kurort_engine.a11y.guest_pwa.

Per ``spec/a11y_guest_pwa/spec.yaml`` AC-1 EARS: the package-level
``SELF_ATTESTATION_TS`` module-level constant is the authoritative
ISO-8601 timestamp for the first-import audit-log event. This module
provides a STRUCTURED ``SelfAttestation`` dataclass for downstream code
that wants to represent an attestation explicitly (e.g. signed export
bundles, signature_bridge handoffs, audit-export tooling).

Mirrors the SHIPPED ``kurort_engine.audit.AuditEntry`` contract:
``frozen=True`` + ``kw_only=True`` for hash stability; ``content_hash``
auto-computed in ``__post_init__`` from canonical-JSON of the 3 fields.

Public surface (re-exported by ``kurort_engine.a11y.guest_pwa.__init__``
if needed, otherwise consumed directly):
  * ``SelfAttestation`` — dataclass (frozen, kw_only)
  * ``mint_self_attestation(profile_id)`` — factory

The factory default claim cites BFSG-EAA §3(1) per spec.yaml AC-1 EARS
(verbatim: "a non-empty claim string referencing BFSG-EAA §3(1) and EN
301 549 V3.2.1 / WCAG 2.1 AA"). ``ts`` is sourced from
``SELF_ATTESTATION_TS`` (package constant) for determinism + idempotence.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

SELF_ATTESTATION_TS: str = "2026-07-10"

_DEFAULT_CLAIM: str = (
    "BFSG-EAA §3(1) self-attestation: kurort_engine.a11y.guest_pwa "
    "asserts WCAG 2.1 AA + EN 301 549 V3.2.1 conformance for the Hotel "
    "Rheinland Bad Orb guest PWA booking flow."
)


@dataclass(frozen=True, kw_only=True)
class SelfAttestation:
    """Immutable, keyword-only self-attestation record.

    Fields:
      profile_id: stable identifier of the attesting tenant/profile
                  (e.g. ``"hotel-rheinland.bad-orb.guest-pwa"``).
      ts: ISO-8601 date ``YYYY-MM-DD`` — sourced from
          ``SELF_ATTESTATION_TS`` for determinism.
      claim: human-readable claim string referencing BFSG-EAA §3(1).
      content_hash: SHA-256 hex digest of canonical-JSON
          (sort_keys=True, separators=(",", ":")) of
          ``(profile_id, ts, claim)``. Auto-computed in ``__post_init__``.
    """

    profile_id: str
    ts: str = SELF_ATTESTATION_TS
    claim: str = _DEFAULT_CLAIM
    content_hash: str = field(init=False, default="")

    def __post_init__(self) -> None:
        # Compute the content_hash from the canonical JSON of the 3 input
        # fields (NOT including content_hash itself — chicken-and-egg).
        canonical = json.dumps(
            [self.profile_id, self.ts, self.claim],
            sort_keys=True,
            separators=(",", ":"),
        )
        # ``object.__setattr__`` is required because the dataclass is
        # ``frozen=True`` — direct attribute assignment raises FrozenInstanceError.
        object.__setattr__(
            self, "content_hash", hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        )


def mint_self_attestation(profile_id: str) -> SelfAttestation:
    """Factory: build a ``SelfAttestation`` with the canonical defaults.

    ``ts`` defaults to ``SELF_ATTESTATION_TS`` (``"2026-07-10"``) and
    ``claim`` defaults to the BFSG-EAA §3(1) marker string. ``profile_id``
    is required (no default) — the caller must declare who is attesting.
    """
    return SelfAttestation(profile_id=profile_id)