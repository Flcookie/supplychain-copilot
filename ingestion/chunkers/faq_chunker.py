import re
from typing import Iterable

from .base import BaseChunker, Chunk


class FaqChunker(BaseChunker):
    doc_type = "faq"

    def split_text(self, text: str) -> Iterable[Chunk]:
        pieces = re.split(r"(?m)^(Q:\s+.+)$", text)
        header = pieces[0].strip()
        for i in range(1, len(pieces), 2):
            title = pieces[i].replace("Q:", "").strip()
            answer = pieces[i + 1].strip() if i + 1 < len(pieces) else ""
            yield Chunk(text=f"{header}\n\nQ: {title}\n{answer}", section_title=title)
