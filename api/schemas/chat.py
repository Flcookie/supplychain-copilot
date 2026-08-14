from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    language: Literal["en", "zh"] = "en"
    clarification_base_question: str | None = None
    thread_id: str | None = None
    task_type: Literal["chat", "supplier_assessment"] | None = None
    supplier_id: str | None = None


class AssessmentRequest(BaseModel):
    supplier_id: str = Field(..., min_length=3, description="e.g. SUP012")
    language: Literal["en", "zh"] = "en"
    question: str | None = None
    thread_id: str | None = None


class RouteInfo(BaseModel):
    intent: str | None = None
    confidence: float | None = None
    ambiguity_type: str | None = None
    human_approval_required: bool | None = None
    reason: str | None = None
    fallback_mode: str | None = None
    kpi_parse: dict[str, Any] | None = None
    hybrid_parallel: bool | None = None
    injection_blocked: bool | None = None
    review_status: str | None = None
    review_notes: str | None = None
    task_type: str | None = None
    task_step: str | None = None
    supplier_id: str | None = None
    review_attempts: int | None = None


class ChatResponse(BaseModel):
    answer: str
    intent: str
    route_info: RouteInfo
    evidence: dict[str, Any] = Field(default_factory=dict)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    clarification_required: bool = False
    thread_id: str | None = None
    review_status: str | None = None
    task_plan: list[str] | None = None
    supplier_id: str | None = None
    trace_id: str | None = None
    cache_hit: bool = False


class ScenarioItem(BaseModel):
    label: str
    question: str


class ScenariosResponse(BaseModel):
    language: str
    scenarios: list[ScenarioItem]


class ThreadHistoryItem(BaseModel):
    thread_id: str
    checkpoint_id: str | None = None
    next: list[str] = Field(default_factory=list)
    created_at: str = ""
    intent: str | None = None
    task_step: str | None = None
    review_status: str | None = None
    supplier_id: str | None = None
    answer_preview: str = ""
    question: str | None = None


class ThreadHistoryResponse(BaseModel):
    thread_id: str
    items: list[ThreadHistoryItem]


class ThreadStateResponse(BaseModel):
    thread_id: str
    checkpoint_id: str | None = None
    next: list[str] = Field(default_factory=list)
    values: dict[str, Any] = Field(default_factory=dict)
