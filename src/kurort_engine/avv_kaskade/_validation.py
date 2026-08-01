"""kurort_engine.avv_kaskade._validation — DRY helpers (Phase 5 refactor)."""
import hashlib
import json
from datetime import date
from typing import Any


def compute_avv_hash(avv_pdf_bytes: bytes) -> str:
    """SHA-256 hex digest of AVV PDF bytes (AC-1)."""
    return hashlib.sha256(avv_pdf_bytes).hexdigest()
def compute_canonical_sha256(payload: Any) -> str:
    """SHA-256 hex digest of canonical-JSON payload (AC-2/AC-3/AC-5)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
def assert_date_constraint(signed: date, expiry: date) -> None:
    """Raise ValueError when signed >= expiry (AC-1.1 Art. 28(1))."""
    if signed >= expiry:
        raise ValueError(f"AVV date violated: signed {signed} must be before expiry {expiry}.")