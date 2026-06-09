from __future__ import annotations

from typing import Literal

from fastapi import APIRouter

from api.scenarios import DEMO_SCENARIOS
from api.schemas.chat import ChatRequest, ChatResponse, RouteInfo, ScenarioItem, ScenariosResponse
from api.services.copilot import merge_clarification_reply, run_copilot

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    question = body.question.strip()
    if body.clarification_base_question:
        question = merge_clarification_reply(
            body.clarification_base_question, question, body.language
        )

    result = run_copilot(question, body.language)
    route_info = RouteInfo(**result["route_info"])

    return ChatResponse(
        answer=result["answer"],
        intent=result["intent"],
        route_info=route_info,
        evidence=result.get("evidence") or {},
        citations=result.get("citations") or [],
        sources=result.get("sources") or [],
        clarification_required=result.get("clarification_required", False),
    )


@router.get("/scenarios", response_model=ScenariosResponse)
def list_scenarios(lang: Literal["en", "zh"] = "en") -> ScenariosResponse:
    pairs = DEMO_SCENARIOS.get(lang, DEMO_SCENARIOS["en"])
    scenarios = [
        ScenarioItem(label=label, question=question)
        for label, question in pairs
        if question
    ]
    return ScenariosResponse(language=lang, scenarios=scenarios)
