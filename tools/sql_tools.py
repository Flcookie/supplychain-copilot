import os
import re
import sqlite3
import time
from typing import Any, Dict, List

from core.config import SQLITE_DB_PATH

# Ratti demo schema: analytical tables only (policies_knowledge_base is RAG-only).
ALLOWED_SQL_TABLES = frozenset(
    {
        "suppliers",
        "category_rules",
        "documents",
        "purchase_orders",
        "delivery_events",
        "quality_events",
        "risk_events",
        "esg_assessments",
        "vendor_rating",
    }
)

DEFAULT_QUERY_LIMIT = 100


def _tables_referenced_in_sql(sql: str) -> List[str]:
    """Bare table names after FROM / JOIN (PoC SQLite; no schema qualifiers)."""
    pat = re.compile(r"(?is)\b(?:from|join)\s+([a-z_][a-z0-9_]*)")
    return pat.findall(sql)


def _validate_table_whitelist(sql: str) -> None:
    tables = [t.lower() for t in _tables_referenced_in_sql(sql)]
    invalid = [t for t in tables if t not in ALLOWED_SQL_TABLES]
    if invalid:
        raise ValueError(
            f"SQL references table(s) not in allowlist {sorted(ALLOWED_SQL_TABLES)}: {invalid}"
        )


def _ensure_limit(sql: str, limit: int = DEFAULT_QUERY_LIMIT) -> str:
    """Append LIMIT when a broad SELECT has no explicit limit."""
    cleaned = sql.strip().rstrip(";")
    if re.search(r"(?is)\blimit\s+\d+", cleaned):
        return cleaned
    return f"{cleaned}\nLIMIT {limit}"


def _validate_read_only_sql(sql: str) -> str:
    cleaned = sql.strip().rstrip(";")
    if not cleaned:
        raise ValueError("SQL is empty.")
    if ";" in cleaned:
        raise ValueError("Multiple SQL statements are not allowed.")
    if not re.match(r"(?is)^(?:select|with)\s+", cleaned):
        raise ValueError("Only SELECT / WITH statements are allowed.")
    blocked = ["insert ", "update ", "delete ", "drop ", "alter ", "create ", "pragma "]
    lower_sql = cleaned.lower()
    if any(token in lower_sql for token in blocked):
        raise ValueError("Non read-only SQL operation detected.")
    _validate_table_whitelist(cleaned)
    return _ensure_limit(cleaned)


def run_sql_query_with_meta(sql: str, params: tuple | None = None) -> Dict[str, Any]:
    """Execute validated read-only SQL and return rows with execution metadata."""
    validated_sql = _validate_read_only_sql(sql)
    db_path = SQLITE_DB_PATH
    if not os.path.isabs(db_path):
        base = os.path.dirname(os.path.dirname(__file__))
        db_path = os.path.join(base, db_path.replace("/", os.sep))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    started = time.perf_counter()
    try:
        cur.execute(validated_sql, params or ())
        rows = cur.fetchall()
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        data = [dict(r) for r in rows]
        return {
            "rows": data,
            "meta": {
                "row_count": len(data),
                "latency_ms": latency_ms,
                "executed_sql": validated_sql,
            },
        }
    finally:
        conn.close()


def run_sql_query(sql: str, params: tuple | None = None) -> List[Dict[str, Any]]:
    """Backward-compatible wrapper returning only query rows."""
    result = run_sql_query_with_meta(sql, params=params)
    return result["rows"]
