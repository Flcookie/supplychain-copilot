"""Unit tests for semantic cache exact-match path (no embeddings required)."""

from __future__ import annotations

from core.semantic_cache import SemanticCache, normalize_question


def test_normalize_question():
    assert normalize_question("  How  is ESG? ") == "how is esg?"


def test_exact_cache_hit(monkeypatch):
    monkeypatch.setenv("ENABLE_SEMANTIC_CACHE", "true")
    monkeypatch.setenv("SEMANTIC_CACHE_THRESHOLD", "0.99")
    cache = SemanticCache()
    payload = {"answer": "ESG uses weighted pillars.", "clarification_required": False}
    cache.put("How is ESG score calculated?", "en", payload)
    hit = cache.get("How is ESG score calculated?", "en")
    assert hit is not None
    assert hit["cache_hit"] is True
    assert hit["cache_mode"] == "exact"
    assert hit["answer"] == payload["answer"]


def test_cache_skips_clarification(monkeypatch):
    monkeypatch.setenv("ENABLE_SEMANTIC_CACHE", "true")
    cache = SemanticCache()
    cache.put("Compare them", "en", {"answer": "x", "clarification_required": True})
    assert cache.get("Compare them", "en") is None


def test_disabled_cache(monkeypatch):
    monkeypatch.setenv("ENABLE_SEMANTIC_CACHE", "false")
    cache = SemanticCache()
    cache.put("How is ESG score calculated?", "en", {"answer": "x"})
    assert cache.get("How is ESG score calculated?", "en") is None
