from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api.data import mock_data
from api.schemas.workbench import (
    DashboardSummary,
    PolicyDoc,
    PolicyListResponse,
    ReviewQueueItem,
    ReviewQueueResponse,
    SupplierDetail,
    SupplierListResponse,
    SupplierSummary,
)

router = APIRouter(prefix="/api/workbench", tags=["workbench"])


@router.get("/dashboard", response_model=DashboardSummary)
def get_dashboard() -> DashboardSummary:
    summary = dict(mock_data.DASHBOARD_SUMMARY)
    summary["risk_alerts"] = mock_data.RISK_ALERTS
    return DashboardSummary(**summary)


@router.get("/suppliers", response_model=SupplierListResponse)
def list_suppliers(
    category: str | None = Query(None),
    risk_level: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
) -> SupplierListResponse:
    rows = mock_data.filter_suppliers(
        category=category,
        risk_level=risk_level,
        status=status,
        search=search,
    )
    items = [SupplierSummary(**row) for row in rows]
    return SupplierListResponse(total=len(mock_data.SUPPLIERS), items=items)


@router.get("/suppliers/{supplier_id}", response_model=SupplierDetail)
def get_supplier(supplier_id: str) -> SupplierDetail:
    row = mock_data.get_supplier(supplier_id)
    if not row:
        raise HTTPException(status_code=404, detail="Supplier not found")
    trend = mock_data.KPI_TREND.get(supplier_id, {})
    return SupplierDetail(**row, kpi_trend=trend)


@router.get("/review-queue", response_model=ReviewQueueResponse)
def get_review_queue() -> ReviewQueueResponse:
    items: list[ReviewQueueItem] = []
    for task in mock_data.REVIEW_QUEUE:
        supplier = mock_data.get_supplier(task["supplier_id"]) or {}
        items.append(
            ReviewQueueItem(
                supplier_id=task["supplier_id"],
                supplier_name=supplier.get("name"),
                category=supplier.get("category"),
                country=supplier.get("country"),
                priority=task["priority"],
                reason=task["reason"],
                due_date=task["due_date"],
                status=task["status"],
            )
        )
    return ReviewQueueResponse(items=items)


@router.get("/policies", response_model=PolicyListResponse)
def list_policies() -> PolicyListResponse:
    items = [PolicyDoc(**doc) for doc in mock_data.POLICY_DOCS]
    return PolicyListResponse(items=items)
