import hashlib
import os
import re
from dataclasses import dataclass
from typing import Iterable

from langchain_core.documents import Document


@dataclass
class Chunk:
    text: str
    section_title: str


def stable_chunk_id(source_name: str, section_title: str, position: int) -> str:
    raw = f"{source_name}:{section_title}:{position}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:12]


def infer_language(text: str) -> str:
    return "zh" if re.search(r"[\u4e00-\u9fff]", text) else "en"


def metadata_for(path: str, doc_type: str, section_title: str, position: int, text: str) -> dict:
    source_name = os.path.basename(path)
    return {
        "doc_type": doc_type,
        "source_name": source_name,
        "source": path,
        "section_title": section_title,
        "chunk_id": stable_chunk_id(source_name, section_title, position),
        "effective_date": _extract_field(text, "Effective Date") or "2026-01-01",
        "owner": _extract_field(text, "Owner") or "Procurement",
        "access_level": _extract_field(text, "Access Level") or "internal",
        "language": infer_language(text),
    }


def _extract_field(text: str, field: str) -> str | None:
    pattern = re.compile(rf"(?im)^{re.escape(field)}:\s*(.+)$")
    match = pattern.search(text)
    return match.group(1).strip() if match else None


class BaseChunker:
    doc_type = "generic"

    def split_text(self, text: str) -> Iterable[Chunk]:
        yield Chunk(text=text.strip(), section_title="Document")

    def chunk_file(self, path: str, text: str) -> list[Document]:
        docs: list[Document] = []
        for position, chunk in enumerate(self.split_text(text), start=1):
            if not chunk.text.strip():
                continue
            docs.append(
                Document(
                    page_content=chunk.text.strip(),
                    metadata=metadata_for(path, self.doc_type, chunk.section_title, position, text),
                )
            )
        return docs
