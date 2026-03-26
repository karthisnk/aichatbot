import json
import threading
from collections import OrderedDict

from app.config import RETRIEVAL_CACHE_SIZE
from app.config import TOP_K
from app.services.application_router import APP_CATALOG, ApplicationRouter
from app.services.vector_store import VectorStore


class Retriever:
    _retrieval_cache = OrderedDict()
    _cache_lock = threading.Lock()

    def __init__(self):
        self.store = VectorStore()
        self.router = ApplicationRouter()

    def retrieve(self, query, history=None, where=None, top_k=None):
        history = history or []
        cache_key = self._build_cache_key(query, history, where, top_k)
        cached = self._get_cached_result(cache_key)
        if cached is not None:
            return cached

        route = self._resolve_route(query, history, where)
        metadata_filters = dict(where or {})
        metadata_filters.pop("app", None)
        metadata_filters.pop("collection", None)
        k = int(top_k or TOP_K)
        if k < 1:
            k = TOP_K
        chunks = self.store.search(
            query,
            collection_name=route["collection"],
            k=k,
            where=metadata_filters,
        )
        result = (route, chunks)
        self._store_cached_result(cache_key, result)
        return result

    def warmup(self):
        self.router.warmup()
        self.store.warmup(
            item["collection"] for item in APP_CATALOG.values()
        )

    def _resolve_route(self, query, history, where):
        explicit_key = self._resolve_explicit_key(where)
        if explicit_key:
            item = APP_CATALOG[explicit_key]
            return {
                "app": item["app"],
                "collection": item["collection"],
                "reason": "filter",
                "method": "explicit",
                "agent_reason": "Matched by selected scope.",
                "confidence": 1.0,
            }

        return self.router.resolve_collection(query, history=history, filters=where)

    def _resolve_explicit_key(self, where):
        if not where:
            return None

        explicit_app = self._normalize_key(where.get("app"))
        if explicit_app in APP_CATALOG:
            return explicit_app

        explicit_collection = self._normalize_key(where.get("collection"))
        if explicit_collection in APP_CATALOG:
            return explicit_collection

        return None

    def _build_cache_key(self, query, history, where, top_k=None):
        history_text = " || ".join(
            f"{(turn.get('role') or '').strip().lower()}:{self._normalize_text(turn.get('text') or '')}"
            for turn in history[-4:]
            if (turn.get("text") or "").strip()
        )
        where_text = json.dumps(where or {}, sort_keys=True, ensure_ascii=False)
        return f"{self._normalize_text(query)}::{history_text}::{where_text}::k={int(top_k or TOP_K)}"

    def _normalize_text(self, value):
        return " ".join(str(value or "").strip().lower().split())

    def _normalize_key(self, value):
        return "".join(ch for ch in str(value or "").strip().lower() if ch.isalnum())

    def _get_cached_result(self, key):
        cache = self.__class__._retrieval_cache
        with self.__class__._cache_lock:
            if key not in cache:
                return None
            value = cache.pop(key)
            cache[key] = value
            route, chunks = value
            return dict(route), [dict(chunk) for chunk in chunks]

    def _store_cached_result(self, key, value):
        cache = self.__class__._retrieval_cache
        with self.__class__._cache_lock:
            if key in cache:
                cache.pop(key)

            route, chunks = value
            cache[key] = (dict(route), [dict(chunk) for chunk in chunks])
            while len(cache) > RETRIEVAL_CACHE_SIZE:
                cache.popitem(last=False)
