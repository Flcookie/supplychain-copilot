"""LangGraph checkpointer factory (MemorySaver or SqliteSaver)."""

from __future__ import annotations

import os
import sqlite3
from functools import lru_cache
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

_BASE_DIR = os.path.dirname(os.path.dirname(__file__))
_DEFAULT_SQLITE = os.path.join(_BASE_DIR, "data", "checkpoints.sqlite")

# Keep the SQLite connection alive for the process lifetime.
_sqlite_conn: sqlite3.Connection | None = None


def checkpoint_backend() -> str:
    return (os.getenv("CHECKPOINT_BACKEND") or "sqlite").strip().lower()


def checkpoint_sqlite_path() -> str:
    return os.getenv("CHECKPOINT_SQLITE_PATH") or _DEFAULT_SQLITE


@lru_cache(maxsize=1)
def get_checkpointer() -> Any:
    """Return a process-wide checkpointer.

    - ``CHECKPOINT_BACKEND=memory`` → in-process MemorySaver (tests / ephemeral)
    - default ``sqlite`` → durable SqliteSaver under ``data/checkpoints.sqlite``
    """
    global _sqlite_conn
    backend = checkpoint_backend()
    if backend in {"memory", "mem", "inmemory"}:
        return MemorySaver()

    path = checkpoint_sqlite_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    _sqlite_conn = sqlite3.connect(path, check_same_thread=False)
    from langgraph.checkpoint.sqlite import SqliteSaver

    saver = SqliteSaver(_sqlite_conn)
    saver.setup()
    return saver


def reset_checkpointer_cache() -> None:
    """Test helper: drop cached checkpointer (does not close open connections)."""
    get_checkpointer.cache_clear()
