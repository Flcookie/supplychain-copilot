from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DashboardSummary(BaseModel):
    active_suppliers: int
    at_risk_suppliers: int
    reviews_due_this_month: int
    open_qualifications: int
    greeting: str
    period_label: str
    yarn_kpi_snapshot: dict[str, float]
    risk_alerts: list[dict[str, Any]]


class SupplierSummary(BaseModel):
    id: str
    name: str
    category: str
    country: str
    rating: str
    otd_rate: float
    defect_rate: float
    risk_level: str
    status: str
    contract_expiry: str
    last_review: str


class SupplierDetail(SupplierSummary):
    kpi_trend: dict[str, Any] = Field(default_factory=dict)


class SupplierListResponse(BaseModel):
    total: int
    items: list[SupplierSummary]


class ReviewQueueItem(BaseModel):
    supplier_id: str
    supplier_name: str | None = None
    category: str | None = None
    country: str | None = None
    priority: str
    reason: str
    due_date: str
    status: str


class ReviewQueueResponse(BaseModel):
    items: list[ReviewQueueItem]
    completed_count: int = 11


class PolicyDoc(BaseModel):
    id: str
    title: str
    category: str
    last_updated: str
    scope: str
    quick_question: str


class PolicyListResponse(BaseModel):
    items: list[PolicyDoc]
