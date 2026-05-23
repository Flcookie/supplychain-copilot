from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
try:
    from pinecone import Pinecone
except ImportError:
    # Compatibility fallback for environments where pinecone exports runtime symbols
    # from `pinecone.pinecone` instead of package root.
    from pinecone.pinecone import Pinecone

from core.config import (
    OPENAI_API_KEY,
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
    EMBEDDING_MODEL,
    PINECONE_HOST,
)

# 1️⃣ Initialize Pinecone client
pc = Pinecone(api_key=PINECONE_API_KEY)

# Compatibility: if PINECONE_HOST (serverless) is set in .env, use it; otherwise, use index name directly
if PINECONE_HOST:
    index = pc.Index(PINECONE_INDEX_NAME, host=PINECONE_HOST)
else:
    index = pc.Index(PINECONE_INDEX_NAME)

# 2️⃣ OpenAI Embeddings (text-embedding-3-small, 1536 dimensions)
embeddings = OpenAIEmbeddings(
    model=EMBEDDING_MODEL,
    api_key=OPENAI_API_KEY,
)

# 3️⃣ Wrap VectorStore (namespace distinguishes business domains, fixed as "supplychain" for now)
NAMESPACE = "supplychain"


def get_vectorstore() -> PineconeVectorStore:
    return PineconeVectorStore(
        index=index,
        embedding=embeddings,
        namespace=NAMESPACE,
    )


def _doc_type_filter(doc_types: list[str] | None) -> dict | None:
    if not doc_types:
        return None
    if len(doc_types) == 1:
        return {"doc_type": doc_types[0]}
    return {"doc_type": {"$in": doc_types}}


def get_vector_retriever(k: int = 5, doc_types: list[str] | None = None):
    vs = get_vectorstore()
    search_kwargs = {"k": k}
    metadata_filter = _doc_type_filter(doc_types)
    if metadata_filter:
        search_kwargs["filter"] = metadata_filter
    return vs.as_retriever(search_kwargs=search_kwargs)


def get_retriever(k: int = 5, doc_types: list[str] | None = None):
    from rag.hybrid_retriever import HybridRetriever
    from rag.rerank import get_reranker

    return HybridRetriever(k=k, doc_types=doc_types, reranker=get_reranker())


# Manual test: uv run python -m rag.retriever
if __name__ == "__main__":
    from langchain_core.documents import Document

    retriever = get_retriever()
    docs = retriever.get_relevant_documents("Test query.")
    print(f"Got {len(docs)} docs from Pinecone.")
