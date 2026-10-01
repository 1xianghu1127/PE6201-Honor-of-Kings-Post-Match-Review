"""Build and inspect the local knowledge-base index."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.chunking import load_knowledge_chunks


def main() -> None:
    knowledge_dir = ROOT / "knowledge_base"
    chunks = load_knowledge_chunks(knowledge_dir)
    manifest = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "embedding_method": "local TF-IDF vectors",
        "document_count": len(list(knowledge_dir.glob("*.md"))),
        "chunk_count": len(chunks),
        "chunks": [chunk.to_dict() for chunk in chunks],
    }
    output = knowledge_dir / "index_manifest.json"
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Indexed {manifest['document_count']} documents into {manifest['chunk_count']} chunks.")


if __name__ == "__main__":
    main()
