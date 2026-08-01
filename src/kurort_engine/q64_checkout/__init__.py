"""kurort_engine.q64_checkout - Pattern F chain-extension package for the
§ 15 Abs. 3 Kurverwaltung-Bad-Orb departure-Meldung mirror + Bezahlung/
Gutschein/Reisebuero-commission clearing.

Iter-6 Phase-3 GREEN - assembles the surface modules (checkout_form,
departure_meldung, gutschein_ledger, commission_split) under a single
namespace + provides the module-level globals the tests inspect:
``events`` (append-only q64.* event registry), ``audit_log``
(append-only audit-log surface consumed by emit_departure_meldung),
and ``commission_table_version`` (read from commission_split_table.json
at import time).

Per spec.yaml assumptions §10 + spec.lock.md §IMPORT_DISCIPLINE:
- Stage-1 minimum: re-exports the surface functions, exposes the
  module globals, exposes the ``f5_q64_checkout`` namespace.
- Stage-2 (out of scope this iter): F5-Receptionist CLI binding, full
  PDF checkout-summary render, 7-locale template.
"""
from __future__ import annotations

# AC-1 + AC-5 surface: f5_q64_checkout namespace exposes the checkout entry.
from kurort_engine.q64_checkout.checkout_form import (  # noqa: E402, F401
    CheckoutForm,
    f5_q64_checkout,
)

# AC-4 surface: OTA + Reisebuero commission split reader.
from kurort_engine.q64_checkout.commission_split import (  # noqa: E402, F401
    compute_commission_split,
    get_commission_table_version,
)

# AC-2 surface: idempotent § 15 Abs. 3 Kurverwaltung-Bad-Orb departure-Meldung.
from kurort_engine.q64_checkout.departure_meldung import (  # noqa: E402, F401
    emit_departure_meldung,
)

# AC-3 surface: § 35 KAG Abrechnung gutschein redemption ledger.
from kurort_engine.q64_checkout.gutschein_ledger import (  # noqa: E402, F401
    redeem_gutschein,
)

# Module-level append-only event registry (observable from tests). AC-1
# asserts ``q64.events`` is iterable and contains the checkout_completed
# event with the 3 spec.yaml:6 fields. AC-4 reuses this for
# commission_split.calculated events.
events: list[dict] = []

# Module-level append-only audit-log surface consumed by emit_departure_meldung.
# AC-2 asserts ``q64.audit_log`` is iterable and contains at least one entry
# whose ``idempotency_key`` matches the emitted event's.
audit_log: list[dict] = []

# Module-level commission-table version (read from commission_split_table.json
# at commission_split import time). AC-4 sub-condition (c) reads this
# attribute to compute sha256(booking_id + commission_table_version).hexdigest().
# Bound AFTER commission_split import to capture the loaded version (defaults
# to "v1" if the JSON file omits the ``version`` key).
commission_table_version: str = get_commission_table_version()

__all__ = [
    "CheckoutForm",
    "f5_q64_checkout",
    "emit_departure_meldung",
    "redeem_gutschein",
    "compute_commission_split",
    "events",
    "audit_log",
    "commission_table_version",
]
