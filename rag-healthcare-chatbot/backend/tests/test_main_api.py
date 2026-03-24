import importlib
import sys
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def load_main_with_mocks():
    rag_instance = MagicMock()
    feedback_store = MagicMock()
    llm_instance = MagicMock()

    patches = [
        patch("app.rag.pipeline.RAGPipeline", return_value=rag_instance),
        patch("app.services.feedback_store.FeedbackStore", return_value=feedback_store),
        patch("app.services.llm.LLM", return_value=llm_instance),
    ]

    for item in patches:
        item.start()

    sys.modules.pop("app.main", None)
    main_module = importlib.import_module("app.main")

    return main_module, rag_instance, feedback_store, llm_instance, patches


class MainApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (
            cls.main,
            cls.rag,
            cls.feedback_store,
            cls.llm,
            cls._patches,
        ) = load_main_with_mocks()
        cls.client = TestClient(cls.main.app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        for item in reversed(cls._patches):
            item.stop()

    def setUp(self):
        self.rag.reset_mock()
        self.feedback_store.reset_mock()
        self.llm.reset_mock()
        self.rag.run.side_effect = None
        self.rag.stream.side_effect = None

    def test_chat_endpoint_returns_result(self):
        self.rag.run.return_value = {
            "answer": "Use the patient tab.",
            "sources": [],
            "collection": "nx2meapp",
            "app": "Nx2meApp",
            "routing": {"collection": "nx2meapp"},
        }

        response = self.client.post(
            "/chat",
            json={
                "question": "How do I open patient details?",
                "app": "nx2meapp",
                "history": [{"role": "user", "text": "Earlier question"}],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "Use the patient tab.")
        self.rag.run.assert_called_once_with(
            "How do I open patient details?",
            history=[{"role": "user", "text": "Earlier question"}],
            where={"app": "nx2meapp"},
        )

    def test_chat_endpoint_returns_503_on_runtime_error(self):
        self.rag.run.side_effect = RuntimeError("backend unavailable")

        response = self.client.post("/chat", json={"question": "Hi", "history": []})

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "backend unavailable")

    def test_stream_endpoint_returns_error_event_on_runtime_error(self):
        self.rag.stream.side_effect = RuntimeError("stream backend unavailable")

        response = self.client.post("/chat/stream", json={"question": "Help", "history": []})

        self.assertEqual(response.status_code, 200)
        self.assertIn('"type": "error"', response.text)
        self.assertIn("stream backend unavailable", response.text)

    def test_stream_endpoint_returns_ndjson_events(self):
        self.rag.stream.return_value = iter(
            [
                {"type": "meta", "collection": "nx2meapp", "app": "Nx2meApp", "routing": {}, "sources": []},
                {"type": "token", "text": "Step 1"},
                {"type": "done"},
            ]
        )

        response = self.client.post("/chat/stream", json={"question": "Help", "history": []})

        self.assertEqual(response.status_code, 200)
        body = response.text
        self.assertIn('"type": "meta"', body)
        self.assertIn('"text": "Step 1"', body)
        self.assertIn('"type": "done"', body)

    def test_feedback_endpoints_delegate_to_store(self):
        payload = {
            "message_id": "m1",
            "question": "q",
            "answer": "a",
            "created_at": "2026-03-22T19:00:00",
        }

        like_response = self.client.post("/feedback/like", json=payload)
        dislike_response = self.client.post("/feedback/dislike", json=payload)

        self.assertEqual(like_response.status_code, 200)
        self.assertEqual(dislike_response.status_code, 200)
        self.feedback_store.save_like.assert_called_once()
        self.feedback_store.save_dislike.assert_called_once()

    def test_chroma_admin_page_contains_document_browser_controls(self):
        response = self.client.get("/chroma-admin")

        self.assertEqual(response.status_code, 200)
        self.assertIn("One by one", response.text)
        self.assertIn("Previous document", response.text)
        self.assertIn("Loaded page", response.text)


if __name__ == "__main__":
    unittest.main()
