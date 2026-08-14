"""In-memory semantic cache for repeated Copilot questions.

Uses OpenAI embeddings when available; falls back to normalized exact-match.
Enable with ENABLE_SEMANTIC_CACHE=true (default on for API path).
"""

from __future__ import annotations

import hashlib
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any


def _enabled() -> bool:
    return os.getenv("ENABLE_SEMANTIC_CACHE", "true").lower() in {"1", "true", "yes"}


def _threshold() -> float:
    try:
        return float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.92"))
    except ValueError:
        return 0.92


def _ttl_seconds() -> float:
    try:
        return float(os.getenv("SEMANTIC_CACHE_TTL_SECONDS", "3600"))
    except ValueError:
        return 3600.0


def _max_entries() -> int:
    try:
        return int(os.getenv("SEMANTIC_CACHE_MAX_ENTRIES", "256"))
    except ValueError:
        return 256


def normalize_question(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _exact_key(question: str, response_language: str) -> str:
    payload = f"{response_language}|{normalize_question(question)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


@dataclass
class CacheEntry:
    exact_key: str
    question: str
    response_language: str
    embedding: list[float] | None
    payload: dict[str, Any]
    created_at: float = field(default_factory=time.time)
    hits: int = 0


class SemanticCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: list[CacheEntry] = []
        self._by_exact: dict[str, CacheEntry] = {}
        self._embedder = None
        self._embedder_failed = False

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._by_exact.clear()

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled": _enabled(),
                "size": len(self._entries),
                "threshold": _threshold(),
                "ttl_seconds": _ttl_seconds(),
            }

    def _get_embedder(self):
        if self._embedder_failed:
            return None
        if self._embedder is not None:
            return self._embedder
        try:
            from langchain_openai import OpenAIEmbeddings
            from core.config import EMBEDDING_MODEL

            self._embedder = OpenAIEmbeddings(model=EMBEDDING_MODEL)
            return self._embedder
        except Exception:
            self._embedder_failed = True
            return None

    def _embed(self, text: str) -> list[float] | None:
        embedder = self._get_embedder()
        if embedder is None:
            return None
        try:
            return list(embedder.embed_query(text))
        except Exception:
            return None

    def _evict_expired_unlocked(self) -> None:
        ttl = _ttl_seconds()
        now = time.time()
        keep: list[CacheEntry] = []
        for entry in self._entries:
            if now - entry.created_at <= ttl:
                keep.append(entry)
            else:
                self._by_exact.pop(entry.exact_key, None)
        self._entries = keep
        while len(self._entries) > _max_entries():
            oldest = min(self._entries, key=lambda e: e.created_at)
            self._entries.remove(oldest)
            self._by_exact.pop(oldest.exact_key, None)

    def get(self, question: str, response_language: str) -> dict[str, Any] | None:
        if not _enabled():
            return None
        key = _exact_key(question, response_language)
        with self._lock:
            self._evict_expired_unlocked()
            exact = self._by_exact.get(key)
            if exact is not None:
                exact.hits += 1
                payload = dict(exact.payload)
                payload["cache_hit"] = True
                payload["cache_mode"] = "exact"
                return payload

            query_emb = None
        # Embed outside lock (network)
        query_emb = self._embed(normalize_question(question))
        if query_emb is None:
            return None

        threshold = _threshold()
        best: CacheEntry | None = None
        best_score = 0.0
        with self._lock:
            for entry in self._entries:
                if entry.response_language != response_language:
                    continue
                if not entry.embedding:
                    continue
                score = _cosine(query_emb, entry.embedding)
                if score > best_score:
                    best_score = score
                    best = entry
            if best is not None and best_score >= threshold:
                best.hits += 1
                payload = dict(best.payload)
                payload["cache_hit"] = True
                payload["cache_mode"] = "semantic"
                payload["cache_similarity"] = round(best_score, 4)
                return payload
        return None

    def put(self, question: str, response_language: str, payload: dict[str, Any]) -> None:
        if not _enabled():
            return
        # Do not cache clarification / refusal-only paths that are empty of value
        if payload.get("clarification_required"):
            return
        key = _exact_key(question, response_language)
        emb = self._embed(normalize_question(question))
        stored = {
            k: v
            for k, v in payload.items()
            if k not in {"cache_hit", "cache_mode", "cache_similarity", "trace_id"}
        }
        entry = CacheEntry(
            exact_key=key,
            question=question,
            response_language=response_language,
            embedding=emb,
            payload=stored,
        )
        with self._lock:
            self._evict_expired_unlocked()
            old = self._by_exact.get(key)
            if old is not None and old in self._entries:
                self._entries.remove(old)
            self._by_exact[key] = entry
            self._entries.append(entry)


_CACHE = SemanticCache()


def get_semantic_cache() -> SemanticCache:
    return _CACHE
