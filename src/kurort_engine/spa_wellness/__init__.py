"""kurort_engine.spa_wellness — Sauna + Massage + Toskana Therme resource management.

Kurort-vertical extension to ``kurort_engine`` for the Heilbad-vertical Spa/Wellness
resource management layer (Sauna slots + Massage appointments + Toskana Therme
cross-sell tickets) per the spa/wellness resource-management design
record §6.4, acceptance criteria AC-1..AC-8.

Module surface (per AC-N bindings):
  - AC-1, AC-2: Sauna slot creation + listing (Resource + Slot + SpaManager)
  - AC-3, AC-4: Massage appointment creation + conflict detection (SpaManager.detect_conflicts)
  - AC-5: Toskana Therme ticket sale via Kur-/Gästekarte (ToskanaThermeAdapter)
  - AC-6, AC-7: Spa payment integration (cash + SEPA + Kurkarte) + guest folio (Payment + SpaBooking)
  - AC-8: Daily Spa revenue report (generate_daily_spa_revenue_report + DailySpaRevenueReport)

Importing this package MUST NOT mutate global state, write to stdout, or
open files (parity with the ``kurort_engine`` package AC-6 contract).
"""
from __future__ import annotations

# Resource manager facade (AC-1, AC-2, AC-4)
from kurort_engine.spa_wellness.manager import SpaManager

# Payment + SpaBooking entities (AC-6, AC-7)
from kurort_engine.spa_wellness.payment_adapter import (
    Payment,
    PaymentMethodError,
    PaymentMethodKurkarteError,
    SlotBookingError,
    SpaBooking,
)

# Daily Spa revenue report (AC-8)
from kurort_engine.spa_wellness.report import (
    DailySpaRevenueReport,
    generate_daily_spa_revenue_report,
)

# Resource + Slot primitives (AC-1, AC-3)
from kurort_engine.spa_wellness.resource import Resource
from kurort_engine.spa_wellness.slot import Slot

# Toskana Therme ticket adapter (AC-5)
from kurort_engine.spa_wellness.toskana_therme import (
    ToskanaThermeAdapter,
    ToskanaThermeKurkarteError,
    ToskanaThermeTicket,
)

__all__ = [
    # Resource + Slot primitives (AC-1, AC-3)
    "Resource",
    "Slot",
    # Resource manager facade (AC-1, AC-2, AC-4)
    "SpaManager",
    # Toskana Therme ticket adapter (AC-5)
    "ToskanaThermeAdapter",
    "ToskanaThermeTicket",
    "ToskanaThermeKurkarteError",
    # Payment + SpaBooking entities (AC-6, AC-7)
    "Payment",
    "PaymentMethodError",
    "PaymentMethodKurkarteError",
    "SlotBookingError",
    "SpaBooking",
    # Daily Spa revenue report (AC-8)
    "DailySpaRevenueReport",
    "generate_daily_spa_revenue_report",
]