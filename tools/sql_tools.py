import os
import sqlite3
import time
import re
from typing import List, Dict, Any

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "supplychain_kpi.db")


def _validate_read_only_sql(sql: str) -> None:
    cleaned = sql.strip().rstrip(";")
    if not cleaned:
        raise ValueError("SQL is empty.")
    if ";" in cleaned:
        raise ValueError("Multiple SQL statements are not allowed.")
    if not re.match(r"(?is)^select\s+", cleaned):
        raise ValueError("Only SELECT statements are allowed.")
    blocked = ["insert ", "update ", "delete ", "drop ", "alter ", "create ", "pragma "]
    lower_sql = cleaned.lower()
    if any(token in lower_sql for token in blocked):
        raise ValueError("Non read-only SQL operation detected.")


def run_sql_query_with_meta(sql: str, params: tuple | None = None) -> Dict[str, Any]:
    """Execute validated read-only SQL and return rows with execution metadata."""
    _validate_read_only_sql(sql)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    started = time.perf_counter()
    try:
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        data = [dict(r) for r in rows]
        return {"rows": data, "meta": {"row_count": len(data), "latency_ms": latency_ms}}
    finally:
        conn.close()


def run_sql_query(sql: str, params: tuple | None = None) -> List[Dict[str, Any]]:
    """Backward-compatible wrapper returning only query rows."""
    result = run_sql_query_with_meta(sql, params=params)
    return result["rows"]
