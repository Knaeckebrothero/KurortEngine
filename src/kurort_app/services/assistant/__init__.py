"""The command-bar assistant: text in, action plan out (see ``schema``)."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from kurort_app.config import get_settings
from kurort_app.config import today as business_today
from kurort_app.services.assistant import planner
from kurort_app.services.assistant.planner import search, suggestions

__all__ = ["plan_for", "search", "suggestions"]

# Answered from the rules because Claude was configured but did not deliver.
RULES_FALLBACK = "rules-fallback"
# A bare name, code or room number: searched directly, Claude is not asked.
PLAIN_SEARCH = "plain-search"


def plan_for(session: Session, text: str, *, day: date | None = None) -> dict[str, Any]:
    """Plan with the configured engine; the phrase rules answer whenever Claude cannot."""
    day = day or business_today()
    if get_settings().assistant_engine != "claude" or not text.strip():
        return planner.plan_for(session, text, day=day)
    if planner.is_plain_search(session, text, day=day):
        result = planner.plan_for(session, text, day=day)
        result["engine"] = PLAIN_SEARCH
        return result
    from kurort_app.services.assistant import claude  # loads the Anthropic SDK only when used

    result = claude.plan(session, text, day=day)
    if result is not None:
        return result
    result = planner.plan_for(session, text, day=day)
    result["engine"] = RULES_FALLBACK
    return result
