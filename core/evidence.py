from __future__ import annotations

from typing import Any, Literal, Optional
from typing_extensions import TypedDict


EvidenceType = Literal["document", "sql", "hybrid", "simulation"]


class SourceEvidence(TypedDict, total=False):
    source_id: str
    source_name: str
    section: str
    chunk_id: str
    doc_type: str
    retrieval_score: Optional[float]
    vector_score: Optional[float]
    keyword_score: Optional[float]
    rerank_score: Optional[float]
    content_preview: str


class SqlEvidence(TypedDict, total=False):
    query: str
    params: dict[str, Any]
    row_count: int
    latency_ms: Optional[float]
    metric: str
    metric_definition: str
    formula: str
    time_range: str
    data_snapshot: str
    sample_size: int
    minimum_sample_size: int
    is_sample_sufficient: bool


class Evidence(TypedDict, total=False):
    evidence_type: EvidenceType
    sources: list[SourceEvidence]
    sql: SqlEvidence
    assumptions: list[str]
    limitations: list[str]
    sample_size: Optional[int]
    is_sample_sufficient: Optional[bool]
    verified_facts: list[str]
    recommendations: list[str]
    retrieval_trace: list[dict[str, Any]]


def source_from_doc(doc: Any, position: int) -> SourceEvidence:
    metadata = getattr(doc, "metadata", {}) or {}
    source_name = (
        metadata.get("source_name")
        or metadata.get("source")
        or metadata.get("file_name")
        or "Policy Document"
    )
    chunk_id = metadata.get("chunk_id") or f"doc-{position}"
    return {
        "source_id": f"{source_name}#{chunk_id}",
        "source_name": source_name,
        "section": metadata.get("section_title") or metadata.get("section") or "",
        "chunk_id": chunk_id,
        "doc_type": metadata.get("doc_type", ""),
        "retrieval_score": metadata.get("retrieval_score"),
        "vector_score": metadata.get("vector_score"),
        "keyword_score": metadata.get("keyword_score"),
        "rerank_score": metadata.get("rerank_score"),
        "content_preview": getattr(doc, "page_content", "")[:300],
    }


def document_evidence(
    docs: list[Any],
    *,
    evidence_type: EvidenceType = "document",
    assumptions: list[str] | None = None,
    limitations: list[str] | None = None,
) -> Evidence:
    return {
        "evidence_type": evidence_type,
        "sources": [source_from_doc(doc, i) for i, doc in enumerate(docs, start=1)],
        "assumptions": assumptions or [],
        "limitations": limitations or [],
    }


def sql_evidence(
    *,
    query: str,
    row_count: int,
    latency_ms: Optional[float],
    metric: str,
    metric_definition: str,
    formula: str,
    time_range: str,
    data_snapshot: str,
    sample_size: int,
    minimum_sample_size: int,
    assumptions: list[str] | None = None,
    limitations: list[str] | None = None,
    params: dict[str, Any] | None = None,
) -> Evidence:
    is_sample_sufficient = sample_size >= minimum_sample_size
    return {
        "evidence_type": "sql",
        "sql": {
            "query": query,
            "params": params or {},
            "row_count": row_count,
            "latency_ms": latency_ms,
            "metric": metric,
            "metric_definition": metric_definition,
            "formula": formula,
            "time_range": time_range,
            "data_snapshot": data_snapshot,
            "sample_size": sample_size,
            "minimum_sample_size": minimum_sample_size,
            "is_sample_sufficient": is_sample_sufficient,
        },
        "sample_size": sample_size,
        "is_sample_sufficient": is_sample_sufficient,
        "assumptions": assumptions or [],
        "limitations": limitations or [],
    }


def hybrid_evidence(
    *,
    docs: list[Any],
    sql: SqlEvidence | None,
    sample_size: int | None,
    minimum_sample_size: int,
    assumptions: list[str] | None = None,
    limitations: list[str] | None = None,
) -> Evidence:
    """Evidence Contract for hybrid answers that combine policy docs and KPI SQL."""
    is_sufficient: Optional[bool]
    if sql is None or sample_size is None:
        is_sufficient = None
    else:
        is_sufficient = sample_size >= minimum_sample_size
    payload: Evidence = {
        "evidence_type": "hybrid",
        "sources": [source_from_doc(doc, i) for i, doc in enumerate(docs, start=1)],
        "assumptions": assumptions or [],
        "limitations": limitations or [],
        "sample_size": sample_size,
        "is_sample_sufficient": is_sufficient,
    }
    if sql is not None:
        payload["sql"] = sql
    return payload


def simulation_evidence(
    *,
    query: str,
    row_count: int,
    latency_ms: Optional[float],
    params: dict[str, Any],
    verified_facts: list[str],
    recommendations: list[str] | None = None,
    assumptions: list[str] | None = None,
    limitations: list[str] | None = None,
) -> Evidence:
    return {
        "evidence_type": "simulation",
        "sql": {
            "query": query,
            "params": params,
            "row_count": row_count,
            "latency_ms": latency_ms,
            "metric": "scenario_impact",
            "metric_definition": "Affected suppliers and order quantities for the selected disruption scope.",
            "formula": "COUNT(p.id), SUM(p.qty) grouped by affected supplier",
            "time_range": "current demo dataset",
            "data_snapshot": "demo SQLite supplychain_kpi.db",
            "sample_size": row_count,
            "minimum_sample_size": 1,
            "is_sample_sufficient": row_count >= 1,
        },
        "sample_size": row_count,
        "is_sample_sufficient": row_count >= 1,
        "verified_facts": verified_facts,
        "recommendations": recommendations or [],
        "assumptions": assumptions or [],
        "limitations": limitations or ["Scenario recommendations are model-generated and based on demo data."],
    }
