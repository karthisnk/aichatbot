import unittest
from unittest.mock import patch

from app.services import chroma_admin
from app.services.document_pipeline import DocumentProcessingPipeline


class FakeCollection:
    def __init__(self, name="demo", count=3, metadata=None, items=None):
        self.name = name
        self._count = count
        self.metadata = metadata or {"source": "test"}
        self._items = items or {
            "ids": ["a", "b"],
            "documents": ["doc one", "doc two"],
            "metadatas": [{"domain": "patient"}, {"domain": "alerts", "page": 7}],
            "embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
        }

    def count(self):
        return self._count

    def get(self, limit=None, offset=None, include=None):
        start = offset or 0
        end = start + (limit or len(self._items["ids"]))
        return {
            "ids": self._items["ids"][start:end],
            "documents": self._items["documents"][start:end],
            "metadatas": self._items["metadatas"][start:end],
            "embeddings": self._items["embeddings"][start:end],
        }

    def peek(self, limit=5):
        return self.get(limit=limit, offset=0, include=None)


class FakeClient:
    def __init__(self, collection):
        self.collection = collection

    def list_collections(self):
        return [self.collection]

    def get_collection(self, name):
        return self.collection


class ChromaAdminTests(unittest.TestCase):
    def test_build_records_shapes_documents_metadata_and_embeddings(self):
        items = {
            "ids": ["doc-1"],
            "documents": ["hello world"],
            "metadatas": [{"section": "General", "page": 2}],
            "embeddings": [[1.0, 2.0, 3.0, 4.0]],
        }

        records = chroma_admin._build_records(items)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["id"], "doc-1")
        self.assertEqual(records[0]["document_length"], 11)
        self.assertEqual(records[0]["metadata_keys"], ["page", "section"])
        self.assertEqual(records[0]["embedding_size"], 4)
        self.assertEqual(records[0]["embedding_preview"], [1.0, 2.0, 3.0, 4.0])

    def test_get_collection_overview_returns_summary(self):
        collection = FakeCollection()

        with patch("app.services.chroma_admin._get_collection", return_value=collection):
            result = chroma_admin.get_collection_overview("demo", sample_size=10)

        self.assertEqual(result["collection"]["name"], "demo")
        self.assertEqual(result["summary"]["sample_size"], 2)
        self.assertEqual(result["summary"]["documents_with_metadata"], 2)
        self.assertEqual(result["summary"]["embedding_size"], 3)
        self.assertIn("domain", result["summary"]["metadata_keys"])

    def test_get_collection_records_returns_pagination_flags(self):
        collection = FakeCollection(
            count=5,
            items={
                "ids": ["a", "b", "c"],
                "documents": ["one", "two", "three"],
                "metadatas": [{}, {}, {}],
                "embeddings": [[0.1], [0.2], [0.3]],
            },
        )

        with patch("app.services.chroma_admin._get_collection", return_value=collection):
            result = chroma_admin.get_collection_records("demo", offset=1, limit=2)

        self.assertEqual(result["offset"], 1)
        self.assertEqual(result["limit"], 2)
        self.assertEqual(result["returned"], 2)
        self.assertTrue(result["has_next_page"])
        self.assertEqual([record["id"] for record in result["records"]], ["b", "c"])

    def test_list_collections_returns_payloads(self):
        collection = FakeCollection(name="alpha", count=9, metadata={"owner": "qa"})
        client = FakeClient(collection)

        with patch("app.services.chroma_admin.get_chroma_client", return_value=client):
            result = chroma_admin.list_collections()

        self.assertEqual(result, [{"name": "alpha", "count": 9, "metadata": {"owner": "qa"}}])

    def test_image_chunk_prefers_extracted_text_with_context(self):
        pipeline = DocumentProcessingPipeline()
        section = {
            "app_name": "DemoApp",
            "domain": "patient",
            "section_title": "Vitals Overview",
            "page_number": 1,
        }
        image = {
            "extracted_text": "Blood Pressure 120/80",
            "description": "Vitals Overview illustration, page 1",
            "image_path": "demo.png",
        }

        text = pipeline._build_image_chunk_text(image, section)

        self.assertIn("Blood Pressure 120/80", text)
        self.assertIn("Image context:", text)


if __name__ == "__main__":
    unittest.main()
