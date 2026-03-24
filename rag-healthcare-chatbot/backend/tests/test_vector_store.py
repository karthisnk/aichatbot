import unittest
from unittest.mock import patch

from app.services.vector_store import VectorStore


class VectorStoreTests(unittest.TestCase):
    def test_rerank_prioritizes_password_help_chunks(self):
        store = VectorStore.__new__(VectorStore)
        results = [
            {
                "text": "General dashboard overview and patient summaries.",
                "section": "Overview",
                "type": "text",
                "keywords": "dashboard, summary",
                "_semantic_rank": 0,
            },
            {
                "text": (
                    "From the top navigation menu, clicking on Change password will take "
                    "user to the Change Password screen. Users can reset their account password."
                ),
                "section": "Change Password",
                "type": "text",
                "keywords": "change password, reset password, login",
                "_semantic_rank": 4,
            },
        ]

        reranked = store._rerank_results("how do i reset password", results)

        self.assertEqual(reranked[0]["section"], "Change Password")

    def test_query_expansion_treats_login_like_sign_in(self):
        store = VectorStore.__new__(VectorStore)

        expanded = store._expand_query_terms("how to sign in to kinexus")

        self.assertIn("login", expanded)
        self.assertIn("sign in", expanded)

    def test_processed_chunk_fallback_finds_login_help(self):
        store = VectorStore.__new__(VectorStore)
        fallback_chunks = [
            {
                "app": "KINEXUSHHD",
                "domain": "patient",
                "type": "text",
                "section": "Logging into kinexus HHD Portal",
                "page": 13,
                "text": "A valid username and password are required to log into the portal.",
                "keywords": ["login", "username", "password"],
            }
        ]

        with patch.object(VectorStore, "_load_processed_chunks", return_value=fallback_chunks):
            results = store._search_processed_chunks(
                "how to login",
                collection_name="kinexushhd",
                limit=5,
                where=None,
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["section"], "Logging into kinexus HHD Portal")


if __name__ == "__main__":
    unittest.main()
