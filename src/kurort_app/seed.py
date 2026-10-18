"""Deterministic demo data around the business date.

33 rooms and roughly ten weeks of stays (four weeks back, six ahead) with
lifecycle states that match the calendar: past stays are checked out,
current ones in house, today's arrivals waiting. A handful of deliberate
exceptions (missing birth date, missing exemption proof, unsigned
Meldeschein) give the front desk something real to resolve in a demo.
"""

from __future__ import annotations

import random
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from kurort_app.config import today as business_today
from kurort_app.defaults import ensure_defaults
from kurort_app.models import (
    CANCELLED,
    CHECKED_IN,
    CHECKED_OUT,
    MELDESCHEIN_OPEN,
    MELDESCHEIN_PRINTED,
    MELDESCHEIN_SIGNED,
    NO_SHOW,
    RESERVED,
    Guest,
    Reservation,
    ReservationGuest,
    Room,
)

SEED = 2026
HOTEL_TZ = ZoneInfo("Europe/Berlin")

# (category, max_occupancy, nightly_rate, features)
ROOM_TYPES = {
    "Einzelzimmer": (1, Decimal("89.00"), "Duschbad"),
    "Doppelzimmer": (2, Decimal("129.00"), "Duschbad, Balkon"),
    "Komfort-Doppelzimmer": (3, Decimal("149.00"), "Badewanne, Balkon, Kurparkblick"),
    "Suite": (4, Decimal("219.00"), "Wohnbereich, Balkon, Kurparkblick"),
}
# 33 rooms over three floors: 1xx/2xx have 11 rooms each, 3xx holds the suites.
ROOM_LAYOUT = (
    ["Einzelzimmer"] * 4 + ["Doppelzimmer"] * 5 + ["Komfort-Doppelzimmer"] * 2,
    ["Einzelzimmer"] * 3 + ["Doppelzimmer"] * 6 + ["Komfort-Doppelzimmer"] * 2,
    ["Einzelzimmer"] * 2 + ["Doppelzimmer"] * 4 + ["Komfort-Doppelzimmer"] * 3 + ["Suite"] * 2,
)

FIRST_NAMES_F = (
    "Marianne",
    "Ursula",
    "Helga",
    "Renate",
    "Gisela",
    "Brigitte",
    "Monika",
    "Sabine",
    "Petra",
    "Karin",
    "Ingrid",
    "Elke",
    "Gabriele",
    "Christa",
    "Hannelore",
    "Anja",
    "Claudia",
    "Susanne",
    "Birgit",
    "Heike",
    "Annette",
    "Doris",
    "Edith",
    "Waltraud",
)
FIRST_NAMES_M = (
    "Klaus",
    "Wolfgang",
    "Jürgen",
    "Dieter",
    "Manfred",
    "Peter",
    "Hans-Joachim",
    "Werner",
    "Günter",
    "Horst",
    "Rainer",
    "Bernd",
    "Uwe",
    "Michael",
    "Thomas",
    "Frank",
    "Joachim",
    "Gerhard",
    "Heinz",
    "Karl-Heinz",
    "Stefan",
    "Andreas",
    "Ralf",
    "Helmut",
)
LAST_NAMES = (
    "Müller",
    "Schmidt",
    "Schneider",
    "Fischer",
    "Weber",
    "Meyer",
    "Wagner",
    "Becker",
    "Schulz",
    "Hoffmann",
    "Koch",
    "Richter",
    "Klein",
    "Wolf",
    "Schröder",
    "Neumann",
    "Schwarz",
    "Zimmermann",
    "Braun",
    "Krüger",
    "Hofmann",
    "Hartmann",
    "Lange",
    "Schmitt",
    "Werner",
    "Krause",
    "Meier",
    "Lehmann",
    "Schmid",
    "Schulze",
    "Maier",
    "Köhler",
    "Herrmann",
    "König",
    "Walter",
    "Mayer",
    "Huber",
    "Kaiser",
    "Fuchs",
    "Peters",
    "von der Lindenberg-Steinberg",
    "Großmann-Überall",
    "Brückner",
    "Weißenfels",
)
CITIES = (
    ("60311", "Frankfurt am Main"),
    ("63450", "Hanau"),
    ("63571", "Gelnhausen"),
    ("36037", "Fulda"),
    ("63739", "Aschaffenburg"),
    ("65183", "Wiesbaden"),
    ("64283", "Darmstadt"),
    ("35390", "Gießen"),
    ("34117", "Kassel"),
    ("97070", "Würzburg"),
    ("50667", "Köln"),
    ("40213", "Düsseldorf"),
    ("70173", "Stuttgart"),
    ("80331", "München"),
    ("20095", "Hamburg"),
    ("10115", "Berlin"),
    ("04109", "Leipzig"),
    ("55116", "Mainz"),
)
STREETS = (
    "Hauptstraße",
    "Bahnhofstraße",
    "Gartenweg",
    "Lindenallee",
    "Schillerstraße",
    "Goethestraße",
    "Am Kurpark",
    "Mühlweg",
    "Rosenweg",
    "Bergstraße",
    "Kirchgasse",
)
FOREIGN = (  # (nationality, city, postal code, street)
    ("NL", "Utrecht", "3511", "Oudegracht"),
    ("AT", "Linz", "4020", "Landstraße"),
    ("CH", "Basel", "4051", "Freie Strasse"),
    ("FR", "Strasbourg", "67000", "Rue des Juifs"),
    ("PL", "Wrocław", "50-001", "ul. Świdnicka"),
)
NOTES = (
    "Wünscht ruhiges Zimmer zum Park.",
    "Laktosefreies Frühstück.",
    "Anreise mit der Bahn, Abholung Bahnhof Wächtersbach.",
    "Stammgast seit 2014.",
    "Rollator – Zimmer nahe Aufzug.",
    "Termin Badearzt am Anreisetag 16:00.",
)
STAY_LENGTHS = (2, 3, 3, 4, 5, 7, 7, 7, 10, 14, 14, 21)
PACKAGES = {3: "A", 7: "B", 10: "C", 14: "D", 21: "E"}


def _birth_date(rng: random.Random, age: int, anchor: date) -> date:
    return date(anchor.year - age, rng.randint(1, 12), rng.randint(1, 28))


def _make_guest(
    rng: random.Random,
    anchor: date,
    *,
    last_name: str | None = None,
    female: bool | None = None,
    age: int | None = None,
    foreign: bool = False,
) -> Guest:
    female = rng.random() < 0.55 if female is None else female
    first = rng.choice(FIRST_NAMES_F if female else FIRST_NAMES_M)
    last = last_name or rng.choice(LAST_NAMES)
    age = age if age is not None else rng.choice((48, 55, 59, 62, 66, 68, 71, 73, 76, 79, 82))
    if foreign:
        nationality, city, postal, street = rng.choice(FOREIGN)
        country = nationality
    else:
        nationality, country = "DE", "DE"
        postal, city = rng.choice(CITIES)
        street = rng.choice(STREETS)
    disability = None
    roll = rng.random()
    if age >= 16 and roll < 0.06:
        disability = rng.choice((70, 80, 90))
    slug = (
        f"{first}.{last}".lower()
        .replace(" ", "")
        .replace("ü", "ue")
        .replace("ö", "oe")
        .replace("ä", "ae")
        .replace("ß", "ss")
    )
    return Guest(
        first_name=first,
        last_name=last,
        birth_date=_birth_date(rng, age, anchor),
        nationality=nationality,
        street=f"{street} {rng.randint(1, 120)}",
        postal_code=postal,
        city=city,
        country=country,
        email=f"{slug}@example.de" if rng.random() < 0.8 else None,
        phone=f"+49 {rng.randint(150, 179)} {rng.randint(1000000, 9999999)}"
        if rng.random() < 0.7
        else None,
        id_document_number=f"L{rng.randint(10000000, 99999999)}" if foreign else None,
        disability_pct=disability,
    )


def _party(rng: random.Random, anchor: date, capacity: int) -> list[Guest]:
    roll = rng.random()
    foreign = rng.random() < 0.08
    if capacity == 1 or roll < 0.3:
        return [_make_guest(rng, anchor, foreign=foreign)]
    lead = _make_guest(rng, anchor, foreign=foreign)
    partner = _make_guest(
        rng,
        anchor,
        last_name=lead.last_name,
        female=lead.first_name in FIRST_NAMES_M,
        age=max(30, (anchor.year - lead.birth_date.year) + rng.randint(-4, 4)),
        foreign=foreign,
    )
    party = [lead, partner]
    if capacity >= 3 and roll > 0.88:
        party.append(
            _make_guest(rng, anchor, last_name=lead.last_name, age=rng.choice((4, 8, 12, 15)))
        )
    return party


def reset_demo_data(session: Session) -> None:
    """Empty every table and restart the ids, so a reseed is reproducible.

    Settings rows go too; ``seed_demo_data`` puts the defaults back.
    """
    tables = session.scalars(
        text(
            "SELECT quote_ident(tablename) FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
        )
    ).all()
    session.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))
    session.commit()


def seed_demo_data(
    session: Session, *, if_empty: bool = False, reset: bool = False, anchor: date | None = None
) -> int:
    """Create rooms, guests and reservations. Returns the number of reservations created."""
    if reset:
        reset_demo_data(session)
    elif if_empty and session.scalar(select(func.count()).select_from(Reservation)):
        return 0
    ensure_defaults(session)

    rng = random.Random(SEED)
    anchor = anchor or business_today()
    now = datetime.now(UTC)

    rooms: list[Room] = []
    for floor, categories in enumerate(ROOM_LAYOUT, start=1):
        for idx, category in enumerate(categories, start=1):
            occupancy, rate, features = ROOM_TYPES[category]
            rooms.append(
                Room(
                    number=f"{floor}{idx:02d}",
                    category=category,
                    floor=floor,
                    max_occupancy=occupancy,
                    nightly_rate=rate,
                    features=features,
                )
            )
    session.add_all(rooms)
    session.flush()

    window_start, window_end = anchor - timedelta(days=28), anchor + timedelta(days=42)
    counter = 0
    created: list[Reservation] = []
    for room in rooms:
        cursor = window_start - timedelta(days=rng.randint(0, 10))
        while cursor < window_end:
            cursor += timedelta(days=rng.choice((0, 0, 0, 1, 1, 2, 3)))
            nights = rng.choice(STAY_LENGTHS)
            arrival, departure = cursor, cursor + timedelta(days=nights)
            cursor = departure
            if departure < window_start:
                continue
            counter += 1
            guests = _party(rng, anchor, room.max_occupancy)
            channel = rng.choices(
                ("direct", "phone", "email", "booking.com"), weights=(30, 30, 15, 25)
            )[0]
            reservation = Reservation(
                code=f"R-{arrival:%y%m}-{counter:04d}",
                room=room,
                arrival=arrival,
                departure=departure,
                channel=channel,
                eta=time(
                    rng.choice((11, 12, 13, 14, 14, 15, 15, 16, 17, 18)),
                    rng.choice((0, 15, 30, 45)),
                ),
                rate_total=room.nightly_rate * nights,
                package_code=PACKAGES.get(nights) if rng.random() < 0.7 else None,
                notes=rng.choice(NOTES) if rng.random() < 0.25 else None,
            )
            for position, guest in enumerate(guests):
                reservation.guests.append(
                    ReservationGuest(guest=guest, is_primary=position == 0, position=position)
                )
            _apply_lifecycle(rng, reservation, anchor, now)
            created.append(reservation)
    session.add_all(created)
    session.flush()
    _plant_exceptions(rng, created, anchor)
    from kurort_app.services.engine import assess_seeded_stays  # noqa: PLC0415

    assess_seeded_stays(session, created)
    _seed_seminar(session, anchor, created)
    from kurort_app.apps.demo import seed_apps  # noqa: PLC0415

    seed_apps(session, anchor)
    session.commit()
    return len(created)


def _apply_lifecycle(rng: random.Random, res: Reservation, anchor: date, now: datetime) -> None:
    def at(day: date, hour: int) -> datetime:
        return datetime.combine(day, time(hour, rng.randint(0, 59)), tzinfo=HOTEL_TZ)

    if res.departure < anchor or (res.departure == anchor and rng.random() < 0.3):
        res.status = CHECKED_OUT
        res.checked_in_at, res.checked_out_at = at(res.arrival, 15), at(res.departure, 10)
    elif res.arrival < anchor:
        res.status = CHECKED_IN
        res.checked_in_at = at(res.arrival, 15)
    elif res.arrival > anchor and rng.random() < 0.04:
        res.status = CANCELLED
    else:
        res.status = RESERVED

    if res.status in (CHECKED_IN, CHECKED_OUT):
        for rg in res.guests:
            rg.meldeschein_status = MELDESCHEIN_SIGNED
            rg.meldeschein_printed_at = rg.meldeschein_signed_at = res.checked_in_at
    # Departure-day stays are still "checked_in" until the desk checks them out.
    _ = now


def _plant_exceptions(rng: random.Random, reservations: list[Reservation], anchor: date) -> None:
    """Make the demo day interesting: a few things the desk has to fix."""
    arrivals = [r for r in reservations if r.arrival == anchor and r.status == RESERVED]
    in_house = [r for r in reservations if r.status == CHECKED_IN and r.departure > anchor]
    past = [
        r
        for r in reservations
        if r.arrival == anchor - timedelta(days=1) and r.status == CHECKED_IN
    ]

    if arrivals:
        arrivals[0].primary_guest.birth_date = None  # blocker: Meldeschein needs it
    if len(arrivals) > 1:
        lead = arrivals[1].guests[0]
        lead.exemption_category = "geschaeftsreisender"  # proof still missing
        arrivals[1].notes = "Dienstreise – Arbeitgeberbescheinigung wird nachgereicht."
    if len(arrivals) > 2:
        lead = arrivals[2].guests[0]
        lead.guest.disability_pct = 100
        lead.exemption_category = "schwerbehindert_100"
        lead.exemption_evidence = f"Schwerbehindertenausweis Nr. {rng.randint(100000, 999999)}"
    if in_house:
        unsigned = in_house[0].guests[0]
        unsigned.meldeschein_status = MELDESCHEIN_PRINTED
        unsigned.meldeschein_signed_at = None
    if past:
        past[0].status = NO_SHOW
        past[0].checked_in_at = None
        for rg in past[0].guests:
            rg.meldeschein_status = MELDESCHEIN_OPEN
            rg.meldeschein_printed_at = rg.meldeschein_signed_at = None


def _seed_seminar(session: Session, anchor: date, reservations: list[Reservation]) -> None:
    from kurort_app.models import FunctionSpace, SpaceBooking
    from kurort_app.services.seminar import calculate_price

    space = session.scalar(select(FunctionSpace).order_by(FunctionSpace.position, FunctionSpace.id))
    linked_day = anchor + timedelta(days=3)
    linked = next(
        r
        for r in sorted(reservations, key=lambda r: r.id)
        if r.status != CANCELLED and r.arrival <= linked_day < r.departure
    )
    specs = [
        (1, 1, "ganztags", "bestaetigt", "Spessart Physio GmbH", 14),
        (3, 3, "nachmittag", "bestaetigt", None, 8),
        (2, 2, "vormittag", "storniert", "Physiokurs", 10),
        (6, 7, "vormittag", "angefragt", "Volkshochschule Bad Orb", 12),
        (-5, -5, "ganztags", "bestaetigt", "Seminar am Kurpark", 16),
    ]
    for idx, (start, end, slot, status, company, attendees) in enumerate(specs):
        first, last = anchor + timedelta(days=start), anchor + timedelta(days=end)
        session.add(
            SpaceBooking(
                space=space,
                start_date=first,
                end_date=last,
                slot=slot,
                status=status,
                organizer_name=linked.primary_guest.full_name if idx == 1 else "Anna Berg",
                company=company,
                email="seminar@example.de",
                phone=None,
                attendees=attendees,
                catering_coffee=idx == 0,
                catering_lunch=idx == 0,
                catering_drinks=idx == 3,
                price=calculate_price(space, first, last, slot),
                price_manual=False,
                reservation=linked if idx == 1 else None,
                cancelled_at=datetime.combine(anchor, time(9), tzinfo=HOTEL_TZ)
                if idx == 2
                else None,
                cancel_reason="Kurs abgesagt" if idx == 2 else None,
            )
        )
