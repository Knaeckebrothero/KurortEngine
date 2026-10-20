"""Command bar on Claude: tool calls become the rules' plans; any failure falls back to the rules.

Claude is replaced by a fake client that returns a scripted response, so these
tests check the wiring, not the model's judgement. Tests that need no guests run
on the empty ``db``: seeding costs seconds per test.
"""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

import anthropic
import httpx2
import pytest
from sqlalchemy import select

from kurort_app.models import RESERVED, Reservation, Room
from kurort_app.services.assistant import claude, planner
from kurort_app.services.availability import free_rooms
from tests.app.conftest import BUSINESS_DATE

D = BUSINESS_DATE  # Wednesday 14.10.2026


class FakeClaude:
    """Stands in for ``anthropic.Anthropic``: records the request, returns ``response``."""

    def __init__(self, response=None, error: Exception | None = None):
        self.response, self.error, self.calls = response, error, []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def tool_call(name: str, **args) -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason="tool_use",
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="tool_use", id="toolu_1", name=name, input=args),
        ],
    )


def reply(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason="end_turn", content=[SimpleNamespace(type="text", text=text)]
    )


@pytest.fixture
def engine(monkeypatch):
    """Switch the command bar to Claude; ``engine(response)`` scripts the next answer."""
    from kurort_app.config import get_settings

    monkeypatch.setenv("KURORT_ASSISTANT_ENGINE", "claude")
    get_settings.cache_clear()

    def script(response=None, *, error=None, client="fake"):
        fake = FakeClaude(response, error)
        monkeypatch.setattr(claude, "_client", lambda timeout: fake if client == "fake" else None)
        return fake

    yield script
    get_settings.cache_clear()


def ask(client, text: str) -> dict:
    response = client.post("/assistent/plan", json={"text": text, "path": "/"})
    assert response.status_code == 200, response.text
    return response.json()


def _arrivals(session) -> list[Reservation]:
    return list(
        session.scalars(
            select(Reservation)
            .where(Reservation.arrival == D, Reservation.status == RESERVED)
            .order_by(Reservation.id)
        )
    )


def _primary(res: Reservation):
    return next(rg.guest for rg in res.guests if rg.is_primary)


def test_a_tool_call_gives_the_same_plan_as_the_rules(client, seeded, engine):
    arrivals = _arrivals(seeded)
    last_names = [_primary(r).last_name for r in arrivals]
    target = next(r for r in arrivals if last_names.count(_primary(r).last_name) == 1)
    said = f"Frau {_primary(target).last_name}"
    engine(tool_call("check_in", guest=said))

    plan = ask(client, f"bitte die {said} einchecken, die ist gerade gekommen")

    assert plan["engine"] == "claude"
    assert plan["steps"] == [
        {
            "type": "navigate",
            "label": f"Check-in für {_primary(target).full_name} öffnen",
            "url": f"/check-in/{target.id}",
        }
    ]
    rules = planner.plan_for(seeded, f"Check-in für {said}", day=D)
    assert {**plan, "engine": rules["engine"]} == rules


def test_the_request_names_today_and_offers_strict_tools(client, db, engine):
    fake = engine(tool_call("departures"))
    ask(client, "Wer muss heute noch raus?")

    (call,) = fake.calls
    assert call["model"] == "claude-opus-5-5"
    assert "tool_choice" not in call  # forced tool use is a 400 on Opus 5.5
    assert call["output_config"] == {"effort": "low"}
    assert call["fallbacks"] == "default"
    assert call["messages"] == [
        {
            "role": "user",
            "content": "Heute ist Mittwoch, 2026-10-14.\n\nAnfrage: Wer muss heute noch raus?",
        }
    ]
    names = [tool["name"] for tool in call["tools"]]
    assert names == [
        "walk_in", "check_in", "move_arrival", "room_availability",
        "arrivals", "departures", "dashboard", "search",
    ]  # fmt: skip
    for tool in call["tools"]:
        schema = tool["input_schema"]
        assert tool["strict"] is True and schema["additionalProperties"] is False
        assert set(schema["required"]) <= set(schema["properties"])


def test_walk_in_fields_fill_the_form(client, seeded, engine):
    engine(
        tool_call(
            "walk_in", nights=2, category="Doppelzimmer", first_name="Klaus", last_name="Becker"
        )
    )
    plan = ask(client, "Herr Becker steht hier, braucht ein DZ für zwei Nächte")

    assert plan["intent"] == "walk_in" and plan["engine"] == "claude"
    url = plan["steps"][0]["url"]
    assert url.startswith("/reservierungen/neu?walkin=1&abreise=2026-10-16&zimmer=")
    room = seeded.scalar(select(Room).where(Room.number == url.rsplit("=", 1)[1]))
    assert room.category == "Doppelzimmer"
    assert room in free_rooms(seeded, D, D + timedelta(days=2))
    assert plan["steps"][1]["fields"] == {"vorname": "Klaus", "nachname": "Becker"}
    assert plan["steps"][-1]["type"] == "confirm"


