"""Config import must not require cloud credentials."""

from __future__ import annotations

import pytest


def test_require_helpers_are_lazy():
    import core.config as config

    original = config.OPENAI_API_KEY
    original_pc = config.PINECONE_API_KEY
    original_idx = config.PINECONE_INDEX_NAME
    try:
        config.OPENAI_API_KEY = None
        config.PINECONE_API_KEY = None
        config.PINECONE_INDEX_NAME = None
        assert config.has_openai() is False
        assert config.has_pinecone() is False
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            config.require_openai()
        with pytest.raises(ValueError, match="PINECONE"):
            config.require_pinecone()
    finally:
        config.OPENAI_API_KEY = original
        config.PINECONE_API_KEY = original_pc
        config.PINECONE_INDEX_NAME = original_idx


def test_sql_tools_import_does_not_need_keys():
    from tools.sql_tools import ALLOWED_SQL_TABLES

    assert "suppliers" in ALLOWED_SQL_TABLES
