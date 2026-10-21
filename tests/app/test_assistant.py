"""Command-bar assistant: German parsing, demo plans on seeded data, endpoints."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from kurort_app.main import create_app
from kurort_app.models import CHECKED_IN, RESERVED, Guest, Reservation, Room
from kurort_app.services.assistant import parsing as p
from kurort_app.services.assistant.planner import NOT_YET
from kurort_app.services.availability import blocking_reservations, free_rooms
from tests.app.auth_helpers import FakeIdP, login, oidc_settings
from tests.app.conftest import BUSINESS_DATE

D = BUSINESS_DATE  # Wednesday 14.10.2026
FRIDAY = date(2026, 10, 16)


def ask(client, text: str) -> dict:
    response = client.post("/assistent/plan", json={"text": text, "path": "/"})
    assert response.status_code == 200, response.text
    plan = response.json()
    assert plan["engine"] == "demo-rules"
    return plan


def steps_of(plan: dict, kind: str) -> list[dict]:
    return [step for step in plan["steps"] if step["type"] == kind]


def query_of(url: str) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}


def primary(res: Reservation) -> Guest:
    return next(rg.guest for rg in res.guests if rg.is_primary)


# ---------------------------------------------------------------------------
# Parsing (pure)
# ---------------------------------------------------------------------------


def test_fold_spells_out_umlauts():
    assert p.fold("  Übermorgen   STRASSE Größe ") == "uebermorgen strasse groesse"


@pytest.mark.parametrize(
    ("text", "nights"),
    [
        ("zwei naechte", 2),
        ("1 nacht", 1),
        ("3 uebernachtungen", 3),
        ("eine woche", 7),
        ("zwei wochen", 14),
        ("doppelzimmer bitte", None),
    ],
)
def test_parse_nights(text, nights):
    assert p.parse_nights(text) == nights


@pytest.mark.parametrize(
    ("text", "days"),
    [("30 tage", 30), ("fuer 14 tagen", 14), ("zwei wochen", 14), ("einen monat", 30), ("x", None)],
)
def test_parse_days(text, days):
    assert p.parse_days(text) == days


@pytest.mark.parametrize(
    ("text", "category"),
    [
        ("ein dz", "Doppelzimmer"),
        ("doppelzimmer", "Doppelzimmer"),
        ("komfort-doppelzimmer", "Komfort-Doppelzimmer"),
        ("einzelzimmer", "Einzelzimmer"),
        ("ez", "Einzelzimmer"),
        ("die suite", "Suite"),
        ("irgendwas", None),
    ],
)
def test_parse_category(text, category):
    assert p.parse_category(text) == category


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("heute", date(2026, 10, 14)),
        ("morgen", date(2026, 10, 15)),
        ("uebermorgen", date(2026, 10, 16)),
        ("am freitag", date(2026, 10, 16)),
        ("am mittwoch", date(2026, 10, 14)),  # today counts
        ("sonntag", date(2026, 10, 18)),
        ("am 23.10.", date(2026, 10, 23)),
        ("am 23.10.2027", date(2027, 10, 23)),
        ("am 1.1.", date(2027, 1, 1)),  # long past this year → next year
        ("am 10.10.", date(2026, 10, 10)),  # a few days back stays this year
        ("31.02.", None),
        ("irgendwann", None),
    ],
)
def test_parse_single_date(text, expected):
    assert p.parse_single_date(text, D) == expected


def test_parse_span_variants():
    assert p.parse_span("am wochenende", D) == (date(2026, 10, 17), date(2026, 10, 19))
    assert p.parse_span("am wochenende", date(2026, 10, 18)) == (
        date(2026, 10, 18),
        date(2026, 10, 19),
    )
    assert p.parse_span("vom 20.10. bis 23.10.", D) == (date(2026, 10, 20), date(2026, 10, 23))
    assert p.parse_span("morgen", D) == (date(2026, 10, 15), date(2026, 10, 16))
    assert p.parse_span("nichts", D) is None


def test_parse_target_date_prefers_what_follows_auf():
    assert p.parse_target_date("verschieb die anreise von heute auf freitag", D) == FRIDAY
    assert p.parse_target_date("anreise auf den 23.10. legen", D) == date(2026, 10, 23)


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ("Walk-in: Herr Klaus Becker, zwei Nächte, Doppelzimmer", ("Klaus", "Becker")),
        ("walk-in für herrn klaus becker zwei nächte", ("Klaus", "Becker")),
        ("Walk-in für Familie Becker, eine Woche", (None, "Becker")),
        ("Walk-in für Frau Müller-Lüdenscheidt 1 Nacht", (None, "Müller-Lüdenscheidt")),
        ("Walk-in für Klaus Becker", ("Klaus", "Becker")),
        ("Walk-in zwei Nächte", None),
    ],
)
def test_extract_new_guest_name(text, name):
    assert p.extract_new_guest_name(text) == name


def test_name_score():
    text = p.fold("Check-in für Frau Anja König")
    assert p.name_score(text, "Anja", "König") == 2
    assert p.name_score(text, "Heinz", "König") == 1
    assert p.name_score(text, "Anja", "Kö") == 0
    assert p.name_score(p.fold("frau koenigsberg"), "Anja", "König") == 0


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------


def test_walk_in_opens_prefilled_form_with_a_free_room(client, seeded):
    plan = ask(client, "Walk-in: Herr Klaus Becker, zwei Nächte, Doppelzimmer")
    assert plan["intent"] == "walk_in"
    nav = steps_of(plan, "navigate")[0]
    query = query_of(nav["url"])
    assert nav["url"].startswith("/reservierungen/neu?")
    assert query["walkin"] == "1"
    assert query["abreise"] == "2026-10-16"
    room = seeded.scalar(select(Room).where(Room.number == query["zimmer"]))
    assert room.category == "Doppelzimmer"
    assert room in free_rooms(seeded, D, D + timedelta(days=2))
    assert steps_of(plan, "fill")[0]["fields"] == {"vorname": "Klaus", "nachname": "Becker"}
    assert plan["steps"][-1]["type"] == "confirm"
    assert room.number in plan["message"]
    assert "258,00 €" in plan["message"]


def test_walk_in_reports_when_the_category_is_full(client, seeded):
    for suite in seeded.scalars(select(Room).where(Room.category == "Suite")):
        seeded.add(
            Reservation(
                code=f"R-TEST-{suite.number}",
                room=suite,
                arrival=D,
                departure=D + timedelta(days=7),
                status=RESERVED,
                rate_total=Decimal("0"),
            )
        )
    seeded.commit()
    plan = ask(client, "Walk-in für Familie Becker, eine Woche, Suite")
    assert plan["intent"] == "walk_in"
    assert plan["steps"] == []
    assert plan["message"].startswith("Keine Suite frei")


def _arrivals(session) -> list[Reservation]:
    return list(
        session.scalars(
            select(Reservation)
            .where(Reservation.arrival == D, Reservation.status == RESERVED)
            .order_by(Reservation.id)
        )
    )


def test_check_in_by_last_name_opens_the_flow(client, seeded):
    arrivals = _arrivals(seeded)
    last_names = [primary(r).last_name for r in arrivals]
    target = next(r for r in arrivals if last_names.count(primary(r).last_name) == 1)
    plan = ask(client, f"Check-in für Frau {primary(target).last_name}")
    assert plan["intent"] == "check_in"
    assert plan["steps"] == [
        {
            "type": "navigate",
            "label": f"Check-in für {primary(target).full_name} öffnen",
            "url": f"/check-in/{target.id}",
        }
    ]
    assert target.code in plan["message"]


def test_check_in_with_two_matching_arrivals_asks_which(client, seeded):
    first, second = _arrivals(seeded)[:2]
    primary(first).last_name = "Zander"
    primary(second).last_name = "Zander"
    seeded.commit()
    plan = ask(client, "Check-in für Familie Zander")
    assert plan["message"].startswith("Mehrere Anreisen passen")
    assert steps_of(plan, "navigate")[0]["url"] == "/anreisen?filter=offen"
    assert {s["value"] for s in steps_of(plan, "highlight")} == {str(first.id), str(second.id)}
    assert {s["target"] for s in steps_of(plan, "highlight")} == {"reservation-row"}


def test_check_in_without_match_offers_a_search(client, seeded):
    plan = ask(client, "Check-in für Frau Nirgendwo")
    assert plan["message"] == "Keine offene Anreise heute für Nirgendwo."
    assert steps_of(plan, "navigate")[0]["url"] == "/reservierungen?q=Nirgendwo"


def test_departures_lists_open_check_outs(client, seeded):
    open_departures = list(
        seeded.scalars(
            select(Reservation).where(Reservation.departure == D, Reservation.status == CHECKED_IN)
        )
    )
    plan = ask(client, "Wer reist heute noch ab?")
    assert plan["intent"] == "departures"
    assert steps_of(plan, "navigate")[0]["url"] == "/abreisen"
    assert plan["message"].startswith(f"{len(open_departures)} Abreise")
    for res in open_departures:
        assert f"{res.room.number} {primary(res).last_name}" in plan["message"]


def test_arrivals_lists_open_arrivals(client, seeded):
    plan = ask(client, "Wer kommt heute noch?")
    assert plan["intent"] == "arrivals"
    assert steps_of(plan, "navigate")[0]["url"] == "/anreisen?filter=offen"
    for res in _arrivals(seeded):
        assert primary(res).full_name in plan["message"]


def test_room_availability_free_and_occupied(client, seeded):
    sat, mon = date(2026, 10, 17), date(2026, 10, 19)
    free = free_rooms(seeded, sat, mon)[0]
    plan = ask(client, f"Ist Zimmer {free.number} am Wochenende frei?")
    assert plan["intent"] == "room_availability"
    assert plan["message"] == f"Zimmer {free.number} ist Sa 17.10.–Mo 19.10. frei."
    assert steps_of(plan, "navigate")[0]["url"] == "/zimmerplan?von=2026-10-16"
    assert steps_of(plan, "highlight")[0] == {
        "type": "highlight",
        "label": f"Zimmer {free.number} markieren",
        "target": "room-row",
        "value": free.number,
    }

    blocker = seeded.scalars(blocking_reservations(sat, mon)).first()
    plan = ask(client, f"Ist Zimmer {blocker.room.number} am Wochenende frei?")
    assert "belegt" in plan["message"]
    assert blocker.code in plan["message"]


def test_room_availability_unknown_room(client, seeded):
    plan = ask(client, "Ist Zimmer 999 morgen frei?")
    assert plan["message"] == "Zimmer 999 gibt es nicht."
    assert plan["steps"] == []


def _upcoming(session) -> list[Reservation]:
    return list(
        session.scalars(
            select(Reservation)
            .where(Reservation.arrival > D, Reservation.status == RESERVED)
            .order_by(Reservation.arrival, Reservation.id)
        )
    )


def _rename(res: Reservation, first: str, last: str) -> None:
    primary(res).first_name, primary(res).last_name = first, last


def test_move_arrival_fills_the_edit_form(client, seeded):
    res = next(r for r in _upcoming(seeded) if r.arrival > FRIDAY)
    _rename(res, "Paul", "Zander")
    seeded.commit()
    nights = res.nights
    plan = ask(client, "Verschieb die Anreise von Paul Zander auf Freitag")
    assert plan["intent"] == "move_arrival"
    assert [s["type"] for s in plan["steps"]] == ["navigate", "fill", "confirm"]
    assert plan["steps"][0]["url"] == f"/reservierungen/{res.id}/bearbeiten"
    assert plan["steps"][1]["fields"] == {
        "anreise": "2026-10-16",
        "abreise": (FRIDAY + timedelta(days=nights)).isoformat(),
    }
    assert res.code in plan["message"]
    assert "Fr 16.10." in plan["message"]
    assert f"Zimmer {res.room.number} ist dann" in plan["message"]


def test_move_arrival_warns_when_the_room_is_taken(client, seeded):
    res = next(r for r in _upcoming(seeded) if r.arrival > FRIDAY + timedelta(days=3))
    _rename(res, "Paul", "Zander")
    seeded.add(
        Reservation(
            code="R-TEST-BLOCK",
            room_id=res.room_id,
            arrival=FRIDAY,
            departure=FRIDAY + timedelta(days=1),
            status=RESERVED,
            rate_total=Decimal("0"),
        )
    )
    seeded.commit()
    plan = ask(client, "Verschieb die Anreise von Paul Zander auf Freitag")
    assert f"Zimmer {res.room.number} ist dann belegt" in plan["message"]


def test_move_arrival_ambiguous_and_unknown(client, seeded):
    a, b = [r for r in _upcoming(seeded) if r.arrival != FRIDAY][:2]
    _rename(a, "Paul", "Zander")
    _rename(b, "Petra", "Zander")
    seeded.commit()
    plan = ask(client, "Verschieb die Anreise von Herrn Zander auf Freitag")
    assert plan["message"].startswith("Mehrere Gäste passen")
    assert a.code in plan["message"] and b.code in plan["message"]
    assert plan["steps"] == []
    # each guest is a button that runs the move for just that guest
    assert plan["suggestions"] == [
        f"Verschiebe die Anreise von {primary(r).full_name} auf 16.10." for r in (a, b)
    ]
    chosen = ask(client, plan["suggestions"][1])
    assert chosen["steps"][0]["url"] == f"/reservierungen/{b.id}/bearbeiten"
    assert chosen["steps"][1]["fields"]["anreise"] == "2026-10-16"

    plan = ask(client, "Verschieb die Anreise von Herrn Niemand auf Freitag")
    assert plan["message"] == "Keine kommende Reservierung für Niemand gefunden."


def test_move_arrival_skips_the_stay_that_already_arrives_that_day(client, seeded):
    upcoming = _upcoming(seeded)
    on_friday = next(r for r in upcoming if r.arrival == FRIDAY)
    later = next(r for r in upcoming if r.arrival > FRIDAY)
    _rename(on_friday, "Christa", "Zander")
    _rename(later, "Anja", "Zander")
    seeded.commit()
    plan = ask(client, "Verschiebe die Anreise von Frau Zander auf Freitag")
    assert plan["suggestions"] == []
    assert plan["steps"][0]["url"] == f"/reservierungen/{later.id}/bearbeiten"
    assert on_friday.code not in plan["message"]


@pytest.mark.parametrize(
    ("text", "config", "url"),
    [
        (
            "Zeig mir nur Anreisen und Belegung, 30 Tage",
            {"widgets": ["today", "occupancy"], "occupancy_days": 30},
            "/?zeigen=anreisen",  # the Heute table shows arrivals too
        ),
        (
            "Blende Heute aus",
            {"widgets": ["metrics", "occupancy"], "occupancy_days": None},
            "/",
        ),
        (
            "Blende die Kennzahlen aus",
            {"widgets": ["today", "occupancy"], "occupancy_days": None},
            "/",
        ),
        ("Belegung für 30 Tage", {"widgets": None, "occupancy_days": 30}, "/"),
        ("Belegung für 100 Tage", {"widgets": None, "occupancy_days": 60}, "/"),
        (
            "Übersicht: nur Kennzahlen, Belegung 3 Tage",
            {"widgets": ["metrics", "occupancy"], "occupancy_days": 7},
            "/",
        ),
        (
            "Übersicht nur Abreisen",
            {"widgets": ["today"], "occupancy_days": None},
            "/?zeigen=abreisen",
        ),
        (
            "Blende die Anreisen aus",
            {"widgets": ["metrics", "occupancy"], "occupancy_days": None},
            "/",
        ),
    ],
)
def test_dashboard_configuration(client, seeded, text, config, url):
    plan = ask(client, text)
    assert "hints" not in str(plan)
    assert plan["intent"] == "dashboard"
    assert plan["steps"][0] == {"type": "dashboard", "label": "Ansicht speichern", "config": config}
    assert plan["steps"][1]["url"] == url


def test_dashboard_arrivals_only_says_so(client, seeded):
    plan = ask(client, "Zeig mir nur Anreisen und Belegung, 30 Tage")
    assert plan["message"] == (
        "Angezeigt: Heute, Belegung · Heute nur Anreisen · Belegung für 30 Tage"
    )


def test_dashboard_reset(client, seeded):
    plan = ask(client, "Übersicht zurücksetzen")
    assert plan["steps"][0]["reset"] is True
    assert plan["steps"][1]["url"] == "/"


@pytest.mark.parametrize(
    ("text", "q"),
    [("Müller", "Müller"), ("R-2610-0094", "R-2610-0094"), ("Frau König", "König"), ("204", "204")],
)
def test_plain_names_codes_and_rooms_search(client, seeded, text, q):
    plan = ask(client, text)
    assert plan["intent"] == "search"
    url = steps_of(plan, "navigate")[0]["url"]
    assert url.startswith("/reservierungen?")
    assert query_of(url)["q"] == q


def test_an_invoice_request_says_it_is_not_there_yet(client, seeded):
    plan = ask(client, "Rechnung für Zimmer 110")
    assert plan["intent"] == "search"
    assert plan["message"] == (
        "Rechnungen kann ich noch nicht – hier die Aufenthalte von Zimmer 110."
    )
    assert query_of(steps_of(plan, "navigate")[0]["url"])["q"] == "110"

    plan = ask(client, "Rechnung für Herrn Klaus Becker")
    assert plan["message"] == (
        "Rechnungen kann ich noch nicht – hier die Aufenthalte von Klaus Becker."
    )

    plan = ask(client, "Mach mal die Rechnung fertig")
    assert plan["intent"] == "unknown"
    assert plan["message"] == "Rechnungen kann ich noch nicht."
    assert plan["suggestions"]


def test_unknown_request_offers_examples(client, seeded):
    plan = ask(client, "Mach mir bitte einen Kaffee mit Milch")
    assert plan["intent"] == "unknown"
    assert plan["message"] == NOT_YET
    assert len(plan["suggestions"]) == 6
    assert plan["steps"] == []


# ---------------------------------------------------------------------------
# Search and suggestions endpoints
# ---------------------------------------------------------------------------


def test_quick_search_matches_like_the_list(client, seeded):
    rows = client.get("/assistent/suche", params={"q": "König"}).json()["results"]
    assert 0 < len(rows) <= 6
    assert any("König" in row["label"] for row in rows)
    assert all(row["url"].startswith("/reservierungen/") for row in rows)
    assert {"label", "sub", "status", "url"} == set(rows[0])
    # current and upcoming stays come first
    first = seeded.get(Reservation, int(rows[0]["url"].rsplit("/", 1)[1]))
    assert first.departure >= D
    assert client.get("/assistent/suche", params={"q": "  "}).json() == {"results": []}


def test_quick_search_by_room_and_code(client, seeded):
    res = _arrivals(seeded)[0]
    by_code = client.get("/assistent/suche", params={"q": res.code}).json()["results"]
    assert by_code[0]["url"] == f"/reservierungen/{res.id}"
    by_room = client.get("/assistent/suche", params={"q": res.room.number}).json()["results"]
    assert any(row["url"] == f"/reservierungen/{res.id}" for row in by_room)


def test_every_suggestion_works(client, seeded):
    suggestions = client.get("/assistent/vorschlaege").json()["suggestions"]
    assert len(suggestions) == 6
    intents = [ask(client, text)["intent"] for text in suggestions]
    assert intents == [
        "walk_in",
        "check_in",
        "departures",
        "room_availability",
        "move_arrival",
        "dashboard",
    ]
    for text in suggestions:
        assert ask(client, text)["steps"], text  # each one actually does something


# ---------------------------------------------------------------------------
# Login: fetch() gets JSON, not a redirect to Keycloak
# ---------------------------------------------------------------------------


@pytest.fixture
def oidc_app_client(db):
    app = create_app(oidc_settings())
    app.state.oidc = FakeIdP()
    with TestClient(app) as client:
        yield client


def test_assistant_without_session_gets_json_401(oidc_app_client):
    response = oidc_app_client.post(
        "/assistent/plan",
        json={"text": "Wer kommt heute noch?"},
        headers={"Referer": "http://testserver/anreisen?filter=offen"},
        follow_redirects=False,
    )
    assert response.status_code == 401
    assert response.json() == {
        "error": "login_required",
        "login": "/auth/login?next=%2Fanreisen%3Ffilter%3Doffen",
    }


def test_json_accept_gets_401_but_pages_still_redirect(oidc_app_client):
    api = oidc_app_client.get(
        "/reservierungen", headers={"Accept": "application/json"}, follow_redirects=False
    )
    assert api.status_code == 401
    assert api.json()["login"] == "/auth/login?next=%2F"
    page = oidc_app_client.get("/reservierungen", follow_redirects=False)
    assert page.status_code == 303


def test_assistant_after_login_answers(oidc_app_client, seeded):
    login(oidc_app_client)
    plan = oidc_app_client.post("/assistent/plan", json={"text": "Wer kommt heute noch?"}).json()
    assert plan["intent"] == "arrivals"


def test_assistant_for_user_without_role_is_json_403(oidc_app_client):
    idp = oidc_app_client.app.state.oidc
    idp.claims["roles"] = ["offline_access"]
    login(oidc_app_client)
    response = oidc_app_client.get("/assistent/vorschlaege")
    assert response.status_code == 403
    assert response.json() == {"error": "forbidden"}
