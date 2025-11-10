from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

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


def get_retriever():
    vs = get_vectorstore()
    # k can be tuned later; using 5 for now
    return vs.as_retriever(search_kwargs={"k": 5})


# Manual test: uv run python -m rag.retriever
if __name__ == "__main__":
    from langchain_core.documents import Document

    retriever = get_retriever()
    docs = retriever.get_relevant_documents("Test query.")
    print(f"Got {len(docs)} docs from Pinecone.")
