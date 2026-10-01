"""Split local knowledge documents into stable, traceable chunks."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class KnowledgeChunk:
    chunk_id: str
    source_name: str
    heading: str
    text: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def chunk_markdown_file(path: Path, max_chars: int = 900) -> list[KnowledgeChunk]:
    text = path.read_text(encoding="utf-8")
    sections = re.split(r"(?m)^(?=##?\s)", text)
    chunks: list[KnowledgeChunk] = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        lines = section.splitlines()
        heading = lines[0].lstrip("# ").strip() if lines[0].startswith("#") else path.stem
        body = "\n".join(lines[1:] if lines[0].startswith("#") else lines).strip()
        paragraphs = [item.strip() for item in re.split(r"\n\s*\n", body) if item.strip()]
        buffer = ""
        for paragraph in paragraphs or [body]:
            candidate = f"{buffer}\n\n{paragraph}".strip()
            if buffer and len(candidate) > max_chars:
                chunks.append(_make_chunk(path.name, heading, buffer))
                buffer = paragraph
            else:
                buffer = candidate
        if buffer:
            chunks.append(_make_chunk(path.name, heading, buffer))
    return chunks


def _make_chunk(source_name: str, heading: str, text: str) -> KnowledgeChunk:
    digest = hashlib.sha1(f"{source_name}|{heading}|{text}".encode("utf-8")).hexdigest()[:12]
    return KnowledgeChunk(f"kb-{digest}", source_name, heading, text)


def load_knowledge_chunks(directory: Path) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    for path in sorted(directory.glob("*.md")):
        chunks.extend(chunk_markdown_file(path))
    return chunks
