"""kurort_engine.avv_kaskade.processor — Art. 28(1) processor registration.

Iter-28 (Developer) — Phase 5 Tactical Green.

AC-1:   register_processor(processor) computes avv_hash and appends.
AC-1.1: register_processor(processor) raises ValueError on expired AVV.

The module-level ``_REGISTRY`` list is append-only — callers can read but never
mutate. The ``register_processor`` function is the sole append site and enforces
the Art. 28(1) DSGVO date invariant ``avv_signed_date < avv_expiry_date``.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from kurort_engine.avv_kaskade._validation import (
    assert_date_constraint,
    compute_avv_hash,
)


class Processor:
    """Art. 28(1) processor registration record (mutable to allow
    ``sub_processors`` assignment + post-init ``avv_hash`` set).

    The constructor mirrors the AC-1 EARS fields:

      - processor_id: stable identity used by AC-2 / AC-3 lookups.
      - controller_name / controller_address: appear in AC-3 verantwortlicher.
      - avv_signed_date / avv_expiry_date: enforce the AC-1.1 invariant.
      - avv_pdf_bytes: SHA-256'd to populate ``avv_hash`` post-registration.
      - sub_processors: optional list of SubProcessor records (AC-2.1 reads).
    """

    def __init__(
        self,
        processor_id: str,
        controller_name: str,
        controller_address: str,
        avv_signed_date: date,
        avv_expiry_date: date,
        avv_pdf_bytes: bytes,
        sub_processors: list[Any] | None = None,
    ) -> None:
        self.processor_id = processor_id
        self.controller_name = controller_name
        self.controller_address = controller_address
        self.avv_signed_date = avv_signed_date
        self.avv_expiry_date = avv_expiry_date
        self.avv_pdf_bytes = avv_pdf_bytes
        self.sub_processors = sub_processors or []
        # Populated by ``register_processor`` post-append.
        self.avv_hash: str | None = None
        self.registered: bool = False


# Module-level append-only registry. The append-only invariant is enforced by
# convention: every read site traverses the list; the sole write site is
# ``register_processor`` which uses ``list.append`` only.
_REGISTRY: list[Processor] = []


def register_processor(processor: Processor) -> None:
    """Register an Art. 28(1) processor in the append-only registry.

    Computes ``avv_hash = sha256(avv_pdf_bytes).hexdigest()`` and appends the
    processor to the module-level registry. Expired AVV
    (``avv_signed_date >= avv_expiry_date``) raises ``ValueError`` per
    AC-1.1 and does NOT append.

    EARS AC-1:
      When register_processor(processor) is called with a Processor dataclass
      whose avv_signed_date < avv_expiry_date, the system shall compute
      avv_hash = sha256(avv_pdf_bytes).hexdigest() and append the processor
      to an append-only registry.

    EARS AC-1.1:
      If register_processor(processor) is called with a Processor whose
      avv_signed_date >= avv_expiry_date, then the system shall raise
      ValueError citing the date constraint and shall NOT append the
      processor to the registry.
    """
    assert_date_constraint(processor.avv_signed_date, processor.avv_expiry_date)
    processor.avv_hash = compute_avv_hash(processor.avv_pdf_bytes)
    _REGISTRY.append(processor)
    processor.registered = True


def _reset_registry() -> None:
    """Test-only utility: clear the module-level ``_REGISTRY``.

    Production code MUST NOT call this. It exists so the chain-integration
    test (``tests/test_avv_kaskade_chain.py``) can assert exact registry
    state (``len == 6``) without interference from prior tests in the same
    pytest session (the registry is process-global).

    Per pinned memory [4] / [7], the append-only invariant of ``_REGISTRY``
    is preserved in production: the sole production write site is
    ``register_processor`` (which uses ``list.append`` only). This helper
    mutates ``_REGISTRY`` for test isolation purposes.
    """
    _REGISTRY.clear()