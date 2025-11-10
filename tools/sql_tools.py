import os
import sqlite3
from typing import List, Dict, Any

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "supplychain_kpi.db")


def run_sql_query(sql: str) -> List[Dict[str, Any]]:
    """Execute read-only SQL and return a list of dictionaries [{col: value}]."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
