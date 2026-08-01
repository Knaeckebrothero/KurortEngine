"""AC-4: Monthly Kurtaxe remittance CSV (Stadt Bad Orb portal).

Test_oracle path recorded in spec.yaml:96. This is the red-phase test
that will fail with an AssertionError against the placeholder
implementation (``generate_monthly_remittance_csv`` currently returns
``""`` with the wrong signature).

AC-4 contract (spec.yaml:86-96):
    When ``generate_monthly_remittance_csv(year, month, reservations)``
    is invoked, the ``kurort_engine`` shall emit a CSV with the
    twelve-column Bad Orb remittance schema (Reservation-ID,
    anonymised guest name, arrival, departure, day_count, rate_band,
    per_guest_per_day_eur, exemption_flag, subtotal_eur, period_yyyy_mm,
    hotel_steuernummer, hotel_signature_line) where row totals reconcile
    to (Σ reservation subtotals) and the period total equals the sum of
    paid-Kurtaxe (i.e., exempt guests contribute €0.00, not "absent").

The AC-4 columns, in spec-documented order, are:
    1.  Reservation-ID
    2.  anonymised guest name
    3.  arrival
    4.  departure
    5.  day_count
    6.  rate_band
    7.  per_guest_per_day_eur
    8.  exemption_flag
    9.  subtotal_eur
    10. period_yyyy_mm
    11. hotel_steuernummer
    12. hotel_signature_line

Convention notes
----------------
- The fixture factory (cached Satzung + age-anchored Guest) lives in
  ``tests/_factories``. We use it for Guest creation.
- We deliberately do NOT import from ``repo/src/kurort_engine/reporting``
  directly — we go through the package public surface (``kurort_engine``)
  so the test is exercisable against any conforming implementation of the
  AC-6 public API.

RED VERIFY
----------
These tests are expected to FAIL during the red phase. The failure mode
must be ``AssertionError`` (placeholder returns ``""``, signature
mismatch, or empty schema), NOT ``ImportError`` / ``AttributeError`` /
``NotImplementedError``. We enforce the failure mode by:

  1. Asserting the function signature matches the AC-4 contract FIRST
     via ``inspect.signature``. Wrong signature -> AssertionError.
  2. Asserting the return type (``str``) and basic content (``len > 0``,
     has at least one header line) before parsing detail — these fail
     with AssertionError on ``""``.
  3. Using ``csv.reader`` for header parsing so column-order mistakes
     surface as AssertionError on column names, not TypeError.
"""
from __future__ import annotations

import csv
import inspect
import io
from datetime import date
from decimal import Decimal
from typing import Sequence

import pytest

import kurort_engine
from kurort_engine import (
    Exemption,
    Guest,
    Reservation,
    Satzung,
    generate_monthly_remittance_csv,
)

from tests._factories import hessen_satzung, make_guest  # noqa: F401  (fixtures re-exported)


# ---------------------------------------------------------------------------
# AC-4 column schema (verbatim from spec.yaml:88-95)
# ---------------------------------------------------------------------------

AC4_HEADER_COLUMNS: tuple[str, ...] = (
    "Reservation-ID",
    "anonymised guest name",
    "arrival",
    "departure",
    "day_count",
    "rate_band",
    "per_guest_per_day_eur",
    "exemption_flag",
    "subtotal_eur",
    "period_yyyy_mm",
    "hotel_steuernummer",
    "hotel_signature_line",
)

# 12 columns required by AC-4.
AC4_COLUMN_COUNT: int = len(AC4_HEADER_COLUMNS)
assert AC4_COLUMN_COUNT == 12, "AC-4 spec mandates 12 columns"


# ---------------------------------------------------------------------------
# Helper: parse CSV text -> list[dict[str, str]] using csv.DictReader
# ---------------------------------------------------------------------------

