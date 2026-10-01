"""Tests for traceable and role-compatible knowledge retrieval."""

import unittest

from rag.retrieval import KnowledgeRetriever


class RetrievalTests(unittest.TestCase):
    def test_returns_traceable_chunks(self):
        retriever = KnowledgeRetriever()
        hits = retriever.search("Marksman high damage share and safe positioning", top_k=3)
        self.assertEqual(len(hits), 3)
        self.assertTrue(all(hit["chunk_id"].startswith("kb-") for hit in hits))
        self.assertTrue(all(hit["source_name"] for hit in hits))

    def test_role_filter_guarantees_target_role_and_excludes_other_roles(self):
        retriever = KnowledgeRetriever()
        hits = retriever.search("Marksman gold damage survival", top_k=4, role="Marksman")
        headings = [hit["heading"] for hit in hits]
        self.assertIn("Marksman", headings)
        self.assertFalse(any(heading in {"Mage", "Assassin", "Fighter", "Tank", "Support"} for heading in headings))


if __name__ == "__main__":
    unittest.main()
