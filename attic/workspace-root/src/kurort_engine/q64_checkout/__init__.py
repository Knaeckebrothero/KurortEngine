"""q64_checkout_departure_meldung — Kurverwaltung-Bad-Orb § 15 Abs. 3 + § 35 KAG mirror.

Pattern F strict (chain-extension of iter-6 meldeschein SHIPPED at b2d13731):
  * Extends the SHIPPED MeldescheinForm from kurort_engine.meldeschein
  * Consumes the SHIPPED kurgaste_retention.audit_log companion-pattern
    (write_art30_audit_entry returns dict with audit_log_hash; consumed
    as audit_log_hash = sha256(...) hexdigest)
  * Consumes the SHIPPED kurpaket_orchestrator (compose_quote / render_*)
  * Anti-drift: 6 SHAs preserved in spec_lock.md PROTECTED block at Phase 1
    close; spec.yaml SHA-256 = 987ff5cb49655576f61a9ed5481f888cde1f3be210091fbdf3fc8cd17b609020

5 public symbols per spec.yaml AC-1..AC-5 (test_oracle paths in
tests/test_q64_checkout_departure_meldung.py):
  * f5_q64_checkout     — AC-1 + AC-5 namespace (foreign-guest + DE-guest checkout)
  * emit_departure_meldung — AC-2 idempotent emission + q64.audit_log_entry
  * redeem_gutschein   — AC-3 ledger append + apply to checkout_form.total_kurtaxe
  * compute_commission_split — AC-4 reads commission_split_table.json
  * CheckoutForm       — Pattern F chain-extension dataclass (extends MeldescheinForm)

Sister event surfaces emitted on successful operations (string-typed, no
external transport dependency):
  * q64.checkout.completed         (AC-1, AC-5)
  * q64.audit_log_entry            (AC-2)
  * q64.commission_split.calculated (AC-4)

Idempotency keys (sha256 hexdigest, see AC-2 / AC-4):
  * emit_departure_meldung: sha256(gast_id + abreisedatum + emission_timestamp)
  * compute_commission_split: sha256(booking_id + commission_table_version)

BEG IV 2025-01-01 carve-out (AC-5): German-guest Meldepflicht is waived
per § 2 Abs. 1 Nr. 3 BMG (BEG IV) — no Meldeschein lookup, but the
departure_meldung (AC-2) + redeem_gutschein (AC-3) + commission_split
(AC-4) code paths are still reached when their arguments are provided.
"""

from __future__ import annotations

# Eager import — checkout_form.py SHIPPED (12395 bytes, mtime 2026-07-14 06:08:00).
# Pattern F strict: CheckoutForm subclasses MeldescheinForm non-destructively.
from .checkout_form import CheckoutForm, f5_q64_checkout  # noqa: E402, F401

# Module-level append-only event registry (observable from tests). AC-1
# asserts ``q64.events`` is iterable and contains the checkout_completed
# event with the 3 spec.yaml:6 fields.
events: list[dict] = []


# Lazy-load the not-yet-written siblings via PEP 562 module-level
# __getattr__. This makes ``import kurort_engine.q64_checkout`` succeed
# even before departure_meldung.py / gutschein.py / commission.py are
# written (todos 4, 5, 6). After those siblings ship, the names will
# also be bound eagerly via the try/except block below.
_LAZY_SUBMODULES: dict[str, str] = {
    "emit_departure_meldung": "kurort_engine.q64_checkout.departure_meldung",
    "redeem_gutschein": "kurort_engine.q64_checkout.gutschein",
    "compute_commission_split": "kurort_engine.q64_checkout.commission",
    "CommissionSplit": "kurort_engine.q64_checkout.commission",
    "gutschein_redemption_ledger": "kurort_engine.q64_checkout.gutschein",
}


def __getattr__(name: str):  # PEP 562
    """Lazy import not-yet-written sibling symbols on first attribute access.

    After departure_meldung.py / gutschein.py / commission.py ship, the
    eager binding block below makes the names available in ``dir()``
    immediately. Until then, ``hasattr()`` and ``getattr()`` still work
    via this hook — returning a usable symbol or raising AttributeError
    cleanly (NOT ImportError, so tests can detect the gap).
    """
    sub = _LAZY_SUBMODULES.get(name)
    if sub is not None:
        import importlib

        try:
            mod = importlib.import_module(sub)
        except ImportError:
            raise AttributeError(
                f"module 'kurort_engine.q64_checkout' has no attribute "
                f"{name!r} (sibling module {sub!r} not yet written)"
            ) from None
        value = getattr(mod, name, None)
        if value is not None:
            globals()[name] = value  # bind for subsequent dir() visibility
            return value
    raise AttributeError(
        f"module 'kurort_engine.q64_checkout' has no attribute {name!r}"
    )


# Eager binding block — runs at package import time. If the sibling
# module is missing, the import is skipped silently (the __getattr__
# hook above will lazy-load on first access). This block is what
# populates ``dir(kurort_engine.q64_checkout)`` for tests after all
# sibling modules are written.
try:
    from .departure_meldung import emit_departure_meldung  # noqa: F401
except ImportError:
    pass
try:
    from .gutschein import (  # noqa: F401
        gutschein_redemption_ledger,
        redeem_gutschein,
    )
except ImportError:
    pass
try:
    from .commission import (  # noqa: F401
        CommissionSplit,
        compute_commission_split,
    )
except ImportError:
    pass


__all__ = [
    "CheckoutForm",
    "CommissionSplit",
    "compute_commission_split",
    "emit_departure_meldung",
    "events",
    "f5_q64_checkout",
    "gutschein_redemption_ledger",
    "redeem_gutschein",
]
