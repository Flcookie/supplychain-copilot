from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException

from api.scenarios import DEMO_SCENARIOS
from api.schemas.chat import (
    AssessmentRequest,
    ChatRequest,
    ChatResponse,
    ResumeRequest,
    RouteInfo,
    ScenarioItem,
    ScenariosResponse,
    ThreadHistoryItem,
    ThreadHistoryResponse,
    ThreadStateResponse,
)
from api.services.copilot import (
    get_thread_history,
    get_thread_state,
    merge_clarification_reply,
    resume_thread,
    run_copilot,
    run_supplier_assessment,
)

router = APIRouter(prefix="/api", tags=["chat"])


def _to_chat_response(result: dict) -> ChatResponse:
    route_info = RouteInfo(**{k: v for k, v in result["route_info"].items() if k in RouteInfo.model_fields})
    return ChatResponse(
        answer=result["answer"],
        intent=result["intent"],
        route_info=route_info,
        evidence=result.get("evidence") or {},
        citations=result.get("citations") or [],
        sources=result.get("sources") or [],
        clarification_required=result.get("clarification_required", False),
        thread_id=result.get("thread_id"),
        review_status=result.get("review_status"),
        task_plan=result.get("task_plan"),
        supplier_id=result.get("supplier_id"),
        trace_id=result.get("trace_id"),
        cache_hit=bool(result.get("cache_hit")),
        paused=bool(result.get("paused")),
        interrupt=result.get("interrupt"),
        approval_decision=result.get("approval_decision"),
        proposed_action=result.get("proposed_action"),
    )


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    question = body.question.strip()
    if body.clarification_base_question:
        question = merge_clarification_reply(
            body.clarification_base_question, question, body.language
        )

    result = run_copilot(
        question,
        body.language,
        thread_id=body.thread_id,
        task_type=body.task_type,
        supplier_id=body.supplier_id,
    )
    return _to_chat_response(result)


@router.post("/assessment", response_model=ChatResponse)
def supplier_assessment(body: AssessmentRequest) -> ChatResponse:
    result = run_supplier_assessment(
        body.supplier_id,
        body.language,
        question=body.question,
        thread_id=body.thread_id,
    )
    return _to_chat_response(result)


@router.get("/threads/{thread_id}/history", response_model=ThreadHistoryResponse)
def thread_history(thread_id: str, limit: int = 20) -> ThreadHistoryResponse:
    items = [ThreadHistoryItem(**row) for row in get_thread_history(thread_id, limit=limit)]
    return ThreadHistoryResponse(thread_id=thread_id, items=items)


@router.get("/threads/{thread_id}", response_model=ThreadStateResponse)
def thread_state(thread_id: str) -> ThreadStateResponse:
    snap = get_thread_state(thread_id)
    return ThreadStateResponse(**snap)


@router.post("/threads/{thread_id}/resume", response_model=ChatResponse)
def thread_resume(thread_id: str, body: ResumeRequest) -> ChatResponse:
    try:
        result = resume_thread(
            thread_id,
            approved=body.approved,
            note=body.note,
            response_language=body.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_chat_response(result)


@router.get("/scenarios", response_model=ScenariosResponse)
def list_scenarios(lang: Literal["en", "zh"] = "en") -> ScenariosResponse:
    pairs = DEMO_SCENARIOS.get(lang, DEMO_SCENARIOS["en"])
    scenarios = [
        ScenarioItem(label=label, question=question)
        for label, question in pairs
        if question
    ]
    return ScenariosResponse(language=lang, scenarios=scenarios)
