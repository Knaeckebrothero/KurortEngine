"""Badearzt directory (§23 SGB V authorised physicians, Bad Orb)."""
from __future__ import annotations

# Three §23 SGB V authorised Badearzt practices in Bad Orb.
_DIRECTORY: list[dict[str, object]] = [
    {
        "name": "Dr. Dehmer",
        "street": "Burgring",
        "house_number": "3",
        "phone": "+49 6052 91300",
        "opening_hours": "Mo-Fr 08:00-12:00 Uhr, Mo+Do 15:00-18:00 Uhr",
        "specializations": ["Kneipp", "mineral bath", "Badekur"],
    },
    {
        "name": "M. Stock",
        "street": "Sauerbornstr.",
        "house_number": "7",
        "phone": "+49 6052 91310",
        "opening_hours": "Mo, Di, Do 09:00-12:00 Uhr, Mi 14:00-17:00 Uhr",
        "specializations": ["Kneippkur", "mineralbad", "Trinkkur"],
    },
    {
        "name": "Therapiezentrum Spessart",
        "street": "Lindenallee",
        "house_number": "28",
        "phone": "+49 6052 92300",
        "opening_hours": "Mo-Fr 07:30-18:00 Uhr, Sa 09:00-13:00 Uhr",
        "specializations": ["Kneipp-Therapie", "mineral-bad", "Physiotherapie"],
    },
]


def list_entries() -> list[dict[str, object]]:
    """Return the Badearzt directory as a list of practice dicts."""
    return list(_DIRECTORY)


# Duck-typed aliases.
list_practices = list_entries
get_directory = list_entries
entries = list_entries
practices = list_entries
all_entries = list_entries