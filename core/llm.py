"""ChatOpenAI factory — constructed on first use, not at import time."""

from __future__ import annotations

from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1)
def get_llm() -> Any:
    """Return the shared temperature-0 chat model. Requires OPENAI_API_KEY."""
    from langchain_openai import ChatOpenAI

    from core.config import LLM_MODEL, require_openai
    from observability.recorder import wrap_llm

    require_openai()
    return wrap_llm(ChatOpenAI(model=LLM_MODEL, temperature=0))


def reset_llm_cache() -> None:
    get_llm.cache_clear()
