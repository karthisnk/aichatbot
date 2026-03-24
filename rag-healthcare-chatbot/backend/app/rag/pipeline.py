import json
import threading
from collections import OrderedDict

from app.config import ANSWER_CACHE_SIZE
from app.rag.prompt import PromptBuilder
from app.rag.retriever import Retriever
from app.services.llm import LLM


class RAGPipeline:
    _answer_cache = OrderedDict()
    _cache_lock = threading.Lock()

    def __init__(self):
        self.retriever = Retriever()
        self.prompt_builder = PromptBuilder()
        self.llm = LLM()

    def warmup(self):
        self.retriever.warmup()
        self.llm.warmup()

    def run(self, query, history=None, where=None):
        history = history or []
        cache_key = self._build_cache_key(query, history, where)
        cached = self._get_cached_answer(cache_key)
        if cached is not None:
            return cached

        retrieval_query, route, chunks = self._prepare_retrieval(query, history, where)

        if not chunks:
            result = {
                "answer": "I could not find relevant information in the knowledge base.",
                "sources": [],
                "collection": route["collection"],
                "app": route["app"],
                "routing": route,
            }
            self._store_cached_answer(cache_key, result)
            return result

        prompt = self.prompt_builder.build(query, chunks, history=history)
        answer = self.llm.generate(prompt)
        result = {
            "answer": answer,
            "sources": chunks,
            "collection": route["collection"],
            "app": route["app"],
            "routing": route,
        }
        self._store_cached_answer(cache_key, result)
        return result

    def stream(self, query, history=None, where=None):
        history = history or []
        cache_key = self._build_cache_key(query, history, where)
        cached = self._get_cached_answer(cache_key)
        if cached is not None:
            yield {
                "type": "meta",
                "collection": cached["collection"],
                "app": cached["app"],
                "routing": cached["routing"],
                "sources": cached["sources"],
            }
            yield {"type": "token", "text": cached["answer"]}
            yield {"type": "done"}
            return

        retrieval_query, route, chunks = self._prepare_retrieval(query, history, where)

        if not chunks:
            result = {
                "answer": "I could not find this in the knowledge base. Please check with the L3 administration team.",
                "sources": [],
                "collection": route["collection"],
                "app": route["app"],
                "routing": route,
            }
            self._store_cached_answer(cache_key, result)
            yield {
                "type": "meta",
                "collection": route["collection"],
                "app": route["app"],
                "routing": route,
                "sources": [],
            }
            yield {
                "type": "token",
                "text": result["answer"],
            }
            yield {"type": "done"}
            return

        prompt = self.prompt_builder.build(query, chunks, history=history)
        yield {
            "type": "meta",
            "collection": route["collection"],
            "app": route["app"],
            "routing": route,
            "sources": chunks,
        }

        answer_parts = []
        for text in self.llm.stream_generate(prompt):
            answer_parts.append(text)
            yield {"type": "token", "text": text}

        self._store_cached_answer(
            cache_key,
            {
                "answer": "".join(answer_parts),
                "sources": chunks,
                "collection": route["collection"],
                "app": route["app"],
                "routing": route,
            },
        )
        yield {"type": "done"}

    def _prepare_retrieval(self, query, history, where):
        retrieval_query = self._build_retrieval_query(query, history)
        route, chunks = self.retriever.retrieve(
            retrieval_query,
            history=history,
            where=where,
        )
        return retrieval_query, route, chunks

    def _build_retrieval_query(self, query, history):
        recent_user_turns = []

        for turn in history[-6:]:
            role = (turn.get("role") or "").strip().lower()
            text = (turn.get("text") or "").strip()
            if role == "user" and text:
                recent_user_turns.append(text)

        if not recent_user_turns:
            return query

        recent_context = " ".join(recent_user_turns[-3:])
        return f"{recent_context}\n{query}".strip()

    def _build_cache_key(self, query, history, where):
        history_text = " || ".join(
            f"{(turn.get('role') or '').strip().lower()}:{self._normalize_text(turn.get('text') or '')}"
            for turn in history[-4:]
            if (turn.get("text") or "").strip()
        )
        where_text = json.dumps(where or {}, sort_keys=True, ensure_ascii=False)
        return f"{self._normalize_text(query)}::{history_text}::{where_text}"

    def _normalize_text(self, value):
        return " ".join(str(value or "").strip().lower().split())

    def _get_cached_answer(self, key):
        cache = self.__class__._answer_cache
        with self.__class__._cache_lock:
            if key not in cache:
                return None
            value = cache.pop(key)
            cache[key] = value
            return dict(value) if isinstance(value, dict) else value

    def _store_cached_answer(self, key, value):
        cache = self.__class__._answer_cache
        with self.__class__._cache_lock:
            if key in cache:
                cache.pop(key)
            cache[key] = dict(value) if isinstance(value, dict) else value
            while len(cache) > ANSWER_CACHE_SIZE:
                cache.popitem(last=False)
