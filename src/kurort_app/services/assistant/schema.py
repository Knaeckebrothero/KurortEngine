"""The action plan the assistant hands to the browser.

This is the contract between the planner (today: German phrase rules, later:
an LLM with tool calling) and the command bar in the page, which executes the
steps in order. The assistant never writes data itself: the last step of
anything that changes a record is ``confirm``, and a person presses save.
"""

from __future__ import annotations

from typing import Any, Literal

Intent = Literal[
    "walk_in",
    "check_in",
    "departures",
    "arrivals",
    "room_availability",
    "move_arrival",
    "dashboard",
    "search",
    "unknown",
]
HighlightTarget = Literal["room-row", "reservation-row", "widget"]
WIDGETS = ("metrics", "arrivals", "hints", "occupancy")
ENGINE = "demo-rules"


def navigate(label: str, url: str) -> dict[str, Any]:
    return {"type": "navigate", "label": label, "url": url}


def fill(label: str, fields: dict[str, str]) -> dict[str, Any]:
    return {"type": "fill", "label": label, "fields": fields}


def highlight(label: str, target: HighlightTarget, value: object) -> dict[str, Any]:
    return {"type": "highlight", "label": label, "target": target, "value": str(value)}


def dashboard(
    label: str, *, widgets: list[str] | None = None, occupancy_days: int | None = None
) -> dict[str, Any]:
    return {
        "type": "dashboard",
        "label": label,
        "config": {"widgets": widgets, "occupancy_days": occupancy_days},
    }


def dashboard_reset(label: str) -> dict[str, Any]:
    return {"type": "dashboard", "label": label, "reset": True}


def confirm(label: str) -> dict[str, Any]:
    return {"type": "confirm", "label": label}


def plan(
    intent: Intent,
    title: str,
    *,
    message: str | None = None,
    steps: list[dict[str, Any]] | None = None,
    suggestions: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "intent": intent,
        "title": title,
        "message": message,
        "steps": steps or [],
        "suggestions": suggestions or [],
        "engine": ENGINE,
    }
