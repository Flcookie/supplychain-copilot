"""Export Ratti policies_knowledge_base CSV into data/docs/policy/ for RAG ingestion."""

from __future__ import annotations

import csv
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = (
    ROOT
    / "ratti_supplier_lifecycle_copilot_package"
    / "ratti_supplier_lifecycle_copilot_package"
    / "csv_data"
    / "policies_knowledge_base.csv"
)
OUT_DIR = ROOT / "data" / "docs" / "policy"


def export_policies() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Policies CSV not found: {CSV_PATH}")

    count = 0
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            chunk_id = row.get("chunk_id", f"chunk_{count}")
            doc_title = row.get("doc_title", "Ratti Policy")
            section = row.get("section", "")
            text = row.get("text", "").strip()
            if not text:
                continue
            filename = OUT_DIR / f"ratti_{chunk_id.lower()}.txt"
            # PolicyChunker splits on markdown ## headings; one section per Ratti chunk.
            content = (
                f"## {doc_title} — {section}\n\n"
                f"{text}\n\n"
                f"chunk_id: {chunk_id}\n"
                f"doc_id: {row.get('doc_id', '')}\n"
                f"source_type: {row.get('source_type', 'Ratti policy')}\n"
            )
            filename.write_text(content, encoding="utf-8")
            count += 1
            print(f"Wrote {filename.name}")

    print(f"Exported {count} policy chunks to {OUT_DIR}")
    return count


if __name__ == "__main__":
    export_policies()
