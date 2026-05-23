import re
from typing import Iterable

from .base import BaseChunker, Chunk


class PolicyChunker(BaseChunker):
    doc_type = "policy"

    def split_text(self, text: str) -> Iterable[Chunk]:
        parts = re.split(r"(?m)^##\s+", text)
        header = parts[0].strip()
        for part in parts[1:]:
            lines = part.strip().splitlines()
            if not lines:
                continue
            title = lines[0].strip()
            body = "\n".join(lines[1:]).strip()
            yield Chunk(text=f"{header}\n\n## {title}\n\n{body}", section_title=title)
