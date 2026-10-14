"""Small, pure German parsing helpers for the demo planner.

Everything here works on plain strings and dates so it can be unit tested
without a database. ``fold`` is the normal form the rules match against:
lower case, umlauts spelled out, single spaces.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "–": "-", "—": "-"})

NUMBER_WORDS = {
    "ein": 1, "eine": 1, "einer": 1, "einen": 1, "eins": 1,
    "zwei": 2, "drei": 3, "vier": 4, "fuenf": 5, "sechs": 6, "sieben": 7,
    "acht": 8, "neun": 9, "zehn": 10, "elf": 11, "zwoelf": 12, "dreizehn": 13,
    "vierzehn": 14, "fuenfzehn": 15, "einundzwanzig": 21,
}  # fmt: skip
_NUMBER = r"(\d+|" + "|".join(sorted(NUMBER_WORDS, key=len, reverse=True)) + r")"

WEEKDAYS = {
    "montag": 0, "dienstag": 1, "mittwoch": 2, "donnerstag": 3,
    "freitag": 4, "samstag": 5, "sonnabend": 5, "sonntag": 6,
}  # fmt: skip

# Folded keyword → room category as stored in rooms.category. Order matters:
# "komfort-doppelzimmer" must win over "doppelzimmer".
CATEGORIES = (
    (r"komfort", "Komfort-Doppelzimmer"),
    (r"suite", "Suite"),
    (r"einzel\w*|\bez\b", "Einzelzimmer"),
    (r"doppel\w*|\bdz\b", "Doppelzimmer"),
)

# Words that end a spoken/typed name ("Herr Klaus Becker, zwei Nächte ...").
_NAME_STOP = {
    "fuer", "mit", "und", "ab", "bis", "von", "vom", "am", "an", "auf", "zum", "zur", "im",
    "heute", "morgen", "uebermorgen", "nacht", "naechte", "woche", "wochen", "zimmer",
    "doppelzimmer", "einzelzimmer", "komfort", "suite", "dz", "ez", "walk", "in", "walk-in",
    "check-in", "bitte", "personen", "person", "erwachsene", "kinder", "kind",
}  # fmt: skip
_SALUTATION = r"(herrn?|frau|familie|fam\.?)"
_NAME_TOKEN = r"[A-Za-zÄÖÜäöüß][\wÄÖÜäöüß'\-]*"


def fold(text: str) -> str:
    """Lower case, umlauts spelled out, whitespace collapsed."""
    return re.sub(r"\s+", " ", text.lower().translate(_UMLAUTS)).strip()


def number(token: str) -> int | None:
    token = fold(token)
    if token.isdigit():
        return int(token)
    return NUMBER_WORDS.get(token)


def parse_nights(folded: str) -> int | None:
    """``zwei Nächte`` → 2, ``1 Nacht`` → 1, ``eine Woche`` → 7."""
    m = re.search(_NUMBER + r"\s*(?:naechte|nacht|uebernachtungen|uebernachtung)\b", folded)
    if m:
        return number(m.group(1))
    m = re.search(_NUMBER + r"\s*wochen?\b", folded)
    if m and (n := number(m.group(1))):
        return n * 7
    return None


def parse_days(folded: str) -> int | None:
    """``30 Tage`` → 30, ``zwei Wochen`` → 14, ``einen Monat`` → 30."""
    m = re.search(_NUMBER + r"\s*tagen?\b", folded)
    if m:
        return number(m.group(1))
    m = re.search(_NUMBER + r"\s*wochen?\b", folded)
    if m and (n := number(m.group(1))):
        return n * 7
    if re.search(r"\bmonat\b", folded):
        return 30
    return None


def parse_category(folded: str) -> str | None:
    for pattern, category in CATEGORIES:
        if re.search(pattern, folded):
            return category
    return None


def parse_room_number(folded: str) -> str | None:
    m = re.search(r"\bzimmer\s*(?:nr\.?|nummer)?\s*(\d{1,4})\b", folded)
    return m.group(1) if m else None


def next_weekday(today: date, weekday: int) -> date:
    """The next given weekday, counting today."""
    return today + timedelta(days=(weekday - today.weekday()) % 7)


def weekend(today: date) -> tuple[date, date]:
    """Nights of the coming weekend: Saturday and Sunday (departure Monday)."""
    if today.weekday() == 6:  # Sunday: what is left of this weekend
        return today, today + timedelta(days=1)
    saturday = next_weekday(today, 5)
    return saturday, saturday + timedelta(days=2)


def _dotted_date(day: str, month: str, year: str | None, today: date) -> date | None:
    try:
        if year:
            y = int(year)
            return date(y + 2000 if y < 100 else y, int(month), int(day))
        candidate = date(today.year, int(month), int(day))
    except ValueError:
        return None
    # Without a year, a date well in the past means the same date next year.
    if candidate < today - timedelta(days=7):
        candidate = candidate.replace(year=today.year + 1)
    return candidate


_DOTTED = r"(\d{1,2})\.(\d{1,2})\.?(\d{2,4})?"


def parse_single_date(folded: str, today: date) -> date | None:
    """``heute``/``morgen``/``übermorgen``, a weekday name, or ``DD.MM.[YYYY]``."""
    m = re.search(r"\b" + _DOTTED, folded)
    if m:
        return _dotted_date(m.group(1), m.group(2), m.group(3), today)
    if re.search(r"\buebermorgen\b", folded):
        return today + timedelta(days=2)
    if re.search(r"\bmorgen\b", folded):
        return today + timedelta(days=1)
    if re.search(r"\bheute\b", folded):
        return today
    for name, weekday in WEEKDAYS.items():
        if re.search(rf"\b{name}\b", folded):
            return next_weekday(today, weekday)
    return None


def parse_target_date(folded: str, today: date) -> date | None:
    """The date a change should move *to*: prefer what follows ``auf``/``zum``/``am``."""
    m = re.search(r"\b(?:auf|zum|am|an den|nach)\b(.*)$", folded)
    if m and (found := parse_single_date(m.group(1), today)):
        return found
    return parse_single_date(folded, today)


def parse_span(folded: str, today: date) -> tuple[date, date] | None:
    """A span of nights ``[start, end)``: ``vom 17.10. bis 19.10.``, ``Wochenende``, one day."""
    m = re.search(r"\bvom\s+" + _DOTTED + r"\s*(?:bis|-)\s*(?:zum\s+)?" + _DOTTED, folded)
    if m:
        start = _dotted_date(m.group(1), m.group(2), m.group(3), today)
        end = _dotted_date(m.group(4), m.group(5), m.group(6), today)
        if start and end:
            return start, end if end > start else start + timedelta(days=1)
    if re.search(r"\bwochenende\b", folded):
        return weekend(today)
    single = parse_single_date(folded, today)
    if single:
        return single, single + timedelta(days=1)
    return None


def _title(token: str) -> str:
    return "-".join(part[:1].upper() + part[1:] for part in token.split("-"))


def extract_new_guest_name(text: str) -> tuple[str | None, str | None] | None:
    """(first, last) for a guest not yet in the system: ``Herr Klaus Becker`` → (Klaus, Becker).

    Looks after a salutation, else after ``für``. ``Familie Becker`` and a
    single word give only a last name.
    """
    m = re.search(rf"\b{_SALUTATION}\s+((?:{_NAME_TOKEN}\s*){{1,3}})", text, re.IGNORECASE)
    family = False
    if m:
        family = fold(m.group(1)).startswith("fam")
        tail = m.group(2)
    else:
        m = re.search(rf"\bf(?:ü|ue)r\s+((?:{_NAME_TOKEN}\s*){{1,3}})", text, re.IGNORECASE)
        if not m:
            return None
        tail = m.group(1)
    tokens: list[str] = []
    for raw in re.findall(_NAME_TOKEN, tail):
        if fold(raw) in _NAME_STOP or number(raw) is not None:
            break
        tokens.append(_title(raw))
    if not tokens:
        return None
    if family or len(tokens) == 1:
        return None, tokens[-1]
    return tokens[0], " ".join(tokens[1:])


def name_score(folded_text: str, first_name: str, last_name: str) -> int:
    """2 = first and last name mentioned, 1 = last name only, 0 = not this person."""
    last = fold(last_name)
    if not last or not re.search(rf"(?<![\w-]){re.escape(last)}(?![\w-])", folded_text):
        return 0
    first = fold(first_name)
    if first and re.search(rf"(?<![\w-]){re.escape(first)}(?![\w-])", folded_text):
        return 2
    return 1


def has_any(folded: str, *patterns: str) -> bool:
    return any(re.search(p, folded) for p in patterns)
