from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    language: Literal["en", "zh"] = "en"
    clarification_base_question: str | None = None


class RouteInfo(BaseModel):
    intent: str | None = None
    confidence: float | None = None
    ambiguity_type: str | None = None
    human_approval_required: bool | None = None
    reason: str | None = None
    fallback_mode: str | None = None
    kpi_parse: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    answer: str
    intent: str
    route_info: RouteInfo
    evidence: dict[str, Any] = Field(default_factory=dict)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    clarification_required: bool = False


class ScenarioItem(BaseModel):
    label: str
    question: str


class ScenariosResponse(BaseModel):
    language: str
    scenarios: list[ScenarioItem]
