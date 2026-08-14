"""Fail-closed SQL guard: parse with sqlglot, allow SELECT/WITH only, table allowlist, LIMIT.

Regex / substring checks are not used for authorization. Unparseable SQL is rejected.
"""

from __future__ import annotations

from typing import Iterable

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

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

FORBIDDEN_TABLES = frozenset(
    {
        "sqlite_master",
        "sqlite_temp_master",
        "sqlite_sequence",
        "sqlite_stat1",
        "sqlite_stat4",
    }
)

ALLOWED_SQLITE_SCHEMAS = frozenset({"", "main", "temp"})

DEFAULT_QUERY_LIMIT = 100

def _forbidden_expr_types() -> tuple[type, ...]:
    names = (
        "Insert",
        "Update",
        "Delete",
        "Drop",
        "Create",
        "Alter",
        "Merge",
        "Command",
        "Pragma",
        "Grant",
        "Revoke",
        "TruncateTable",
        "Undrop",
        "Attach",
        "Detach",
    )
    return tuple(cls for name in names if (cls := getattr(exp, name, None)) is not None)


_FORBIDDEN_EXPR = _forbidden_expr_types()

_ALLOWED_ROOT = (exp.Select, exp.Union, exp.Except, exp.Intersect, exp.With)


def _root_query(expression: exp.Expression) -> exp.Expression:
    if isinstance(expression, exp.With):
        return expression.this
    return expression


def _root_has_limit(expression: exp.Expression) -> bool:
    root = _root_query(expression)
    return bool(root.args.get("limit"))


def _cte_names(expression: exp.Expression) -> set[str]:
    names: set[str] = set()
    for cte in expression.find_all(exp.CTE):
        alias = cte.alias
        if alias:
            names.add(alias.lower())
    return names


def _table_names(expression: exp.Expression) -> list[str]:
    cte = _cte_names(expression)
    found: list[str] = []
    for table in expression.find_all(exp.Table):
        name = (table.name or "").lower()
        if not name or name in cte:
            continue
        schema = (table.db or table.catalog or "").lower()
        if schema not in ALLOWED_SQLITE_SCHEMAS:
            raise ValueError(f"SQL schema '{schema}' is not allowed.")
        found.append(name)
    return found


def _reject_forbidden(expression: exp.Expression) -> None:
    for node in expression.walk():
        if isinstance(node, _FORBIDDEN_EXPR):
            kind = type(node).__name__
            raise ValueError(f"Non read-only SQL operation detected ({kind}).")
        if isinstance(node, exp.Anonymous):
            this = str(node.this or "").lower()
            if this in {"load_extension", "readfile", "writefile"}:
                raise ValueError(f"SQL function '{this}' is not allowed.")


def _ensure_limit(expression: exp.Expression, limit: int) -> exp.Expression:
    if _root_has_limit(expression):
        return expression
    root = _root_query(expression)
    limited = root.limit(limit)
    if isinstance(expression, exp.With):
        expression.set("this", limited)
        return expression
    return limited


def validate_read_only_sql(
    sql: str,
    *,
    allowed_tables: Iterable[str] | None = None,
    limit: int = DEFAULT_QUERY_LIMIT,
) -> str:
    """Parse, authorize, and return a single SELECT/WITH with LIMIT applied."""
    cleaned = (sql or "").strip().rstrip(";")
    if not cleaned:
        raise ValueError("SQL is empty.")

    try:
        statements = sqlglot.parse(cleaned, read="sqlite")
    except ParseError as exc:
        raise ValueError(f"SQL could not be parsed: {exc}") from exc

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise ValueError("Exactly one SQL statement is allowed.")

    tree = statements[0]
    if not isinstance(tree, _ALLOWED_ROOT):
        raise ValueError("Only SELECT / WITH statements are allowed.")

    _reject_forbidden(tree)

    allow = {t.lower() for t in (allowed_tables or ALLOWED_SQL_TABLES)}
    tables = _table_names(tree)
    invalid = [t for t in tables if t not in allow]
    forbidden = [t for t in tables if t in FORBIDDEN_TABLES]
    if forbidden:
        raise ValueError(f"SQL references forbidden catalog table(s): {forbidden}")
    if invalid:
        raise ValueError(
            f"SQL references table(s) not in allowlist {sorted(allow)}: {invalid}"
        )

    tree = _ensure_limit(tree, limit)
    return tree.sql(dialect="sqlite")