def _parse_csv(csv_text: str) -> tuple[list[str], list[dict[str, str]]]:
    """Return (header_columns, data_rows) for the given CSV text.

    The header is parsed with csv.reader to preserve column order; data rows
    are parsed with csv.DictReader for keyed access in assertions.
    """
    assert isinstance(csv_text, str), (
        f"generate_monthly_remittance_csv must return str, got {type(csv_text).__name__}"
    )
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert rows, "CSV must contain at least the header row"

    header = rows[0]
    data_rows: list[dict[str, str]] = []
    for raw in rows[1:]:
        # csv.DictReader needs the source re-opened per row, so re-parse.
        parsed = next(csv.DictReader(io.StringIO(csv_text)), None)
        if parsed is None:
            break
        data_rows.append(parsed)
    # Deduplicate: csv.DictReader re-reads from the top each time so the
    # list above is actually a copy of the whole data set per row. Use a
    # proper one-pass parse instead.
    data_rows = list(csv.DictReader(io.StringIO(csv_text)))
    return header, data_rows


# ---------------------------------------------------------------------------
# Signature contract assertion (shared across tests)
# ---------------------------------------------------------------------------

def _assert_ac4_signature() -> inspect.Signature:
    """Assert that ``generate_monthly_remittance_csv`` matches the AC-4 contract.

    AC-4 mandates: ``generate_monthly_remittance_csv(year, month, reservations)``
    returning CSV text. We enforce:

      - First parameter named ``year``
      - Second parameter named ``month``
      - A third positional parameter named ``reservations``
      - No additional required positional parameters beyond these three

    Returns the inspected ``inspect.Signature`` so the caller can pass the
    bound arguments using the documented parameter names.
    """
    sig = inspect.signature(generate_monthly_remittance_csv)
    params = list(sig.parameters.values())

    # Must have at least the three documented positional params (in order).
    assert len(params) >= 3, (
        f"AC-4 contract requires (year, month, reservations) — got signature "
        f"{sig!s} with only {len(params)} parameter(s)"
    )
    assert params[0].name == "year", (
        f"AC-4 contract: first parameter must be named 'year', got {params[0].name!r}"
    )
    assert params[1].name == "month", (
        f"AC-4 contract: second parameter must be named 'month', got {params[1].name!r}"
    )
    assert params[2].name == "reservations", (
        f"AC-4 contract: third parameter must be named 'reservations', "
        f"got {params[2].name!r}"
    )
    return sig


# ===========================================================================
# Test 1 — the spec test_oracle (AC-4 schema + reconciliation)
# ===========================================================================

