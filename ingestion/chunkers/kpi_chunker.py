import re
from typing import Iterable

from .base import BaseChunker, Chunk


class KpiChunker(BaseChunker):
    doc_type = "kpi_dict"

    def split_text(self, text: str) -> Iterable[Chunk]:
        pieces = re.split(r"(?m)^(Metric:\s+.+)$", text)
        header = pieces[0].strip()
        for i in range(1, len(pieces), 2):
            title = pieces[i].strip()
            body = pieces[i + 1].strip() if i + 1 < len(pieces) else ""
            yield Chunk(text=f"{header}\n\n{title}\n{body}", section_title=title.replace("Metric:", "").strip())
