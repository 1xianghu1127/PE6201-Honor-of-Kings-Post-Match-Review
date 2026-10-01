"""Retrieve role-compatible knowledge chunks for one match."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rag.chunking import KnowledgeChunk, load_knowledge_chunks
from rag.embeddings import LocalTfidfEmbeddings


DEFAULT_KB_DIR = Path(__file__).resolve().parents[1] / "knowledge_base"
ROLE_NAMES = {"Marksman", "Mage", "Assassin", "Fighter", "Tank", "Support"}


class KnowledgeRetriever:
    def __init__(self, knowledge_dir: Path | None = None):
        self.knowledge_dir = knowledge_dir or DEFAULT_KB_DIR
        self.chunks: list[KnowledgeChunk] = load_knowledge_chunks(self.knowledge_dir)
        self.embeddings = LocalTfidfEmbeddings()
        corpus = [f"{chunk.heading}\n{chunk.text}" for chunk in self.chunks]
        self.embeddings.fit(corpus)

    def search(self, query: str, top_k: int = 4, role: str | None = None) -> list[dict[str, Any]]:
        """Return traceable chunks without mixing guidance for different roles.

        The TF-IDF ranker still chooses general gameplay evidence. When a supported
        role is known, the exact role chunk is guaranteed and chunks whose headings
        clearly belong to another role are excluded.
        """
        if top_k <= 0:
            return []

        ranked = self.embeddings.search(query, top_k=len(self.chunks))
        allowed_indexes = [
            hit.index
            for hit in ranked
            if role not in ROLE_NAMES or self._heading_role(self.chunks[hit.index].heading) in {None, role}
        ]

        selected_indexes: list[int] = []
        if role in ROLE_NAMES:
            exact_role_indexes = [
                index
                for index in allowed_indexes
                if self.chunks[index].source_name == "roles.md"
                and self.chunks[index].heading.casefold() == role.casefold()
            ]
            selected_indexes.extend(exact_role_indexes[:1])

        selected_indexes.extend(index for index in allowed_indexes if index not in selected_indexes)
        score_by_index = {hit.index: hit.score for hit in ranked}
        return [
            {
                **self.chunks[index].to_dict(),
                "similarity_score": round(score_by_index[index], 6),
            }
            for index in selected_indexes[:top_k]
        ]

    @staticmethod
    def _heading_role(heading: str) -> str | None:
        words = set(heading.replace("-", " ").split())
        return next((role for role in ROLE_NAMES if role in words), None)


def build_match_query(data: dict[str, Any]) -> str:
    parts = [
        f"hero {data.get('hero') or 'unknown'}",
        f"role {data.get('role') or 'unknown'}",
        f"kills {data.get('kills')}",
        f"deaths {data.get('deaths')}",
        f"assists {data.get('assists')}",
        f"gold share {data.get('gold_share_pct')}",
        f"damage share {data.get('damage_dealt_share_pct')}",
        f"damage taken share {data.get('damage_taken_share_pct')}",
        f"kill participation {data.get('kill_participation_pct')}",
        f"result {data.get('match_result') or 'unknown'}",
    ]
    return " | ".join(parts)
