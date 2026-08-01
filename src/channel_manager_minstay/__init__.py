"""channel_manager_minstay v0.1.0 â Kurort-native channel-manager MinLOS push.

A Kurort-vertical extension to ``kurort_engine`` that declares per-Bundesland ×
per-Kurort MinLOS peak-week rules (Easter / Whitsun / Summer Hochsaison /
Christmas + default Shoulder) in YAML and pushes them to OTA channels
(Booking.com Connectivity API + HRS Channel Manager) on demand, with a
dry-run scheduler that emits OTA_HotelAvailNotif XML envelopes without
performing network IO.

This top-level package re-exports the public API defined by AC-1..AC-7 in
``spec.yaml``:

    AC-1: MinLosProfile, MinLosRule, load_minlos_profile
    AC-2/AC-3: BookingComConnector
    AC-4: HrsCmConnector, RateTypeFilter
    AC-5: MinLosValidator, MinLosValidationReport
    AC-6: MinLosScheduler, DryRunResult

Importing this package MUST NOT mutate global state, write to stdout, or
open files (parity with the ``kurort_engine`` package AC-6 contract).
"""
from __future__ import annotations

# Submodule re-export per AC-2/AC-3. The connector class lives in
# ``channel_manager_minstay.booking_com`` and is imported here so callers
# can use either form (``channel_manager_minstay.BookingComConnector``
# or ``channel_manager_minstay.booking_com.BookingComConnector``)
# interchangeably.
from channel_manager_minstay.booking_com import BookingComConnector

# Submodule re-exports per AC-4. The HRS Channel Manager connector lives in
# ``channel_manager_minstay.hrs`` and the RateTypeFilter frozenset is exposed
# at the top level so callers can override the filter without importing the
# submodule.
from channel_manager_minstay.hrs import HrsCmConnector, RateTypeFilter

# Submodule re-exports per AC-1. The dataclass/function bodies live in
# ``channel_manager_minstay.profile_loader`` and are imported here so that
# callers can use either form (``channel_manager_minstay.load_minlos_profile``
# or ``channel_manager_minstay.profile_loader.load_minlos_profile``)
# interchangeably.
from channel_manager_minstay.profile_loader import (
    MinLosProfile,
    MinLosRule,
    load_minlos_profile,
)

# Submodule re-exports per AC-6. The scheduler + dry-run result dataclass
# live in ``channel_manager_minstay.scheduler`` and are exposed at the top
# level so the CLI entry point can ``from channel_manager_minstay import
# MinLosScheduler``.
from channel_manager_minstay.scheduler import DryRunResult, MinLosScheduler

# Submodule re-exports per AC-5. The validator + report dataclass live in
# ``channel_manager_minstay.validator`` and are exposed at the top level.
from channel_manager_minstay.validator import (
    MinLosValidationReport,
    MinLosValidator,
)

__version__ = "0.1.0"

__all__ = [
    # AC-1
    "MinLosProfile",
    "MinLosRule",
    "load_minlos_profile",
    # AC-2/AC-3
    "BookingComConnector",
    # AC-4
    "HrsCmConnector",
    "RateTypeFilter",
    # AC-5
    "MinLosValidator",
    "MinLosValidationReport",
    # AC-6
    "MinLosScheduler",
    "DryRunResult",
]
