import os
import sys
from dotenv import load_dotenv

# Load .env from the project root
load_dotenv()

# ---------- LLM & Embedding ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
RERANKER_BACKEND = os.getenv("RERANKER_BACKEND", "cross_encoder")
RERANKER_FALLBACK = os.getenv("RERANKER_FALLBACK", "openai")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")
RERANK_POOL = int(os.getenv("RERANK_POOL", "20"))
ENABLE_HYDE = os.getenv("ENABLE_HYDE", "false").lower() == "true"

# ---------- Pinecone ----------
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("INDEX_NAME") or os.getenv("PINECONE_INDEX_NAME")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_HOST = os.getenv("PINECONE_HOST")

LANGSMITH_TRACING_V2 = os.getenv("LANGSMITH_TRACING_V2", "false").lower() == "true"
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "supplychain-copilot")

DB_URL = os.getenv("DB_URL", "sqlite:///data/ratti_copilot_demo.db")

_BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SQLITE_DB_PATH = os.getenv(
    "SQLITE_DB_PATH",
    os.path.join(_BASE_DIR, "data", "ratti_copilot_demo.db"),
)

SKILLHUB_DB_PATH = os.getenv(
    "SKILLHUB_DB_PATH",
    os.path.join(_BASE_DIR, "data", "skillhub.db"),
)

CHECKPOINT_BACKEND = os.getenv("CHECKPOINT_BACKEND", "sqlite")
CHECKPOINT_SQLITE_PATH = os.getenv(
    "CHECKPOINT_SQLITE_PATH",
    os.path.join(_BASE_DIR, "data", "checkpoints.sqlite"),
)

from core.demo_constants import DEMO_CURRENT_DATE, RATTI_DATA_SNAPSHOT  # noqa: E402


def has_openai() -> bool:
    return bool(OPENAI_API_KEY)


def has_pinecone() -> bool:
    return bool(PINECONE_API_KEY and PINECONE_INDEX_NAME)


def require_openai() -> str:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is required for LLM calls.")
    return OPENAI_API_KEY


def require_pinecone() -> tuple[str, str]:
    if not PINECONE_API_KEY or not PINECONE_INDEX_NAME:
        raise ValueError(
            "PINECONE_API_KEY and INDEX_NAME (or PINECONE_INDEX_NAME) are required for RAG."
        )
    return PINECONE_API_KEY, PINECONE_INDEX_NAME


def log_config(*, stream=None) -> None:
    """Print resolved config (stderr by default so MCP stdio stays clean)."""
    _log = stream or sys.stderr
    print("Config loaded:", file=_log)
    print(f" - LLM_MODEL = {LLM_MODEL}", file=_log)
    print(f" - EMBEDDING_MODEL = {EMBEDDING_MODEL}", file=_log)
    print(f" - RERANKER_BACKEND = {RERANKER_BACKEND}", file=_log)
    print(f" - RERANKER_FALLBACK = {RERANKER_FALLBACK}", file=_log)
    print(f" - RERANKER_MODEL = {RERANKER_MODEL}", file=_log)
    print(f" - RERANK_POOL = {RERANK_POOL}", file=_log)
    print(f" - ENABLE_HYDE = {ENABLE_HYDE}", file=_log)
    print(f" - PINECONE_INDEX_NAME = {PINECONE_INDEX_NAME}", file=_log)
    print(f" - OPENAI_API_KEY set = {has_openai()}", file=_log)
    print(f" - PINECONE_API_KEY set = {bool(PINECONE_API_KEY)}", file=_log)
    if PINECONE_HOST:
        print(f" - PINECONE_HOST = {PINECONE_HOST}", file=_log)
    if LANGSMITH_TRACING_V2:
        print(f" - LangSmith enabled, project = {LANGSMITH_PROJECT}", file=_log)
    print(f" - DEMO_CURRENT_DATE = {DEMO_CURRENT_DATE}", file=_log)
    print(f" - RATTI_DATA_SNAPSHOT = {RATTI_DATA_SNAPSHOT}", file=_log)


if __name__ == "__main__":
    log_config()
    print("All configs loaded")
