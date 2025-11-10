import os
from dotenv import load_dotenv

# Load .env from the project root
load_dotenv()

# ---------- LLM & Embedding ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# ---------- Pinecone ----------
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")


PINECONE_INDEX_NAME = os.getenv("INDEX_NAME") or os.getenv("PINECONE_INDEX_NAME")

PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")  
PINECONE_HOST = os.getenv("PINECONE_HOST")  


LANGSMITH_TRACING_V2 = os.getenv("LANGSMITH_TRACING_V2", "false").lower() == "true"
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "supplychain-copilot")

# ---------- Required variable check ----------
required_vars = {
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "PINECONE_API_KEY": PINECONE_API_KEY,
    "PINECONE_INDEX_NAME": PINECONE_INDEX_NAME,
}

missing = [k for k, v in required_vars.items() if not v]
if missing:
    raise ValueError(f"Missing environment variables: {', '.join(missing)}")

# ---------- Print summary on startup (for debugging, optional) ----------
print("Config loaded:")
print(f" - LLM_MODEL = {LLM_MODEL}")
print(f" - EMBEDDING_MODEL = {EMBEDDING_MODEL}")
print(f" - PINECONE_INDEX_NAME = {PINECONE_INDEX_NAME}")
if PINECONE_HOST:
    print(f" - PINECONE_HOST = {PINECONE_HOST}")
if LANGSMITH_TRACING_V2:
    print(f" - LangSmith enabled, project = {LANGSMITH_PROJECT}")

DB_URL = os.getenv("DB_URL", "sqlite:///data/supplychain_kpi.db")


if __name__ == "__main__":
    print("All configs loaded")

