import os
import sys

# Ensure modules under project root (rag / core) can be imported
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.retriever import get_vectorstore, NAMESPACE


DOCS_DIR = "data/docs"


def load_docs():
    if not os.path.exists(DOCS_DIR):
        raise FileNotFoundError(f"{DOCS_DIR} does not exist. Please create it and add some documents first.")

    loader = DirectoryLoader(
        DOCS_DIR,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},  
        show_progress=True,
        silent_errors=False,  
    )
    docs = loader.load()

    if not docs:
        print("No documents were successfully loaded. Please check that files under data/docs are UTF-8 encoded text.")

    return docs


def split_docs(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        add_start_index=True,
    )
    return splitter.split_documents(docs)


def main():
    print("📄 Loading docs...")
    docs = load_docs()
    print(f"Loaded {len(docs)} documents")

    print("✂️ Splitting...")
    chunks = split_docs(docs)
    print(f"Created {len(chunks)} chunks")

    if not chunks:
        print("❌ No valid document chunks found. Please check that data/docs contains valid content.")
        return

    print(f"📦 Indexing into Pinecone namespace='{NAMESPACE}' ...")
    vs = get_vectorstore()
    vs.add_documents(chunks)

    print("✅ Ingestion done.")


if __name__ == "__main__":
    main()
