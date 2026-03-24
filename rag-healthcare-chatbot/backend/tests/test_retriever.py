import unittest
from unittest.mock import MagicMock, patch

from app.rag.retriever import Retriever


class RetrieverTests(unittest.TestCase):
    def test_explicit_scope_bypasses_router_and_queries_selected_collection(self):
        with patch("app.rag.retriever.VectorStore") as store_cls, patch(
            "app.rag.retriever.ApplicationRouter"
        ) as router_cls:
            store = MagicMock()
            store.search.return_value = [{"text": "therapy gap info"}]
            store_cls.return_value = store
            router = MagicMock()
            router_cls.return_value = router

            retriever = Retriever()
            route, chunks = retriever.retrieve(
                "What is therapy gap?",
                history=[],
                where={"app": "kinexushhd"},
            )

        router.resolve_collection.assert_not_called()
        store.search.assert_called_once_with(
            "What is therapy gap?",
            collection_name="kinexushhd",
            k=2,
            where={},
        )
        self.assertEqual(route["app"], "KINEXUSHHD")
        self.assertEqual(route["collection"], "kinexushhd")
        self.assertEqual(route["method"], "explicit")
        self.assertEqual(chunks, [{"text": "therapy gap info"}])


if __name__ == "__main__":
    unittest.main()
