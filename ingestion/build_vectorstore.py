import argparse
import os
import sys
from pathlib import Path

# Ensure modules under project root (rag / core) can be imported
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ingestion.chunker_registry import dispatch_chunker
from rag.bm25_index import save_bm25_index
from rag.retriever import get_vectorstore, NAMESPACE


DOCS_DIR = "data/docs"
SUPPORTED_EXTENSIONS = {".txt", ".md"}


def infer_doc_type(path: Path) -> str:
    try:
        relative = path.relative_to(DOCS_DIR)
        return relative.parts[0] if len(relative.parts) > 1 else "policy"
    except ValueError:
        return "policy"


def load_and_chunk_docs():
    docs_path = Path(DOCS_DIR)
    if not docs_path.exists():
        raise FileNotFoundError(f"{DOCS_DIR} does not exist. Please create it and add some documents first.")

    chunks = []
    for path in sorted(docs_path.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        doc_type = infer_doc_type(path)
        chunker = dispatch_chunker(doc_type)
        text = path.read_text(encoding="utf-8")
        file_chunks = chunker.chunk_file(str(path), text)
        chunks.extend(file_chunks)
        print(f" - {path} ({doc_type}) -> {len(file_chunks)} chunks")

    if not chunks:
        print("No document chunks were created. Please check data/docs content.")
    return chunks


def clear_namespace():
    print(f"Clearing Pinecone namespace='{NAMESPACE}' ...")
    vs = get_vectorstore()
    try:
        vs.delete(delete_all=True)
    except TypeError:
        vs.delete(ids=None, delete_all=True)
    except Exception as exc:
        if "Namespace not found" in str(exc) or "Not Found" in str(exc):
            print("Namespace did not exist; continuing with fresh index.")
        else:
            raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reindex", action="store_true", help="Clear namespace before indexing.")
    args = parser.parse_args()

    if args.reindex:
        clear_namespace()

    print("Loading docs...")
    chunks = load_and_chunk_docs()
    print(f"Created {len(chunks)} chunks")

    if not chunks:
        print("❌ No valid document chunks found. Please check that data/docs contains valid content.")
        return

    print(f"Indexing into Pinecone namespace='{NAMESPACE}' ...")
    vs = get_vectorstore()
    vs.add_documents(chunks)
    print("Writing local BM25 index ...")
    save_bm25_index(chunks)

    print("Ingestion done.")


if __name__ == "__main__":
    main()
