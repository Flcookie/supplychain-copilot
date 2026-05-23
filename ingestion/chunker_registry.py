from ingestion.chunkers import (
    BaseChunker,
    ContractChunker,
    FaqChunker,
    KpiChunker,
    PolicyChunker,
    SopChunker,
)


CHUNKERS = {
    "policy": PolicyChunker,
    "contract": ContractChunker,
    "kpi_dict": KpiChunker,
    "sop": SopChunker,
    "faq": FaqChunker,
}


def dispatch_chunker(doc_type: str) -> BaseChunker:
    chunker_cls = CHUNKERS.get(doc_type, BaseChunker)
    return chunker_cls()
