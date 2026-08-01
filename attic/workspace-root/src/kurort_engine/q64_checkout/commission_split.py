"""q64_checkout.commission_split — Reisebüro / OTA commission split calculator.

Per spec.yaml AC-4: compute_commission_split(booking_id, channel) returns a
CommissionSplit whose rate is read from commission_split_table.json per:
  (a) booking_com: 0.15
  (b) agoda: 0.12
  (c) trivago: 0.0 (lead-gen only)
  (d) reisebuero_x_negotiated: 0.10 (negotiated entry in the table)
  (e) direct: 0.0
…and shall emit a q64.commission_split.calculated event with
idempotency_key = sha256(booking_id + commission_table_version).hexdigest();
and shall raise ValueError citing the unsupported channel for any channel
not present in commission_split_table.json.

Pattern F strict: this module is a read-only consumer of the versioned
config table commission_split_table.json. The table is config-only — no
code change is needed to update rates (re-engage trigger: spec.yaml
amendment). The commission_table_version is exposed at
``kurort_engine.q64_checkout.commission_table_version`` (via the package
__init__.py re-export) so the AC-4 test can verify the idempotency_key
formula uses the current table version.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

# Module-level location of the versioned commission rates config table.
_TABLE_PATH = Path(__file__).parent / "commission_split_table.json"

# Module-level event registry (observable from tests as
# ``q64.commission_split_calculated_events``). Each entry is a dict with
# the event_type, booking_id, channel, rate, commission_table_version, and
# idempotency_key fields.
commission_split_calculated_events: list[dict[str, Any]] = []


def _load_table() -> dict[str, Any]:
    """Load the versioned commission rates config table from disk.

    Returns a dict with at least the keys ``version`` (str) and one key
    per supported channel (rate as float). Raises FileNotFoundError if
    the table file is missing.
    """
    with open(_TABLE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _compute_idempotency_key(
    booking_id: str, commission_table_version: str
) -> str:
    """Compute the AC-4 idempotency key.

    spec.yaml:15 verbatim: ``idempotency_key = sha256(booking_id +
    commission_table_version).hexdigest()``. Returns a 64-char lowercase
    hex string.
    """
    payload = f"{booking_id}{commission_table_version}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CommissionSplit:
    """Result of compute_commission_split(booking_id, channel).

    Per spec.yaml AC-4: carries the rate from the versioned config table.
    Immutable (frozen=True) to prevent downstream mutation of the
    commission calculation result.
    """

    booking_id: str
    channel: str
    rate: Decimal
    commission_table_version: str
    idempotency_key: str


def compute_commission_split(booking_id: str, channel: str) -> CommissionSplit:
    """Compute the commission split for a booking routed via ``channel``.

    Per spec.yaml AC-4: reads the rate from commission_split_table.json,
    returns a CommissionSplit with the rate, and emits a
    q64.commission_split.calculated event with idempotency_key =
    sha256(booking_id + commission_table_version).hexdigest(). Raises
    ValueError citing the unsupported channel for any channel not present
    in the table.
    """
    table = _load_table()
    commission_table_version = str(table.get("version", "unknown"))

    if channel not in table:
        raise ValueError(
            f"unsupported channel for commission split: {channel!r}. "
            f"Supported channels: {sorted(k for k in table if k != 'version')}"
        )

    rate = Decimal(str(table[channel]))
    idempotency_key = _compute_idempotency_key(
        booking_id, commission_table_version
    )

    # Emit q64.commission_split.calculated event.
    event: dict[str, Any] = {
        "event_type": "q64.commission_split.calculated",
        "event_id": f"csc-{uuid.uuid4().hex[:12]}",
        "booking_id": booking_id,
        "channel": channel,
        "rate": rate,
        "commission_table_version": commission_table_version,
        "idempotency_key": idempotency_key,
    }
    commission_split_calculated_events.append(event)

    return CommissionSplit(
        booking_id=booking_id,
        channel=channel,
        rate=rate,
        commission_table_version=commission_table_version,
        idempotency_key=idempotency_key,
    )


# Module-level commission_table_version (loaded at import time from the
# config table). Exposed at ``q64.commission_table_version`` via the
# package __init__.py re-export.
commission_table_version: str = str(_load_table().get("version", "unknown"))


__all__ = [
    "CommissionSplit",
    "commission_split_calculated_events",
    "commission_table_version",
    "compute_commission_split",
]
