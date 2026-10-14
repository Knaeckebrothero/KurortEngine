"""JSON endpoints behind the command bar: plan, quick search, suggestions."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from kurort_app.db import get_session
from kurort_app.services import assistant

router = APIRouter(prefix="/assistent", tags=["assistent"])


class PlanRequest(BaseModel):
    text: str = ""
    path: str = "/"


@router.post("/plan")
def plan(body: PlanRequest, session: Session = Depends(get_session)) -> dict[str, Any]:
    """Turn a typed or spoken request into steps for the page to carry out."""
    return assistant.plan_for(session, body.text[:500])


@router.get("/suche")
def quick_search(q: str = "", session: Session = Depends(get_session)) -> dict[str, Any]:
    return {"results": assistant.search(session, q[:100])}


@router.get("/vorschlaege")
def example_commands(session: Session = Depends(get_session)) -> dict[str, Any]:
    return {"suggestions": assistant.suggestions(session)}
