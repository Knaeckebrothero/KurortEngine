"""Q5.7 AC-8 — Badearzt directory test surface.

AC-8 contract (verbatim from spec.yaml):

    When guest requests a Badearzt referral THEN the ``badearzt_directory``
    module shall return a directory listing containing:
        Dr. Dehmer (Burgring 3, +49 6052 91300),
        M. Stock (Sauerbornstr. 7),
        Therapiezentrum Spessart (Lindenallee 28)
    — each entry shall include opening hours AND specializations listing at
    minimum Kneipp + mineral bath.

RED VERIFY
----------
Test MUST fail with ``AssertionError``, NOT ImportError. We use
``importlib.util.find_spec`` as a pre-check so missing-module failures
surface as ``AssertionError`` ("module should exist"), not
``ModuleNotFoundError``.
"""
from __future__ import annotations

import importlib.util


def _badearzt_directory_is_importable() -> str:
    """Pre-check: the badearzt_directory module must exist."""
    found = importlib.util.find_spec("kurort_engine.badearzt_directory")
    assert found is not None, (
        "kurort_engine.badearzt_directory is not importable — green phase "
        "must create repo/src/kurort_engine/badearzt_directory.py before "
        f"this test can pass. find_spec returned: {found!r}"
    )
    return f"found at {found.origin if hasattr(found, 'origin') else '<namespace>'}"


# Concrete expected entries (pinned addresses per AC-8).
_DEHMER_NAME = "Dehmer"
_DEHMER_STREET = "Burgring"
_DEHMER_HOUSE_NUMBER = "3"
_DEHMER_PHONE = "06052 91300"
_DEHMER_PHONE_INTL = "+49 6052 91300"

_STOCK_NAME = "Stock"
_STOCK_STREET = "Sauerbornstr"
_STOCK_HOUSE_NUMBER = "7"

_SPESSART_NAME = "Therapiezentrum Spessart"
_SPESSART_STREET = "Lindenallee"
_SPESSART_HOUSE_NUMBER = "28"

# Kneipp + mineral bath are the minimum specialization set per AC-8.
_REQUIRED_SPECIALIZATIONS = ("Kneipp", "mineral bath")


def _get_directory_module():
    """Import the directory module after the find_spec guard."""
    _badearzt_directory_is_importable()
    import kurort_engine.badearzt_directory as _bd  # noqa: E402
    assert _bd is not None, "importlib returned None — module is None"
    return _bd


def _entry_field(entry: object, *names: str) -> object:
    """Return the first matching field on ``entry`` from a list of candidate names.

    Used to tolerate minor naming variation between green-phase candidates
    (e.g. ``opening_hours`` vs ``hours`` vs ``open_hours``).
    """
    candidates: list[str] = list(names)
    if hasattr(entry, "__dict__"):
        candidates.extend(list(entry.__dict__.keys()))
    if isinstance(entry, dict):
        candidates.extend(list(entry.keys()))
    seen = set()
    for name in candidates:
        if name in seen:
            continue
        seen.add(name)
        value = entry.get(name) if isinstance(entry, dict) else getattr(entry, name, None)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (tuple, list, dict)) and len(value) == 0:
            continue
        return value
    return None


# ===========================================================================
# AC-8 — Badearzt directory lists three practices with required details
# ===========================================================================

