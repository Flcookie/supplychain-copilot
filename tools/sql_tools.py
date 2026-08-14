import os
import time
from typing import Any, Dict, List

from core.config import SQLITE_DB_PATH
from tools.sql_guard import (
    ALLOWED_SQL_TABLES,
    DEFAULT_QUERY_LIMIT,
    validate_read_only_sql,
)

__all__ = [
    "ALLOWED_SQL_TABLES",
    "DEFAULT_QUERY_LIMIT",
    "run_sql_query",
    "run_sql_query_with_meta",
    "validate_read_only_sql",
]


def _validate_read_only_sql(sql: str) -> str:
    return validate_read_only_sql(sql)


def run_sql_query_with_meta(sql: str, params: tuple | None = None) -> Dict[str, Any]:
    """Execute validated read-only SQL and return rows with execution metadata."""
    validated_sql = validate_read_only_sql(sql)
    db_path = SQLITE_DB_PATH
    if not os.path.isabs(db_path):
        base = os.path.dirname(os.path.dirname(__file__))
        db_path = os.path.join(base, db_path.replace("/", os.sep))
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    started = time.perf_counter()
    try:
        cur.execute(validated_sql, params or ())
        rows = cur.fetchall()
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        data = [dict(r) for r in rows]
        try:
            from observability.recorder import record_step

            record_step(
                tool_called="sql_query",
                tool_latency_ms=latency_ms,
                detail={"row_count": len(data), "sql_preview": validated_sql[:240]},
            )
        except Exception:
            pass
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
