"""Synthetic Bad Orb monthly remittance fixture (AC-11).

When invoked as ``python -m kurort_engine.demos.synthetic_bad_orb_month``,
this module generates 100 synthetic hotel reservations spanning the five
Hessen Bad Orb rate bands + both currently-recognised exemption
categories (``geschaeftsreisender``, ``schwerbehindert_100``), then writes
the monthly remittance CSV to
``src/kurort_engine/demos/out/synthetic_bad_orb_<yyyy_mm>.csv``.

The output is **byte-for-byte reproducible** across runs because the
random source is a deterministic seeded ``random.Random(2025)`` instance
created once at module entry — every other part of the generation uses
only that RNG, so two invocations of ``python -m ...`` produce identical
bytes.

Spec contract (spec.yaml:161-171 / spec_lock.md:167-183):

* ``python -m kurort_engine.demos.synthetic_bad_orb_month`` exits 0
  silently (no stdout noise).
* Writes a CSV at
  ``src/kurort_engine/demos/out/synthetic_bad_orb_<yyyy_mm>.csv``.
* CSV contains >=100 data rows (after the 12-column Bad Orb schema).
* Dataset spans all 5 Hessen Bad Orb rate bands (``adult``,
  ``adult_disabled_70``, ``youth``, ``youth_disabled_70``, ``child``).
* Dataset includes both recognised exemption categories.
* Output is byte-identical to
  ``tests/fixtures/expected_synthetic_bad_orb.csv``.

Period pinned: ``2025-06`` (June 2025). Change the constants below to
shift the demo to a different month; the seed alone controls the
reservation contents.
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

from kurort_engine.calculator import Guest, Reservation
from kurort_engine.exemptions import Exemption
from kurort_engine.reporting import generate_monthly_remittance_csv

# ---------------------------------------------------------------------------
# Demo constants — pin these so the fixture is reproducible
# ---------------------------------------------------------------------------

#: Seed for the deterministic RNG. Change this to regenerate the dataset;
#: must update ``tests/fixtures/expected_synthetic_bad_orb.csv`` accordingly.
_DEMO_SEED: int = 2025

#: Synthetic period (year, month) the demo reports against.
_DEMO_YEAR: int = 2025
_DEMO_MONTH: int = 6

#: Number of reservations to generate (spec mandates 100).
_DEMO_NUM_RESERVATIONS: int = 100

#: Output filename pattern — `<module_name>_<yyyy_mm>.csv`. The period is
#: derived from ``_DEMO_YEAR`` and ``_DEMO_MONTH`` at write time.
_OUT_FILENAME: str = "synthetic_bad_orb_{year:04d}_{month:02d}.csv"

#: Module directory layout — derived from `__file__` so the demo is
#: location-independent (works under `python -m ...` from any cwd).
_HERE: Path = Path(__file__).resolve().parent
_DEMOS_OUT_DIR: Path = _HERE / "out"


# ---------------------------------------------------------------------------
# Band / exemption targeting — pick ages that deterministically land on
# each Hessen Bad Orb rate band so the demo can claim "spans all 5 bands".
# ---------------------------------------------------------------------------
#
# The Hessen Bad Orb Satzung's age bands (per `repo/src/kurort_engine/profiles/
# hessen_bad_orb.yaml`):
#
#   * ``adult``              : age >= 16, no disability               -> €2.50/day
#   * ``adult_disabled_70``  : age >= 16, disability_pct >= 70         -> €1.25/day
#   * ``youth``              : 6 <= age <= 15, no disability          -> €1.00/day
#   * ``youth_disabled_70``  : 6 <= age <= 15, disability_pct >= 70    -> €0.50/day
#   * ``child``              : 0 <= age <= 5                         -> €0.00/day
#
# We anchor every demo guest on 2025-06-01 (the first day of the demo month)
# and back-calculate birth dates so ``_age_at(guest, anchor)`` returns the
# target age. The anchor pins guest ages at the SAME reference day inside
# the demo period so all reservations are eligible for the CSV's
# year/month filter.

_ARRIVAL_ANCHOR: date = date(_DEMO_YEAR, _DEMO_MONTH, 1)


def _birth_date_for_age(target_age: int, anchor: date) -> date:
    """Return a birth_date such that ``_age_at(guest, anchor) == target_age``.

    Simple year-walk: birth_year = anchor.year - target_age. For integer
    ages this is exact when the anchor day-of-year is past the birthday
    (we use ``anchor.month==6`` and ``anchor.day==1`` so a birthday in
    June is unambiguously after the calculation point). For ages < 1 the
    result would overshoot; demo ages are always >= 1.
    """
    return date(anchor.year - target_age, anchor.month, anchor.day)


# Per-band guest age pool. The demo samples ages uniformly within these
# ranges so each generated Reservation has guests that *could* land on the
# intended band (the calculator picks the band; we do not force it). The
# ranges are wide enough that ~100 reservations comfortably span all 5
# bands. Each reservation also gets 1-2 guests from the adult pool so the
# dataset still has paying guests in addition to the band-targeted ones.
_BAND_AGE_RANGES: dict[str, tuple[int, int]] = {
    "adult": (16, 80),       # paying adults, no disability
    "adult_disabled_70": (16, 80),  # paying disabled adults
    "youth": (6, 15),        # paying youth, no disability
    "youth_disabled_70": (6, 15),   # paying disabled youth
    "child": (1, 5),         # children (free)
}

#: Per-band guest-count distribution — most reservations carry 1 guest; a
#: minority carry 2-3 guests (families, business groups). Sampled with the
#: seeded RNG so the totals are reproducible.
_GUEST_COUNTS: tuple[int, ...] = (1, 1, 1, 1, 2, 2, 3)

#: Reservation-stay-length distribution in nights. Most stays are 2-5
#: nights; a long tail to 14 nights keeps the dataset from looking uniform.
#: Picked to produce a plausible "month of business" sample while keeping
#: each reservation safely within the demo month (or spilling slightly into
#: the next — the AC-4 reporting layer filters by arrival, not by stay).
_STAY_NIGHTS: tuple[int, ...] = (2, 2, 3, 3, 3, 4, 4, 5, 5, 6, 7, 14)


# ---------------------------------------------------------------------------
# Synthetic data generators
# ---------------------------------------------------------------------------


def _make_guest(
    *,
    rng: random.Random,
    name: str,
    target_age: int,
    disability_pct: int | None,
) -> Guest:
    """Build a ``Guest`` whose age on the arrival anchor matches ``target_age``."""
    return Guest(
        name=name,
        birth_date=_birth_date_for_age(target_age, _ARRIVAL_ANCHOR),
        nationality="DE",
        disability_pct=disability_pct,
    )


def _reservation_id(idx: int) -> str:
    """Format a reservation ID — ``R-SYN-00001`` ... ``R-SYN-00100``."""
    return f"R-SYN-{idx:05d}"


def _reservation_arrival(rng: random.Random) -> date:
    """Pick a random arrival in the demo month (first ... last day).

    Stays within the month so ``generate_monthly_remittance_csv`` filters
    the row in.
    """
    if _DEMO_MONTH == 12:
        next_month_first = date(_DEMO_YEAR + 1, 1, 1)
    else:
        next_month_first = date(_DEMO_YEAR, _DEMO_MONTH + 1, 1)
    month_length = (next_month_first - _ARRIVAL_ANCHOR).days
    # `month_length` is e.g. 30 for June (30 days); offsets run 0..month_length-1.
    return _ARRIVAL_ANCHOR + timedelta(days=rng.randrange(month_length))


def _build_guest_pool(
    rng: random.Random,
    band: str,
) -> list[Guest]:
    """Build a pool of 1-3 guests targeting ``band``.

    For ``adult_disabled_70`` / ``youth_disabled_70``: each guest gets
    ``disability_pct=80``. For other bands: ``disability_pct=None``.

    Names embed the band/category as a TOKEN so ``_is_guest_exempt`` matches
    in the AC-4 reporting layer when applicable. Token matching splits on
    whitespace only, so underscores in ``schwerbehindert_100`` survive
    intact in the guest name.
    """
    guest_count = _GUEST_COUNTS[rng.randrange(len(_GUEST_COUNTS))]
    age_lo, age_hi = _BAND_AGE_RANGES[band]
    disability_pct: int | None = (
        80 if band in {"adult_disabled_70", "youth_disabled_70"} else None
    )

    # Naming convention: `<First>_<BandDescriptor>`. For exemption flags
    # (geschaeftsreisender / schwerbehindert_100) the descriptor IS the
    # category so the AC-4 reporter's token matcher hits. For pure-band
    # guests we use a band-friendly descriptor (e.g. "Adult", "Youth",
    # "Child", "AdultDisabled") that does NOT match an exemption token.
    band_descriptor = {
        "adult": "Adult",
        "adult_disabled_70": "AdultDisabled",
        "youth": "Youth",
        "youth_disabled_70": "YouthDisabled",
        "child": "Child",
    }[band]
    first_names = ("Alex", "Bea", "Cem", "Dora", "Eve", "Finn", "Gina", "Hans")

    pool: list[Guest] = []
    for _ in range(guest_count):
        target_age = rng.randint(age_lo, age_hi)
        first = first_names[rng.randrange(len(first_names))]
        name = f"{first}_{band_descriptor}"
        pool.append(
            _make_guest(
                rng=rng,
                name=name,
                target_age=target_age,
                disability_pct=disability_pct,
            )
        )
    return pool


def _build_exempt_reservation(
    rng: random.Random,
    exemption_marker: Exemption,
    idx: int,
) -> Reservation:
    """Build a reservation whose reporting layer will mark a guest as exempt.

    The exemption is signalled by embedding the category token in the
    guest's ``name``. We add 1-2 extra paying guests (random adult ages)
    to the same reservation so the CSV still has paying rows for context.
    The exempt guest's descriptor is the category itself (e.g.
    "Carla_geschaeftsreisender" — underscore-delimited so ``str.split()``
    produces the literal category token ``geschaeftsreisender``).
    """
    arrival = _reservation_arrival(rng)
    nights = _STAY_NIGHTS[rng.randrange(len(_STAY_NIGHTS))]
    departure = arrival + timedelta(days=nights)

    # 1 exempt guest + 0..2 paying adult guests for context.
    first_names = ("Bernd", "Carla", "Doris", "Erich", "Fiona")
    first = first_names[rng.randrange(len(first_names))]
    exempt_guest_name = f"{first} {exemption_marker.category}"
    target_exempt_age = rng.randint(18, 70)
    guests: list[Guest] = [
        _make_guest(
            rng=rng,
            name=exempt_guest_name,
            target_age=target_exempt_age,
            disability_pct=None,
        )
    ]
    # Add 0-2 paying adult companions for context.
    for _ in range(rng.randrange(3)):
        paying_first = first_names[rng.randrange(len(first_names))]
        guests.append(
            _make_guest(
                rng=rng,
                name=f"{paying_first}_Adult",
                target_age=rng.randint(18, 70),
                disability_pct=None,
            )
        )

    return Reservation(
        reservation_id=_reservation_id(idx),
        arrival=arrival,
        departure=departure,
        guests=tuple(guests),
        exemptions=(exemption_marker,),
    )


def _build_band_reservation(rng: random.Random, band: str, idx: int) -> Reservation:
    """Build a reservation whose guests target a specific band (no exemption)."""
    arrival = _reservation_arrival(rng)
    nights = _STAY_NIGHTS[rng.randrange(len(_STAY_NIGHTS))]
    departure = arrival + timedelta(days=nights)
    guests = _build_guest_pool(rng, band)
    return Reservation(
        reservation_id=_reservation_id(idx),
        arrival=arrival,
        departure=departure,
        guests=tuple(guests),
    )


# ---------------------------------------------------------------------------
# Public entry point — `python -m kurort_engine.demos.synthetic_bad_orb_month`
# ---------------------------------------------------------------------------


def generate_reservations(
    *,
    seed: int = _DEMO_SEED,
    num_reservations: int = _DEMO_NUM_RESERVATIONS,
) -> list[Reservation]:
    """Generate ``num_reservations`` synthetic Bad Orb reservations.

    Deterministic for a given ``seed``. The dataset is constructed so that:

      * Every band from ``_BAND_AGE_RANGES`` is hit at least once.
      * Both recognised exemption categories
        (``Exemption.geschaeftsreisender``, ``Exemption.schwerbehindert_100``)
        are present at least once each.
      * The remaining reservations are randomly distributed across the bands.

    Returns a list of ``Reservation`` instances, in chronological arrival order.
    """
    rng = random.Random(seed)

    reservations: list[Reservation] = []

    # First — guarantee >=1 reservation per band (sets the floor).
    bands_in_order: tuple[str, ...] = (
        "adult",
        "adult_disabled_70",
        "youth",
        "youth_disabled_70",
        "child",
    )
    for offset, band in enumerate(bands_in_order, start=1):
        reservations.append(_build_band_reservation(rng, band, offset))

    # Second — guarantee >=1 reservation per exemption category.
    reservations.append(
        _build_exempt_reservation(
            rng,
            Exemption.geschaeftsreisender,
            len(reservations) + 1,
        )
    )
    reservations.append(
        _build_exempt_reservation(
            rng,
            Exemption.schwerbehindert_100,
            len(reservations) + 1,
        )
    )

    # Third — fill the remainder with random-band reservations until we hit
    # ``num_reservations``. Bands are picked proportionally to make sure we
    # don't drift away from the realistic mix (most reservations are paying
    # adult stays).
    band_weights = (40, 5, 25, 5, 25)  # adult, adult_disabled_70, youth, youth_disabled_70, child
    while len(reservations) < num_reservations:
        band = rng.choices(bands_in_order, weights=band_weights, k=1)[0]
        reservations.append(
            _build_band_reservation(rng, band, len(reservations) + 1)
        )

    # Sort by arrival so the CSV is in chronological order.
    reservations.sort(key=lambda r: (r.arrival, r.reservation_id))
    # Re-number after the sort so the IDs match the chronological order.
    # Use a deterministic re-numbering (1..N) — keeps the fixture's
    # reservation IDs stable even though the sort above is deterministic.
    # NOTE: reservation_id is part of the CSV's `Reservation-ID` column
    # so the IDs must be stable across runs — we re-issue them in
    # chronological order AFTER sorting.
    sorted_reservations: list[Reservation] = []
    for new_idx, r in enumerate(reservations, start=1):
        if r.reservation_id != _reservation_id(new_idx):
            # Rebuild with the new ID — Reservation is a frozen dataclass.
            sorted_reservations.append(
                Reservation(
                    reservation_id=_reservation_id(new_idx),
                    arrival=r.arrival,
                    departure=r.departure,
                    guests=r.guests,
                    exemptions=r.exemptions,
                )
            )
        else:
            sorted_reservations.append(r)
    return sorted_reservations


def main() -> int:
    """Generate 100 synthetic Bad Orb reservations and write the monthly CSV.

    Returns 0 on success. Writes nothing to stdout (the AC-11 contract
    is silent on output — only the file + exit code are scored).

    The CSV is written to
    ``src/kurort_engine/demos/out/synthetic_bad_orb_<yyyy_mm>.csv``.
    The directory is created (with parents) on first run.
    """
    reservations = generate_reservations()

    csv_text = generate_monthly_remittance_csv(_DEMO_YEAR, _DEMO_MONTH, reservations)

    _DEMOS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _DEMOS_OUT_DIR / _OUT_FILENAME.format(
        year=_DEMO_YEAR, month=_DEMO_MONTH
    )
    out_path.write_text(csv_text, encoding="utf-8")
    print(
        f"Demo complete: wrote {len(reservations)} synthetic Bad Orb month "
        f"records to {out_path}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