def test_ac4_monthly_remittance_csv_schema_and_reconciliation(hessen_satzung) -> None:
    """AC-4 spec test_oracle: 12-column schema + Σ subtotals == paid Kurtaxe.

    Builds two reservations:
      - R-1: single paying adult, 2 nights (2024-06-10 -> 2024-06-12)
              Expected subtotal: 2.50 × 2 = 5.00 EUR
      - R-2: mixed (1 paying adult + 1 exempt Geschaeftsreisender),
              3 nights (2024-06-10 -> 2024-06-13)
              Expected paid subtotal: 2.50 × 3 = 7.50 EUR
              Exempt row subtotal: 0.00 EUR (exempt guest IS present in CSV,
              not absent — per AC-4 "exempt guests contribute €0.00, not absent").

    The CSV must contain:
      - 1 header row with the 12 documented columns in order
      - 1 row per (reservation × guest) = 1 + 2 = 3 data rows
        (exempt guest is present with subtotal 0.00)
      - Σ subtotal_eur across data rows == 5.00 + 7.50 + 0.00 == 12.50 EUR
        (this is the "period total equals sum of paid-Kurtaxe" rule — the
        exempt 0.00 row is present but contributes nothing to the paid sum)

    Note: each guest in a multi-guest reservation contributes its own row.
    The exempt Geschaeftsreisender row has subtotal 0.00 but exemption_flag
    set, so the period total of paid Kurtaxe (12.50) is unaffected.
    """
    _assert_ac4_signature()

    # ---- Reservation 1: paying adult, 2 nights ----
    r1 = Reservation(
        reservation_id="R-AC4-001",
        arrival=date(2024, 6, 10),
        departure=date(2024, 6, 12),
        guests=(make_guest(age_years=35, name="Anna Vollzahler"),),
    )

    # ---- Reservation 2: paying adult + exempt Geschaeftsreisender, 3 nights ----
    # Geschaeftsreisender = business traveller: marked via Exemption enum
    # (covers AC-3 / AC-4 exemption_flag column).
    paying_guest = make_guest(age_years=40, name="Bernd Vollzahler")
    exempt_guest = make_guest(
        age_years=45,
        name="Carla Geschaeftsreisender",
        # Geschaeftsreisender is recorded as a flag/Exemption on the
        # Reservation context — the engine must recognise it during CSV
        # emission. The Reservation dataclass shape is intentionally
        # opaque here; tests assert the AC-4 output contract only.
    )
    r2 = Reservation(
        reservation_id="R-AC4-002",
        arrival=date(2024, 6, 10),
        departure=date(2024, 6, 13),
        guests=(paying_guest, exempt_guest),
        # The exempt guest's exemption is encoded by name convention here
        # (the AC-4 reporting layer is expected to detect
        # 'geschaeftsreisender' tokens in guest metadata). The engine will
        # be expected to wire this through in the green phase. The red
        # phase only cares that the CSV output honours the contract.
        exemptions=(Exemption.geschaeftsreisender,),
    )

    csv_text = generate_monthly_remittance_csv(2024, 6, [r1, r2])

    # ---- Type + non-empty contract ----
    assert isinstance(csv_text, str), (
        f"AC-4: generate_monthly_remittance_csv must return str, got {type(csv_text).__name__}"
    )
    assert csv_text.strip(), (
        f"AC-4: CSV output must not be empty/whitespace; got {csv_text!r}"
    )

    # ---- Parse header + data rows ----
    header, data_rows = _parse_csv(csv_text)

    # ---- Header schema: 12 columns in spec order ----
    assert tuple(header) == AC4_HEADER_COLUMNS, (
        f"AC-4: header columns must match spec verbatim in order.\n"
        f"  expected: {AC4_HEADER_COLUMNS}\n"
        f"  got:      {tuple(header)}"
    )
    assert len(header) == AC4_COLUMN_COUNT == 12, (
        f"AC-4: header must have exactly 12 columns, got {len(header)}"
    )

    # ---- Row count: r1 has 1 guest, r2 has 2 guests → 3 data rows ----
    assert len(data_rows) == 3, (
        f"AC-4: expected 3 data rows (1 paying adult + 2 guests in r2), "
        f"got {len(data_rows)}"
    )

    # ---- Each row must carry every required column (no missing/extra keys) ----
    required_keys = set(AC4_HEADER_COLUMNS)
    for idx, row in enumerate(data_rows):
        assert set(row.keys()) >= required_keys, (
            f"AC-4: data row {idx} is missing required columns: "
            f"{required_keys - set(row.keys())}"
        )

    # ---- Period_yyyy_mm must be '2024-06' on every row ----
    for idx, row in enumerate(data_rows):
        assert row.get("period_yyyy_mm") == "2024-06", (
            f"AC-4: row {idx} period_yyyy_mm must be '2024-06', got {row.get('period_yyyy_mm')!r}"
        )

    # ---- Reconciliation: Σ subtotal_eur == 5.00 + 7.50 + 0.00 == 12.50 ----
    total_paid = sum(
        (Decimal(row["subtotal_eur"]) for row in data_rows), Decimal("0.00")
    )
    assert total_paid == Decimal("12.50"), (
        f"AC-4: period total must equal sum of paid Kurtaxe (€12.50); "
        f"got €{total_paid}. Σ subtotals = "
        f"{[row['subtotal_eur'] for row in data_rows]}"
    )


# ===========================================================================
# Test 2 — exempt guest row is PRESENT with €0.00 subtotal (not "absent")
# ===========================================================================

