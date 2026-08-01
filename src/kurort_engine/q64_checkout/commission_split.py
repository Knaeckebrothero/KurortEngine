"""kurort_engine.q64_checkout.commission_split - OTA + Reisebuero commission
split reader (Pattern F non-destructive extension).

Iter-6 Phase-3 GREEN - implements AC-4 (compute_commission_split reads
commission_split_table.json + emits q64.commission_split.calculated event
with idempotency_key = sha256(booking_id + commission_table_version)
.hexdigest()).

Spec contract (verbatim from spec.yaml:15):
  "When compute_commission_split(booking_id, channel) is called for an
   OTA- or Reisebuero-routed booking routed via the SHIPPED
   channel_manager_minstay, the system shall return a CommissionSplit
   whose rate is read from commission_split_table.json per (a)
   booking_com: 0.15, (b) agoda: 0.12, (c) trivago: 0.0 (lead-gen only),
   (d) reisebuero_x_negotiated: the negotiated entry in the table
   (config-only update, no code change), (e) direct: 0.0; and shall
   emit a q64.commission_split.calculated event with idempotency_key =
   sha256(booking_id + commission_table_version).hexdigest(); and shall
   raise ValueError citing the unsupported channel for any channel not
   present in commission_split_table.json."

Pattern F discipline: the rate table is config-only data
(commission_split_table.json co-located with this module). Rate changes
are operational config updates (per pinned memory [3] config-only
discipline); no code change required.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

# Module-level table cache (loaded once at module import; refresh-able
# via reload_commission_table() test hook).
_COMMISSION_TABLE: dict[str, Any] = {}
_COMMISSION_TABLE_VERSION: str = "v1"


def _load_commission_table() -> tuple[dict[str, Any], str]:
    """Load commission_split_table.json from the co-located module dir.

    Returns a (table, version) tuple. The table maps channel name to
    Decimal rate. The version is read from the table's ``version`` key
    (defaults to "v1" if absent).
    """
    global _COMMISSION_TABLE, _COMMISSION_TABLE_VERSION
    table_path = Path(__file__).parent / "commission_split_table.json"
    with table_path.open(encoding="utf-8") as fh:
        raw = json.load(fh)
    table: dict[str, Any] = {}
    for k, v in raw.items():
        if k == "version":
            continue
        # Coerce numeric rates to Decimal for exact Decimal arithmetic.
        table[k] = Decimal(str(v))
    version = str(raw.get("version", "v1"))
    _COMMISSION_TABLE = table
    _COMMISSION_TABLE_VERSION = version
    return table, version


# Load the table at import time so q64.commission_table_version is
# available before any compute_commission_split call.
_load_commission_table()


def get_commission_table_version() -> str:
    """Return the active commission_table_version (e.g. "v1")."""
    return _COMMISSION_TABLE_VERSION


def reload_commission_table() -> tuple[dict[str, Any], str]:
    """Test-only hook: re-read commission_split_table.json from disk.

    Useful when the operator updates the config-only rate table at
    runtime (per pinned memory [3] config-only discipline) and wants
    the change to take effect without a process restart.
    """
    return _load_commission_table()


def compute_commission_split(
    booking_id: str,
    channel: str,
) -> dict[str, Any]:
    """AC-4 entry point - return CommissionSplit dict for a (booking_id, channel).

    Reads the per-channel rate from the module-level _COMMISSION_TABLE
    (loaded at import time from commission_split_table.json). Raises
    ``ValueError`` citing the unsupported channel name for any channel
    not present in the table (per spec.yaml:15). Emits a
    ``q64.commission_split.calculated`` event to the q64.events
    registry with ``idempotency_key`` =
    sha256(booking_id + commission_table_version).hexdigest() (64-char
    lowercase hex).
    """
    # Look up the rate; raise ValueError citing the unsupported channel
    # if the channel is not present in the table.
    if channel not in _COMMISSION_TABLE:
        raise ValueError(
            f"unsupported channel {channel!r} - not present in "
            f"commission_split_table.json (active channels: "
            f"{sorted(_COMMISSION_TABLE.keys())})"
        )
    rate = _COMMISSION_TABLE[channel]

    # Compute the idempotency_key per spec.yaml:15 verbatim.
    idempotency_key = hashlib.sha256(
        f"{booking_id}{_COMMISSION_TABLE_VERSION}".encode()
    ).hexdigest()

    # Build the CommissionSplit result dict (JSON-serializable, Decimal
    # rate preserved for exact comparison in tests).
    result: dict[str, Any] = {
        "booking_id": booking_id,
        "channel": channel,
        "rate": rate,
        "commission_table_version": _COMMISSION_TABLE_VERSION,
        "idempotency_key": idempotency_key,
    }

    # Emit q64.commission_split.calculated event to the q64.events registry.
    # Defer the import to break any potential circular dependency between
    # q64_checkout/__init__.py and this module.
    from kurort_engine.q64_checkout import events as _q64_events  # noqa: E402

    _q64_events.append(
        {
            "event_type": "q64.commission_split.calculated",
            "booking_id": booking_id,
            "channel": channel,
            "rate": rate,
            "commission_table_version": _COMMISSION_TABLE_VERSION,
            "idempotency_key": idempotency_key,
        }
    )

    return result


__all__ = [
    "compute_commission_split",
    "get_commission_table_version",
    "reload_commission_table",
    "_COMMISSION_TABLE",
    "_COMMISSION_TABLE_VERSION",
]
