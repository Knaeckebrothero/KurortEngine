"""Signature bridge from Meldeschein to a11y.guest_pwa (Pattern F chain extension).

Per ``spec/a11y_guest_pwa/spec.yaml`` AC-4 EARS: ``kurort_engine.a11y.guest_pwa``
shall Pattern F chain-extend 4 SHIPPED modules (audit + kurkarte_wallet +
meldeschein + f5_t2 dispatcher). This module is the meldeschein half of the
chain — it provides a graceful import fallback for the future-iter Meldeschein
``meldeschein_signature_v1`` API that the AC-4 anchor string references.

Per ``spec.yaml`` not_included (L167): the meldeschein signature API is a
forward-anchor string, NOT a literal module function. The try/except
``ImportError`` wrapper ensures this module imports cleanly on Phase 7b
without depending on the future-iter signature API landing.

Public surface:
  * ``meldeschein_signature_v1`` — the anchor symbol (or graceful stub if
    the underlying API is not yet implemented in the SHIPPED meldeschein
    package — currently the case).
  * ``has_meldeschein_signature`` — bool indicating whether the bridge
    resolved to a real implementation or a stub.
  * ``sign_a11y_attestation(profile_id, claim)`` — convenience helper
    that combines SelfAttestation + signature_v1 if available.

``kurort_engine.meldeschein`` IS imported (Pattern F import line) so
that the AC-4 anchor regex (`from kurort_engine.X import ...`) finds
the literal ``meldeschein`` top-level module in ``__init__.py`` source.
"""
from __future__ import annotations

from typing import Any

# Pattern F import — the module name ``meldeschein`` is the AC-4 anchor
# and MUST appear as a top-level ``import kurort_engine.meldeschein``
# line in ``kurort_engine.a11y.guest_pwa.__init__`` source.
#
# We wrap the symbol import in try/except ImportError because
# ``meldeschein_signature_v1`` is a forward-anchor (per spec.yaml AC-4
# not_included L167), not a literal function in the SHIPPED
# ``kurort_engine.meldeschein`` package.
try:
    from kurort_engine.meldeschein import (
        meldeschein_signature_v1,  # type: ignore[attr-defined]  # noqa: F401
    )

    _HAS_MELDESCHEIN_SIGNATURE: bool = True
except ImportError:
    # Future-iter: when the SHIPPED meldeschein package exposes
    # ``meldeschein_signature_v1``, this branch is dead code and the
    # resolved binding above takes effect.
    meldeschein_signature_v1 = None  # type: ignore[assignment,misc]
    _HAS_MELDESCHEIN_SIGNATURE = False


def has_meldeschein_signature() -> bool:
    """Return True iff ``meldeschein_signature_v1`` resolved to a real binding."""
    return _HAS_MELDESCHEIN_SIGNATURE


def sign_a11y_attestation(profile_id: str, claim: str) -> dict[str, Any]:
    """Bridge: combine a SelfAttestation with the Meldeschein signature if available.

    Args:
      profile_id: stable identifier of the attesting tenant/profile.
      claim: human-readable claim string referencing BFSG-EAA §3(1).

    Returns:
      A dict with keys ``profile_id``, ``claim``, ``signed`` (bool),
      and optionally ``signature`` (when the real
      ``meldeschein_signature_v1`` is wired up). When the signature
      function is unavailable, the dict records ``signed=False`` with
      a stable ``fallback_reason`` so downstream verification tooling
      can detect the Phase 7b stub state without breaking.
    """
    result: dict[str, Any] = {
        "profile_id": profile_id,
        "claim": claim,
        "signed": False,
    }
    if _HAS_MELDESCHEIN_SIGNATURE and meldeschein_signature_v1 is not None:
        try:
            result["signature"] = meldeschein_signature_v1(profile_id, claim)
            result["signed"] = True
        except Exception as exc:  # noqa: BLE001 — bridge resilience
            result["signed"] = False
            result["fallback_reason"] = type(exc).__name__
    else:
        result["fallback_reason"] = "meldeschein_signature_v1_unavailable"
    return result