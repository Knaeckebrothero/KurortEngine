"""kurort_engine.avv_kaskade.sub_processor — Art. 28(2) sub-processor record.

Iter-28 (Developer) — Phase 5 Tactical Green.

Each ``SubProcessor`` represents an Art. 28(2) unterauftragsverarbeiter
disclosed by a controller. The ``vendor_non_cooperation`` flag is the
trigger for AC-2.1 gap-flagging in the ``GeeignetheitspruefungReport``.
"""
from __future__ import annotations

from typing import Any


class SubProcessor:
    """Art. 28(2) sub-processor record.

    Fields:
      - sub_processor_id: stable identity used by AC-2.1 gap-flagging.
      - vendor_name: appears in AC-3 sub_processors block.
      - data_categories: per-category data processing scope.
      - tom_evidence_index: optional per-category TOM mapping (AC-2(d)).
      - vendor_non_cooperation: True triggers AC-2.1 gap flag.
    """

    def __init__(
        self,
        sub_processor_id: str,
        vendor_name: str,
        data_categories: list[str],
        tom_evidence_index: dict[str, Any] | None = None,
        vendor_non_cooperation: bool = False,
    ) -> None:
        self.sub_processor_id = sub_processor_id
        self.vendor_name = vendor_name
        self.data_categories = data_categories
        self.tom_evidence_index = tom_evidence_index or {}
        self.vendor_non_cooperation = vendor_non_cooperation