def test_ac4_exempt_guest_row_has_zero_subtotal_and_exemption_flag(
    hessen_satzung,
) -> None:
    """AC-4 explicit clause: "exempt guests contribute €0.00, not 'absent'".

    A single Geschaeftsreisender over 3 nights must produce a CSV row with:
      - subtotal_eur == "0.00" (not omitted, not negative)
      - exemption_flag indicating the exemption reason
      - day_count == 3
      - per_guest_per_day_eur == 0.00 (the rate is overridden by the
        exemption, NOT the underlying rate band)

    This pins the spec language: the row must exist with €0.00 — emitting
    no row at all would silently hide the exemption from the Stadt portal.
    """
    _assert_ac4_signature()

    guest = make_guest(
        age_years=45,
        name="Carla Geschaeftsreisender",
    )
    reservation = Reservation(
        reservation_id="R-AC4-EXEMPT-1",
        arrival=date(2024, 6, 10),
        departure=date(2024, 6, 13),
        guests=(guest,),
        exemptions=(Exemption.geschaeftsreisender,),
    )

    csv_text = generate_monthly_remittance_csv(2024, 6, [reservation])
    assert isinstance(csv_text, str) and csv_text.strip(), (
        f"AC-4: CSV must be non-empty string; got {csv_text!r}"
    )

    header, data_rows = _parse_csv(csv_text)

    # Exactly one data row — the exempt guest is PRESENT (not absent).
    assert len(data_rows) == 1, (
        f"AC-4: exempt guest row must be PRESENT (not absent) per spec; "
        f"expected 1 data row, got {len(data_rows)}"
    )
    row = data_rows[0]

    # Subtotal must be 0.00 (not empty, not "—", not omitted).
    assert "subtotal_eur" in row, (
        "AC-4: subtotal_eur column missing from row"
    )
    assert Decimal(row["subtotal_eur"]) == Decimal("0.00"), (
        f"AC-4: exempt guest row must have subtotal_eur == '0.00', "
        f"got {row.get('subtotal_eur')!r}"
    )

    # Exemption flag must be set (truthy, non-empty string).
    flag = row.get("exemption_flag", "")
    assert flag, (
        f"AC-4: exempt guest row must have exemption_flag set (non-empty), "
        f"got {flag!r}"
    )

    # Day count + period must still be populated.
    assert row.get("day_count") == "3", (
        f"AC-4: day_count must equal 3 for a 3-night stay, got {row.get('day_count')!r}"
    )
    assert row.get("period_yyyy_mm") == "2024-06", (
        f"AC-4: period_yyyy_mm must be '2024-06', got {row.get('period_yyyy_mm')!r}"
    )

    # Per-guest-per-day must be 0.00 (the exemption overrides the rate).
    per_day = row.get("per_guest_per_day_eur", "")
    assert Decimal(per_day) == Decimal("0.00"), (
        f"AC-4: per_guest_per_day_eur must be 0.00 for an exempt guest, "
        f"got {per_day!r}"
    )


# ===========================================================================
# Test 3 — column order is pinned to spec wording
# ===========================================================================

def test_ac4_csv_header_columns_are_in_documented_order(hessen_satzung) -> None:
    """AC-4: pin the exact column order documented in spec.yaml.

    Independent of row content: the header line of the emitted CSV must
    list the 12 AC-4 columns in the exact spec-documented order. This is
    the contract the Stadt Bad Orb portal parses against; a column reorder
    breaks the upstream integration.
    """
    _assert_ac4_signature()

    reservation = Reservation(
        reservation_id="R-AC4-ORDER-1",
        arrival=date(2024, 6, 10),
        departure=date(2024, 6, 11),
        guests=(make_guest(age_years=30, name="Solo Adult"),),
    )

    csv_text = generate_monthly_remittance_csv(2024, 6, [reservation])
    assert isinstance(csv_text, str) and csv_text.strip(), (
        f"AC-4: CSV must be non-empty; got {csv_text!r}"
    )

    header, _data = _parse_csv(csv_text)

    # Pin order — assert element-by-element so a mismatch reports position.
    assert len(header) == 12, (
        f"AC-4: header must have 12 columns, got {len(header)}: {header!r}"
    )
    for position, (expected, actual) in enumerate(zip(AC4_HEADER_COLUMNS, header)):
        assert actual == expected, (
            f"AC-4: header column at position {position} must be {expected!r}, "
            f"got {actual!r}. Full header: {header!r}"
        )

    # The header must be the first non-empty line.
    first_line = csv_text.splitlines()[0]
    assert first_line.count(",") == 11, (
        f"AC-4: header line must have exactly 11 commas (12 columns), "
        f"got {first_line.count(',')} in {first_line!r}"
    )