def test_ac8_directory_lists_three_practices() -> None:
    """AC-8 spec test_oracle.

    Asserts:
      * The directory exposes a public listing function (e.g. ``list_entries``,
        ``list_practices``, ``get_directory``, ``entries``, ``practices``)
        that returns at least 3 entries.
      * Entry 1 — Dr. Dehmer at Burgring 3, phone +49 6052 91300.
      * Entry 2 — M. Stock at Sauerbornstr. 7.
      * Entry 3 — Therapiezentrum Spessart at Lindenallee 28.
      * Each entry has non-empty ``opening_hours`` AND ``specializations``;
        the specializations list MUST contain BOTH ``Kneipp`` and
        ``mineral bath`` (case-insensitive).
    """
    _badearzt_directory_is_importable()
    bd_mod = _get_directory_module()

    # Locate the public listing accessor. Common shapes:
    #   - a function: list_entries() / list_practices() / get_directory()
    #   - a class attribute: ENTRIES / PRACTICES / DIRECTORY
    listing = None
    for candidate_name in (
        "list_entries",
        "list_practices",
        "list_directory",
        "get_directory",
        "directory",
        "entries",
        "practices",
        "all_entries",
    ):
        candidate = getattr(bd_mod, candidate_name, None)
        if candidate is None:
            continue
        if callable(candidate):
            listing = candidate()
        else:
            listing = candidate
        if listing:
            break

    assert listing, (
        "AC-8: badearzt_directory must expose a public listing of at least "
        "3 entries (Dr. Dehmer, M. Stock, Therapiezentrum Spessart). Found "
        f"no callable or attribute that returns a non-empty listing. Module "
        f"surface: {[n for n in dir(bd_mod) if not n.startswith('_')]!r}"
    )

    assert len(listing) >= 3, (
        f"AC-8: directory must contain at least 3 entries; got {len(listing)}"
    )

    # Index the directory by (name substring, street substring) so we can
    # locate each expected practice robustly even if order differs.
    dehmer_entry = None
    stock_entry = None
    spessart_entry = None
    for entry in listing:
        # Name field
        name_field = (
            _entry_field(entry, "name", "doctor", "practice", "title")
            or ""
        )
        name_field_str = str(name_field)
        address_field = (
            _entry_field(entry, "address", "street", "street_address") or ""
        )
        address_field_str = str(address_field)

        if _DEHMER_NAME in name_field_str and _DEHMER_STREET in (
            address_field_str or address_field_str
        ):
            dehmer_entry = entry
        elif _STOCK_NAME in name_field_str and _STOCK_STREET in address_field_str:
            stock_entry = entry
        elif _SPESSART_NAME in name_field_str and _SPESSART_STREET in (
            address_field_str
        ):
            spessart_entry = entry
        else:
            # Fallback: check street-only or name-only
            if _DEHMER_STREET in address_field_str and not dehmer_entry:
                dehmer_entry = entry
            elif _STOCK_STREET in address_field_str and not stock_entry:
                stock_entry = entry
            elif _SPESSART_STREET in address_field_str and not spessart_entry:
                spessart_entry = entry

    # ---- Each expected entry must be present ----
    assert dehmer_entry is not None, (
        "AC-8: directory must contain Dr. Dehmer at Burgring 3 (phone "
        f"{_DEHMER_PHONE_INTL}); entries examined: "
        f"{[str(_entry_field(e, 'name', 'doctor', 'practice')) for e in listing]!r}"
    )
    assert stock_entry is not None, (
        "AC-8: directory must contain M. Stock at Sauerbornstr. 7; entries "
        f"examined: {[str(_entry_field(e, 'name', 'doctor', 'practice')) for e in listing]!r}"
    )
    assert spessart_entry is not None, (
        "AC-8: directory must contain Therapiezentrum Spessart at Lindenallee "
        f"28; entries examined: {[str(_entry_field(e, 'name', 'doctor', 'practice')) for e in listing]!r}"
    )

    # ---- Per-entry required fields ----
    for entry, label, expected_street, expected_house_number in (
        (dehmer_entry, "Dr. Dehmer", _DEHMER_STREET, _DEHMER_HOUSE_NUMBER),
        (stock_entry, "M. Stock", _STOCK_STREET, _STOCK_HOUSE_NUMBER),
        (spessart_entry, _SPESSART_NAME, _SPESSART_STREET, _SPESSART_HOUSE_NUMBER),
    ):
        # Street + house number
        street_field = str(_entry_field(entry, "street", "address", "street_address") or "")
        house_number_field = str(
            _entry_field(entry, "house_number", "house_no", "number") or ""
        )
        combined = f"{street_field} {house_number_field}".strip()
        assert expected_street in combined, (
            f"AC-8: {label}'s street must contain {expected_street!r}; "
            f"got street={street_field!r} house_number={house_number_field!r}"
        )
        assert expected_house_number in combined, (
            f"AC-8: {label}'s address must include house number "
            f"{expected_house_number!r}; got combined={combined!r}"
        )

        # Opening hours — must be a non-empty string or structured field
        hours = _entry_field(
            entry, "opening_hours", "hours", "open_hours", "sprechzeiten"
        )
        assert hours, (
            f"AC-8: {label} must have a non-empty opening_hours field; "
            f"entry={entry!r}"
        )
        # If it's a string, it should look like opening-hours text (contains
        # at least one weekday marker or "Uhr")
        if isinstance(hours, str):
            hours_l = hours.lower()
            looks_like_hours = (
                any(
                    day in hours_l
                    for day in (
                        "mo",
                        "di",
                        "mi",
                        "do",
                        "fr",
                        "sa",
                        "so",
                        "mon",
                        "tue",
                        "wed",
                        "thu",
                        "fri",
                        "sat",
                        "sun",
                        "montag",
                        "dienstag",
                        "mittwoch",
                        "donnerstag",
                        "freitag",
                        "samstag",
                        "sonntag",
                    )
                )
                or "uhr" in hours_l
                or "-" in hours
                or ":" in hours
            )
            assert looks_like_hours, (
                f"AC-8: {label}'s opening_hours must look like opening-hours "
                f"text (weekday or 'Uhr'); got {hours!r}"
            )

        # Specializations — must contain both Kneipp and mineral bath
        specs = _entry_field(
            entry,
            "specializations",
            "specialities",
            "specialty",
            "treatments",
            "leistungen",
        )
        assert specs, (
            f"AC-8: {label} must list specializations; got entry={entry!r}"
        )
        # specs can be a list/tuple of strings OR a comma-separated string
        if isinstance(specs, (list, tuple)):
            spec_set = {str(s).lower() for s in specs}
        elif isinstance(specs, str):
            spec_set = {chunk.strip().lower() for chunk in specs.split(",")}
        else:
            spec_set = {str(specs).lower()}
        spec_text = " ".join(spec_set)

        for required in _REQUIRED_SPECIALIZATIONS:
            required_l = required.lower()
            # Allow common variants: "kneipp" / "kneippkur" / "kneipp-therapie"
            # and "mineral bath" / "mineralbad" / "mineral-bad"
            variants_present = required_l in spec_text or any(
                variant in spec_text
                for variant in (
                    "kneipp" if required_l == "kneipp" else "mineralbad",
                    "kneippkur" if required_l == "kneipp" else "mineral-bad",
                    "kneipp-therapie" if required_l == "kneipp" else "mineral bath",
                    "kneipptherapie" if required_l == "kneipp" else "min.bath",
                )
            )
            assert variants_present, (
                f"AC-8: {label} must list {required!r} in specializations; "
                f"got specs={specs!r} (parsed: {spec_set})"
            )

    # ---- Dehmer phone number ----
    phone = _entry_field(dehmer_entry, "phone", "telephone", "tel", "fon")
    assert phone, (
        f"AC-8: Dr. Dehmer must have a phone number; got entry={dehmer_entry!r}"
    )
    phone_str = str(phone)
    # Accept either the international form or the local form
    has_phone = (
        _DEHMER_PHONE_INTL.replace(" ", "") in phone_str.replace(" ", "")
        or _DEHMER_PHONE.replace(" ", "") in phone_str.replace(" ", "")
        or "605291300" in phone_str.replace(" ", "")
        or "6052/91300" in phone_str
        or "+49605291300" in phone_str.replace(" ", "")
    )
    assert has_phone, (
        f"AC-8: Dr. Dehmer's phone must be {_DEHMER_PHONE_INTL!r} (or the "
        f"local form {_DEHMER_PHONE!r}); got phone={phone_str!r}"
    )