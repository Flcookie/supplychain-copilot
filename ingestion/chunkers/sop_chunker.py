import re
from typing import Iterable

from .base import BaseChunker, Chunk


class SopChunker(BaseChunker):
    doc_type = "sop"

    def split_text(self, text: str) -> Iterable[Chunk]:
        pieces = re.split(r"(?m)^(Step\s+\d+\.\s+.+)$", text)
        header = pieces[0].strip()
        for i in range(1, len(pieces), 2):
            title = pieces[i].strip()
            body = pieces[i + 1].strip() if i + 1 < len(pieces) else ""
            yield Chunk(text=f"{header}\n\n{title}\n\n{body}", section_title=title)
