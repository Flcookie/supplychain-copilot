from functools import lru_cache

from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from core.config import (
    EMBEDDING_MODEL,
    PINECONE_HOST,
    require_openai,
    require_pinecone,
)

NAMESPACE = "supplychain"


@lru_cache(maxsize=1)
def _pinecone_index():
    try:
        from pinecone import Pinecone
    except ImportError:
        from pinecone.pinecone import Pinecone

    api_key, index_name = require_pinecone()
    pc = Pinecone(api_key=api_key)
    if PINECONE_HOST:
        return pc.Index(index_name, host=PINECONE_HOST)
    return pc.Index(index_name)


@lru_cache(maxsize=1)
def _embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=require_openai(),
    )


def get_vectorstore() -> PineconeVectorStore:
    return PineconeVectorStore(
        index=_pinecone_index(),
        embedding=_embeddings(),
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
    from core.config import RERANK_POOL
    from rag.hybrid_retriever import HybridRetriever
    from rag.rerank import get_reranker

    return HybridRetriever(
        k=k,
        rerank_pool=RERANK_POOL,
        doc_types=doc_types,
        reranker=get_reranker(),
    )


if __name__ == "__main__":
    retriever = get_retriever()
    docs = retriever.get_relevant_documents("Test query.")
    print(f"Got {len(docs)} docs from Pinecone.")