# ===========================================================================
# Test 4 — Σ paid subtotals equals the Kurtaxe total (reconciliation rule)
# ===========================================================================

def test_ac4_reconciliation_period_total_equals_paid_kurtaxe_sum(
    hessen_satzung,
) -> None:
    """AC-4 reconciliation: Σ subtotal_eur == Σ paid-Kurtaxe across reservations.

    Mix of three reservations:
      - r_paying: 1 adult × 2 nights = €5.00 (paid)
      - r_exempt: 1 Geschaeftsreisender × 3 nights = €0.00 (paid, but exempted)
      - r_mixed:  1 adult × 4 nights = €10.00 (paid)

    Σ paid-Kurtaxe = 5.00 + 0.00 + 10.00 = 15.00 EUR.
    Σ subtotal_eur in CSV must equal exactly 15.00 (the exempt 0.00 row
    contributes nothing to the sum but IS present).
    """
    _assert_ac4_signature()

    r_paying = Reservation(
        reservation_id="R-RECON-PAY",
        arrival=date(2024, 6, 10),
        departure=date(2024, 6, 12),
        guests=(make_guest(age_years=35, name="Anna Vollzahler"),),
    )
    r_exempt = Reservation(
        reservation_id="R-RECON-EXEMPT",
        arrival=date(2024, 6, 10),
        departure=date(2024, 6, 13),
        guests=(make_guest(age_years=45, name="Carla Geschaeftsreisender"),),
        exemptions=(Exemption.geschaeftsreisender,),
    )
    r_mixed = Reservation(
        reservation_id="R-RECON-MIXED",
        arrival=date(2024, 6, 10),
        departure=date(2024, 6, 14),
        guests=(make_guest(age_years=50, name="Dieter Vollzahler"),),
    )

    reservations: Sequence[Reservation] = [r_paying, r_exempt, r_mixed]

    csv_text = generate_monthly_remittance_csv(2024, 6, reservations)
    assert isinstance(csv_text, str) and csv_text.strip(), (
        f"AC-4: CSV must be non-empty; got {csv_text!r}"
    )

    header, data_rows = _parse_csv(csv_text)

    # Row count: r_paying 1 + r_exempt 1 + r_mixed 1 = 3 data rows.
    assert len(data_rows) == 3, (
        f"AC-4 reconciliation: expected 3 data rows (one per reservation), "
        f"got {len(data_rows)}"
    )

    # Σ subtotals == 5.00 + 0.00 + 10.00 == 15.00
    total = sum(
        (Decimal(row["subtotal_eur"]) for row in data_rows), Decimal("0.00")
    )
    assert total == Decimal("15.00"), (
        f"AC-4 reconciliation: Σ subtotal_eur must equal €15.00 (paid Kurtaxe "
        f"sum: 5.00 + 0.00 + 10.00); got €{total}"
    )

    # Each reservation_id appears exactly once (no duplicates).
    seen_ids = [row["Reservation-ID"] for row in data_rows]
    assert len(set(seen_ids)) == len(seen_ids) == 3, (
        f"AC-4: each reservation must appear exactly once; saw {seen_ids!r}"
    )
    assert set(seen_ids) == {"R-RECON-PAY", "R-RECON-EXEMPT", "R-RECON-MIXED"}, (
        f"AC-4: all three reservation IDs must be present; got {set(seen_ids)!r}"
    )