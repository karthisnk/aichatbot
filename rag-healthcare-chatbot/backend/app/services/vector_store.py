import json
import re
from itertools import zip_longest
from pathlib import Path

from app.config import PROCESSED_DATA_DIR, TOP_K
from app.services.chroma_client import get_chroma_client
from app.services.embedder import Embedder


class VectorStore:
    _chunk_cache = {}
    _image_query_terms = {
        "image",
        "images",
        "figure",
        "fig",
        "screenshot",
        "screen",
        "card",
        "diagram",
        "chart",
    }

    def __init__(self):
        self.client = get_chroma_client()
        self.embedding = Embedder().get_embedding_function()

    def _get_collection(self, collection_name):
        try:
            return self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding,
            )
        except Exception as exc:
            raise RuntimeError(
                f"The ChromaDB collection '{collection_name}' is missing. "
                "Run `python backend\\scripts\\run_chunking.py --ingest-chroma` "
                "or `python backend\\scripts\\build_index.py` to ingest the documents."
            ) from exc

    def warmup(self, collection_names):
        for collection_name in collection_names:
            try:
                self._get_collection(collection_name)
            except RuntimeError:
                continue

    def search(self, query_text, collection_name, k=TOP_K, where=None):
        if not query_text or not query_text.strip():
            return []

        collection = self._get_collection(collection_name)
        normalized_query = self._normalize_search_text(query_text)

        try:
            results = collection.query(
                query_texts=[query_text],
                n_results=max(k * 5, 10),
                where=where or None,
            )
        except Exception as exc:
            raise RuntimeError("Failed to query ChromaDB for relevant documents.") from exc

        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]

        if not documents:
            return []

        formatted_results = []
        for index, (document, metadata) in enumerate(
            zip_longest(documents, metadatas, fillvalue=None)
        ):
            if not document:
                continue
            item = {"text": document}
            if metadata:
                item.update(metadata)
            item["collection"] = collection_name
            self._enrich_image_metadata(item, collection_name)
            item["_semantic_rank"] = index
            formatted_results.append(item)

        lexical_results = self._search_processed_chunks(
            normalized_query,
            collection_name=collection_name,
            limit=max(k * 5, 10),
            where=where,
        )
        merged_results = self._merge_results(formatted_results, lexical_results)
        reranked = self._rerank_results(normalized_query, merged_results)
        return reranked[:k]

    def _search_processed_chunks(self, query_text, collection_name, limit, where=None):
        chunks = self._load_processed_chunks(collection_name)
        if not chunks:
            return []

        matches = []
        for index, chunk in enumerate(chunks):
            if not self._matches_filters(chunk, where):
                continue

            item = {
                "text": self._build_chunk_document(chunk),
                "collection": collection_name,
                "_semantic_rank": 10_000 + index,
            }
            item.update(self._build_chunk_metadata(chunk, collection_name=collection_name))
            score = self._score_result(query_text, item)
            if score <= 0:
                continue
            item["_lexical_score"] = score
            matches.append(item)

        matches.sort(
            key=lambda item: (-item.get("_lexical_score", 0), item.get("_semantic_rank", 0))
        )
        return matches[:limit]

    def _load_processed_chunks(self, collection_name):
        cache = self.__class__._chunk_cache
        if collection_name in cache:
            return cache[collection_name]

        app_dir = Path(PROCESSED_DATA_DIR) / collection_name
        chunks = []
        if app_dir.exists():
            for jsonl_path in sorted(app_dir.glob("*_chunks.jsonl")):
                with open(jsonl_path, "r", encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            chunks.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

        cache[collection_name] = chunks
        return chunks

    def _matches_filters(self, chunk, where):
        if not where:
            return True

        for key, value in where.items():
            if str(chunk.get(key) or "").lower() != str(value).lower():
                return False
        return True

    def _build_chunk_document(self, chunk):
        parts = [
            str(chunk.get("section") or "").strip(),
            str(chunk.get("text") or "").strip(),
        ]
        keywords = chunk.get("keywords") or []
        if keywords:
            parts.append("Keywords: " + ", ".join(str(keyword) for keyword in keywords))
        return "\n\n".join(part for part in parts if part)

    def _build_chunk_metadata(self, chunk, collection_name):
        metadata = {
            "app": str(chunk.get("app") or ""),
            "domain": str(chunk.get("domain") or ""),
            "type": str(chunk.get("type") or ""),
            "section": str(chunk.get("section") or ""),
        }
        if chunk.get("page") is not None:
            metadata["page"] = int(chunk["page"])
        if chunk.get("image_path") is not None:
            metadata["image_path"] = str(chunk.get("image_path"))
            self._enrich_image_metadata(metadata, collection_name)
        keywords = chunk.get("keywords") or []
        if keywords:
            metadata["keywords"] = ", ".join(str(keyword) for keyword in keywords)
        return metadata

    def _enrich_image_metadata(self, item, collection_name):
        raw_path = str(item.get("image_path") or "").strip()
        if not raw_path:
            return

        relative_path = self._to_relative_image_path(raw_path, collection_name)
        if not relative_path:
            return

        item["image_path"] = relative_path
        item["image_url"] = f"/kb-images/{relative_path}"

    def _to_relative_image_path(self, raw_path, collection_name):
        posix = raw_path.replace("\\", "/").strip()
        if not posix:
            return ""

        if "/processed/" in posix:
            relative = posix.split("/processed/", 1)[1].lstrip("/")
        elif "/images/" in posix:
            file_name = posix.rsplit("/", 1)[-1]
            relative = f"{collection_name}/images/{file_name}" if file_name else ""
        else:
            file_name = posix.rsplit("/", 1)[-1]
            relative = f"{collection_name}/images/{file_name}" if file_name else ""

        if not relative:
            return ""

        parts = [part for part in relative.split("/") if part not in {"", ".", ".."}]
        if len(parts) < 3:
            return ""
        if parts[1] != "images":
            return ""

        return "/".join(parts)

    def _merge_results(self, semantic_results, lexical_results):
        merged = []
        seen = set()

        for item in semantic_results + lexical_results:
            key = (
                item.get("section"),
                item.get("page"),
                self._normalize_search_text(item.get("text", ""))[:240],
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)

        return merged

    def _rerank_results(self, query_text, results):
        return sorted(
            results,
            key=lambda item: (
                -self._score_result(query_text, item),
                item.get("_semantic_rank", 0),
            ),
        )

    def _score_result(self, query_text, item):
        text = self._normalize_search_text(item.get("text", ""))
        section = self._normalize_search_text(item.get("section", ""))
        chunk_type = self._normalize_search_text(item.get("type", ""))
        keywords = self._normalize_search_text(item.get("keywords", ""))
        combined = " ".join(part for part in [section, keywords, text] if part)

        query_terms = self._expand_query_terms(query_text)
        if not query_terms:
            return 0

        score = 0
        for term in query_terms:
            if term in section:
                score += 8
            if term in keywords:
                score += 6
            if term in text:
                score += 4
            if term in combined:
                score += 2

        if chunk_type == "table" and any(term in {"password", "login", "log in"} for term in query_terms):
            score += 2

        if "reset password" in combined and ("reset" in query_terms or "password" in query_terms):
            score += 8
        if "change password" in combined and ("change" in query_terms or "password" in query_terms):
            score += 8
        if "logging into" in combined or "log into the portal" in combined:
            if any(term in {"login", "log in", "sign in"} for term in query_terms):
                score += 8
        if "mfa" in combined or "multi factor authentication" in combined:
            if "mfa" in query_terms or "authentication" in query_terms:
                score += 6

        if chunk_type == "image" and query_terms.intersection(self._image_query_terms):
            score += 14

        return score

    def _expand_query_terms(self, query_text):
        normalized = self._normalize_search_text(query_text)
        terms = set()

        for phrase in [
            "login",
            "log in",
            "sign in",
            "password",
            "reset password",
            "change password",
            "forgot password",
            "mfa",
            "authentication",
            "figure",
            "fig",
            "image",
            "screenshot",
            "screen",
            "card",
            "diagram",
            "chart",
        ]:
            if phrase in normalized:
                terms.add(phrase)

        for token in re.findall(r"[a-z0-9]+", normalized):
            if len(token) >= 3:
                terms.add(token)

        if "login" in terms:
            terms.update({"log in", "sign in"})
        if "log" in terms and "in" in normalized:
            terms.update({"login", "log in", "sign in"})
        if "password" in terms:
            terms.update({"reset password", "change password", "forgot password"})
        if "reset" in terms and "password" in normalized:
            terms.update({"reset password", "change password"})

        return terms

    def _normalize_search_text(self, value):
        normalized = str(value or "").lower()
        normalized = normalized.replace("â€™", "'").replace("’", "'")
        normalized = normalized.replace("â€¢", " ").replace("•", " ")
        normalized = normalized.replace("log into", "login")
        normalized = normalized.replace("logging into", "login")
        normalized = normalized.replace("log in", "login")
        normalized = normalized.replace("sign in", "login")
        normalized = re.sub(r"[^a-z0-9\s]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized
