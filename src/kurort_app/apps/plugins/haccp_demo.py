"""Four weeks of kitchen records, relative to the demo business date."""

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from random import Random

from kurort_app.apps import store
from kurort_app.apps.registry import AppRegistry
from kurort_app.config import HOTEL_TZ


def seed_demo(session, anchor_date):
    app = AppRegistry().valid["haccp"]
    rng = Random(20261014)
    actors = ("j.becker", "m.schmidt")

    def stamp(day, hour=7, minute=30):
        return datetime.combine(day, time(hour, minute), HOTEL_TZ).astimezone(UTC)

    def create(collection, data, at):
        actor = rng.choice(actors)
        if any(f.key == "mitarbeiter" for f in app.collection(collection).fields):
            data = {**data, "mitarbeiter": actor}
        return store.create(session, app, collection, data, actor=actor, created_at=at)

    first = anchor_date - timedelta(days=28)
    devices = []
    for name, kind, location, low, high in [
        ("Kühlschrank Küche", "kuehlschrank", "Küche", "0", "7"),
        ("Kühlschrank Frühstücksbuffet", "kuehlschrank", "Frühstück", "0", "7"),
        ("Getränkekühlschrank Bar", "kuehlschrank", "Bar", "0", "7"),
        ("Tiefkühler Küche", "tiefkuehler", "Küche", "-25", "-18"),
        ("Warmhaltung Rührei", "warmhaltung", "Frühstück", "63", None),
    ]:
        data = {"name": name, "typ": kind, "standort": location, "soll_min": low, "aktiv": True}
        if high is not None:
            data["soll_max"] = high
        devices.append(create("geraete", data, stamp(first)))

    for days_ago in range(28, -1, -1):
        day = anchor_date - timedelta(days=days_ago)
        for index, device in enumerate(devices):
            if (days_ago == 0 and index != 0) or (days_ago == 1 and index == 3):
                continue
            if index == 3:
                number = rng.randint(-235, -190)
            elif index == 4:
                number = rng.randint(650, 780)
            else:
                number = rng.randint(25, 60)
            action = ""
            if days_ago == 9 and index == 2:
                number, action = 84, "Tür stand offen, nach 30 Min. 5,9 °C"
            elif days_ago == 3 and index == 3:
                number, action = -165, "Abtauvorgang, nach 1 Std. −19,0 °C"
            at = stamp(day, 7 + (index * 18) // 60, (index * 18) % 60)
            create(
                "messungen",
                {
                    "geraet": device.id,
                    "gemessen_am": at,
                    "temperatur": Decimal(number) / 10,
                    "massnahme": action,
                },
                at,
            )

    for name, interval, hint, tasks in [
        (
            "Kaffeemaschine",
            1,
            "Gehäuse, Tropfschale und Milchsystem reinigen.",
            ["geraet", "oberflaechen"],
        ),
        (
            "Teestation",
            1,
            "Arbeitsfläche und Heißwassergerät reinigen.",
            ["oberflaechen", "geraet"],
        ),
        ("Buffet", 1, "Flächen reinigen und desinfizieren.", ["oberflaechen", "desinfiziert"]),
        (
            "Eierstation",
            1,
            "Warmhaltegerät und Arbeitsfläche reinigen.",
            ["geraet", "oberflaechen"],
        ),
        (
            "Kühlschränke innen",
            7,
            "Innenräume und Einlegeböden gründlich reinigen.",
            ["tiefenreinigung"],
        ),
    ]:
        station = create(
            "stationen",
            {"name": name, "haeufigkeit_tage": interval, "hinweis": hint, "aktiv": True},
            stamp(first),
        )
        for days_ago in range(28, 0, -1):
            if interval == 7 and days_ago != 5:
                continue
            if name == "Eierstation" and days_ago == 1:
                continue
            at = stamp(anchor_date - timedelta(days=days_ago), 11, rng.randrange(30))
            create(
                "reinigungen",
                {
                    "station": station.id,
                    "erledigt_am": at,
                    "aufgaben": tasks,
                    "mittel": "Küchenreiniger",
                },
                at,
            )

    for index, days_ago in enumerate((27, 24, 20, 17, 13, 10, 6, 3)):
        day = anchor_date - timedelta(days=days_ago)
        supplier, product, amount, temperature = [
            ("Molkerei Spessart", "Milch und Joghurt", "10 kg", "4.2"),
            ("Metzgerei Weber", "Rindfleisch", "5 kg", "3.8"),
            ("Bäckerei Müller", "Brötchen", "3 Kartons", None),
            ("Gemüsehof Main-Kinzig", "Saisongemüse", "10 kg", None),
        ][index % 4]
        rejected = days_ago == 6
        if rejected:
            supplier, product, amount, temperature = "Metzgerei Weber", "Hackfleisch", "5 kg", "9.2"
        create(
            "wareneingang",
            {
                "geliefert_am": day,
                "lieferant": supplier,
                "produkt": product,
                "menge": amount,
                "temperatur": temperature,
                "mhd": day + timedelta(days=5),
                "charge": f"RH-{day:%Y%m%d}-{index + 1}",
                "zustand_ok": not rejected,
                "ergebnis": "abgelehnt" if rejected else "angenommen",
                "bemerkung": "Kühlkette unterbrochen, zurückgegeben" if rejected else "",
            },
            stamp(day, 9),
        )

    for product, opened, deadline, done in [
        ("Milch", -4, -1, False),
        ("Sahne", -2, 0, False),
        ("Frischkäse", -1, 2, False),
        ("Apfelmus", 0, 3, False),
        ("Quark", -5, -2, True),
        ("Orangensaft", -4, -1, True),
    ]:
        day = anchor_date + timedelta(days=opened)
        create(
            "offene_produkte",
            {
                "produkt": product,
                "menge": "1 Packung",
                "geoeffnet_am": day,
                "verbrauchen_bis": anchor_date + timedelta(days=deadline),
                "erledigt": done,
            },
            stamp(day, 8),
        )
