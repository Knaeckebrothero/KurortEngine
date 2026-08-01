"""Centralised configuration constants for ``kurort_engine.spa_wellness``.

All HHV (Hessischer Heilb\u00e4derverband) reference tariffs, default
durations, allowed payment methods, and Toskana Therme pricing live here
so the spa_wellness modules never carry private constants that drift
out of sync.

Reference:
  - Heilbad Sauna entry: \u20ac8.00 (HHV reference tariff)
  - Heilbad 30-min ambulante Vorsorge Massage: \u20ac35.00 (HHV reference tariff + \u00a723 SGB V)
  - Toskanaworld Bad Orb 2026 day-pass: \u20ac22.50 list, 20% G\u00e4stekarte discount
  - Payment methods: cash + SEPA + Kurkarte
"""
from __future__ import annotations

from decimal import Decimal

# ---------------------------------------------------------------------------
# Sauna + Massage prices (AC-1, AC-3) -- HHV reference tariffs.
# ---------------------------------------------------------------------------

SAUNA_FOLIO_PRICE_EUR: Decimal = Decimal("8.00")
MASSAGE_FOLIO_PRICE_EUR: Decimal = Decimal("35.00")


# ---------------------------------------------------------------------------
# Default slot durations (AC-1, AC-3).
# ---------------------------------------------------------------------------

SAUNA_DEFAULT_DURATION_MINUTES: int = 0  # Sauna is point-in-time (capacity-based)
MASSAGE_DEFAULT_DURATION_MINUTES: int = 30  # HHV ambulante Vorsorge


# ---------------------------------------------------------------------------
# Payment methods (AC-6).
# ---------------------------------------------------------------------------

ALLOWED_PAYMENT_METHODS: frozenset[str] = frozenset({"cash", "sepa", "kurkarte"})


# ---------------------------------------------------------------------------
# Toskana Therme day-pass pricing (AC-5).
# ---------------------------------------------------------------------------

TOSKANA_DAY_PASS_LIST_PRICE_EUR: Decimal = Decimal("22.50")
GAESTEKARTE_DISCOUNT_FACTOR: Decimal = Decimal("0.80")  # = 1 - 0.20 (20% off)


__all__ = [
    "SAUNA_FOLIO_PRICE_EUR",
    "MASSAGE_FOLIO_PRICE_EUR",
    "SAUNA_DEFAULT_DURATION_MINUTES",
    "MASSAGE_DEFAULT_DURATION_MINUTES",
    "ALLOWED_PAYMENT_METHODS",
    "TOSKANA_DAY_PASS_LIST_PRICE_EUR",
    "GAESTEKARTE_DISCOUNT_FACTOR",
]