def test_move_arrival_takes_an_iso_date_and_asks_without_one(client, seeded, engine):
    res = next(
        r
        for r in seeded.scalars(
            select(Reservation)
            .where(Reservation.arrival > D + timedelta(days=2), Reservation.status == RESERVED)
            .order_by(Reservation.arrival, Reservation.id)
        )
    )
    guest = _primary(res)
    guest.first_name, guest.last_name = "Paul", "Zander"
    seeded.commit()

    engine(tool_call("move_arrival", guest="Paul Zander", new_arrival="2026-10-16"))
    plan = ask(client, "Herr Zander kommt schon am Freitag")
    assert plan["steps"][0]["url"] == f"/reservierungen/{res.id}/bearbeiten"
    assert plan["steps"][1]["fields"] == {
        "anreise": "2026-10-16",
        "abreise": (D + timedelta(days=2 + res.nights)).isoformat(),
    }

    engine(tool_call("move_arrival", guest="Paul Zander", new_arrival="Freitag"))
    plan = ask(client, "Herr Zander kommt später")
    assert plan["message"] == "Auf welchen Tag soll die Anreise verschoben werden?"


def test_room_availability_and_dashboard(client, seeded, engine):
    engine(tool_call("room_availability", room="Zimmer 204", first_night="2026-10-16"))
    plan = ask(client, "Ist die 204 am Freitag noch zu haben?")
    assert plan["intent"] == "room_availability"
    assert plan["steps"][0]["url"] == "/zimmerplan?von=2026-10-15"
    assert plan["steps"][1] == {
        "type": "highlight",
        "label": "Zimmer 204 markieren",
        "target": "room-row",
        "value": "204",
    }

    engine(tool_call("dashboard", show=["occupancy", "today"], occupancy_days=30))
    plan = ask(client, "Startseite nur mit Heute-Tabelle und Belegung für einen Monat")
    assert plan["steps"][0]["config"] == {"widgets": ["today", "occupancy"], "occupancy_days": 30}
    assert plan["message"] == "Angezeigt: Heute, Belegung · Belegung für 30 Tage"

    engine(tool_call("dashboard", reset=True))
    assert ask(client, "Startseite wie vorher")["steps"][0]["reset"] is True


def test_a_text_answer_is_shown_with_examples(client, db, engine):
    engine(reply("Für welchen Gast soll ich die Rechnung erstellen?"))
    plan = ask(client, "Mach mal die Rechnung fertig")
    assert plan["intent"] == "unknown" and plan["engine"] == "claude"
    assert plan["message"] == "Für welchen Gast soll ich die Rechnung erstellen?"
    assert plan["suggestions"]


REQUEST = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


@pytest.mark.parametrize(
    "setup",
    [
        pytest.param({"error": anthropic.APIConnectionError(request=REQUEST)}, id="unreachable"),
        pytest.param({"error": anthropic.APITimeoutError(request=REQUEST)}, id="timeout"),
        pytest.param(
            {
                "error": anthropic.APIStatusError(
                    "overloaded", response=httpx2.Response(529, request=REQUEST), body=None
                )
            },
            id="api-error",
        ),
        pytest.param(
            {"response": SimpleNamespace(stop_reason="refusal", content=[])}, id="refusal"
        ),
        pytest.param({"response": tool_call("send_invoice", guest="x")}, id="unknown-tool"),
        pytest.param({"response": tool_call("search", term="  ")}, id="empty-term"),
        pytest.param({"response": reply("")}, id="empty-answer"),
        pytest.param({"client": None}, id="no-key"),
    ],
)
def test_the_rules_answer_when_claude_does_not(client, db, engine, setup):
    engine(**setup)
    plan = ask(client, "Wer reist heute noch ab?")
    assert plan["engine"] == "rules-fallback"
    assert plan["intent"] == "departures"


def test_the_rules_engine_never_calls_claude(client, db, monkeypatch):
    def no_claude(timeout):
        raise AssertionError("Claude was called with KURORT_ASSISTANT_ENGINE=rules")

    monkeypatch.setattr(claude, "_client", no_claude)
    plan = ask(client, "Wer reist heute noch ab?")
    assert plan["engine"] == "demo-rules"


def test_an_empty_request_shows_examples_without_calling_claude(client, db, engine):
    fake = engine(tool_call("departures"))
    plan = ask(client, "  ")
    assert plan["title"] == "Was möchten Sie tun?" and plan["suggestions"]
    assert not fake.calls
