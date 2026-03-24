import json
import threading
from collections import OrderedDict
import re

import requests

from app.config import (
    OLLAMA_KEEP_ALIVE,
    OLLAMA_URL,
    ROUTER_CACHE_SIZE,
    ROUTER_MODEL,
    ROUTER_TIMEOUT_SECONDS,
)


APP_CATALOG = {
    "nx2meapp": {
        "app": "Nx2meApp",
        "collection": "nx2meapp",
        "summary": (
            "Patient-facing Nx2me application. Topics include iPad setup, ConNxBox, Wi-Fi, "
            "cycler sync, alarms, cautions, messages, flowsheets, and treatment status."
        ),
    },
    "kinexushhd": {
        "app": "KINEXUSHHD",
        "collection": "kinexushhd",
        "summary": (
            "KINEXUS HHD provider portal. Topics include provider portal login, MFA, "
            "clinic overview, therapy gaps, first 90 days, patients, prescriptions, vitals, and user creation."
        ),
    },
}

ROUTING_HINTS = {
    "nx2meapp": (
        "nx2me",
        "connxbox",
        "cycler",
        "ipad",
        "flowsheet",
        "treatment status",
        "nxstage router",
        "nxstagerouter",
    ),
    "kinexushhd": (
        "kinexus",
        "provider portal",
        "therapy gap",
        "first 90 days",
        "mfa",
        "clinic overview",
        "provider",
        "vitals",
    ),
}

APP_ALIASES = {
    "nx2meapp": ("nx2meapp", "nx2me app", "nx2me"),
    "kinexushhd": ("kinexushhd", "kinexus hhd", "kinexus"),
}


class ApplicationRouter:
    _route_cache = OrderedDict()
    _cache_lock = threading.Lock()
    _session = requests.Session()

    def resolve_collection(self, query, history=None, filters=None):
        filters = filters or {}
        history = history or []

        explicit_route = self._resolve_explicit_route(filters)
        if explicit_route:
            return explicit_route

        heuristic_route = self._resolve_heuristic_route(query, history)
        if heuristic_route:
            cache_key = self._build_cache_key(query, history)
            self._store_cached_route(cache_key, heuristic_route)
            return heuristic_route

        cache_key = self._build_cache_key(query, history)
        cached = self._get_cached_route(cache_key)
        if cached is not None:
            cached_route = dict(cached)
            cached_route["reason"] = "cache"
            return cached_route

        decision = self._run_routing_agent(query, history)
        if decision:
            self._store_cached_route(cache_key, decision)
            return decision

        return self._fallback_route()

    def warmup(self):
        try:
            response = self.__class__._session.post(
                OLLAMA_URL,
                json={
                    "model": ROUTER_MODEL,
                    "prompt": (
                        'Return strict JSON only: {"app_key":"kinexushhd","reason":"warmup","confidence":1}'
                    ),
                    "stream": False,
                    "keep_alive": OLLAMA_KEEP_ALIVE,
                    "format": "json",
                    "options": {
                        "num_predict": 20,
                        "temperature": 0,
                    },
                },
                timeout=min(10, ROUTER_TIMEOUT_SECONDS + 2),
            )
            response.raise_for_status()
        except requests.RequestException:
            return

    def _resolve_explicit_route(self, filters):
        explicit_app = self._normalize_key(filters.get("app"))
        if explicit_app in APP_CATALOG:
            return self._build_route(explicit_app, reason="filter", method="explicit")

        explicit_collection = self._normalize_key(filters.get("collection"))
        if explicit_collection in APP_CATALOG:
            return self._build_route(explicit_collection, reason="filter", method="explicit")

        return None

    def _run_routing_agent(self, query, history):
        history_text = self._format_history(history)
        catalog_text = self._format_catalog()

        prompt = f"""
Route this healthcare support question to exactly one application.

{catalog_text}

History:
{history_text}

Question:
{query}

Return strict JSON only:
{{
  "app_key": "nx2meapp or kinexushhd",
  "reason": "short reason",
  "confidence": 0.0
}}

Rules:
- Pick the best app from the catalog.
- Keep reason very short.
- app_key must be exactly one of: nx2meapp, kinexushhd
""".strip()

        try:
            response = self.__class__._session.post(
                OLLAMA_URL,
                json={
                    "model": ROUTER_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": OLLAMA_KEEP_ALIVE,
                    "format": "json",
                    "options": {
                        "num_predict": 24,
                        "temperature": 0,
                    },
                },
                timeout=ROUTER_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            payload = response.json()
            parsed = self._parse_agent_output(payload.get("response", ""))
        except requests.RequestException:
            return None

        app_key = self._normalize_key(parsed.get("app_key"))
        if app_key not in APP_CATALOG:
            return None

        route = self._build_route(app_key, reason="question", method="agent")
        route["agent_reason"] = str(parsed.get("reason") or "").strip() or "Matched by routing agent."
        confidence = parsed.get("confidence")
        try:
            route["confidence"] = float(confidence)
        except (TypeError, ValueError):
            route["confidence"] = None
        return route

    def _resolve_heuristic_route(self, query, history):
        query_text = self._normalize_text(query)
        history_text = self._normalize_text(
            " ".join(
                (turn.get("text") or "").strip()
                for turn in history[-4:]
                if (turn.get("text") or "").strip()
            )
        )
        combined = f"{history_text} {query_text}".strip()
        if not combined:
            return None

        direct_query_matches = self._find_direct_app_matches(query_text)
        if len(direct_query_matches) == 1:
            app_key = next(iter(direct_query_matches))
            route = self._build_route(app_key, reason="keyword", method="heuristic")
            route["agent_reason"] = "Matched by direct application name in the question."
            route["confidence"] = 0.99
            return route

        direct_history_matches = self._find_direct_app_matches(history_text)
        if len(direct_history_matches) == 1:
            app_key = next(iter(direct_history_matches))
            route = self._build_route(app_key, reason="history", method="heuristic")
            route["agent_reason"] = "Matched by direct application name in recent history."
            route["confidence"] = 0.9
            return route

        scores = {}
        for app_key, hints in ROUTING_HINTS.items():
            score = 0
            for hint in hints:
                if hint in combined:
                    score += 2 if hint in query_text else 1
            if score:
                scores[app_key] = score

        if not scores:
            return None

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
            return None

        app_key, score = ranked[0]
        route = self._build_route(app_key, reason="keyword", method="heuristic")
        route["agent_reason"] = "Matched by offline keyword routing."
        route["confidence"] = min(0.99, 0.55 + (score * 0.1))
        return route

    def _find_direct_app_matches(self, text):
        matches = set()
        for app_key, aliases in APP_ALIASES.items():
            for alias in aliases:
                pattern = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
                if re.search(pattern, text):
                    matches.add(app_key)
                    break
        return matches

    def _parse_agent_output(self, text):
        raw = (text or "").strip()
        if not raw:
            return {}

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            if not match:
                return {}
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}

    def _format_catalog(self):
        lines = []
        for key, item in APP_CATALOG.items():
            lines.append(f"- {key}: {item['summary']}")
        return "\n".join(lines)

    def _format_history(self, history):
        if not history:
            return "No previous conversation."

        lines = []
        for turn in history[-3:]:
            role = (turn.get("role") or "user").strip().lower()
            text = (turn.get("text") or "").strip()
            if text:
                lines.append(f"{role}: {self._limit_text(text, 120)}")
        return "\n".join(lines) if lines else "No previous conversation."

    def _limit_text(self, text, limit):
        normalized = (text or "").strip()
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3].rstrip() + "..."

    def _build_route(self, key, reason, method):
        app = APP_CATALOG[key]
        return {
            "app": app["app"],
            "collection": app["collection"],
            "reason": reason,
            "method": method,
        }

    def _fallback_route(self):
        route = self._build_route("kinexushhd", reason="fallback", method="fallback")
        route["agent_reason"] = "Routing agent could not make a structured decision, so the fallback collection was used."
        route["confidence"] = None
        return route

    def _normalize_key(self, value):
        return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())

    def _normalize_text(self, value):
        return re.sub(r"\s+", " ", str(value or "").strip().lower())

    def _build_cache_key(self, query, history):
        history_text = " || ".join(
            f"{(turn.get('role') or '').strip().lower()}:{self._normalize_text(turn.get('text') or '')}"
            for turn in history[-4:]
            if (turn.get("text") or "").strip()
        )
        return f"{self._normalize_text(query)}::{history_text}"

    def _get_cached_route(self, key):
        cache = self.__class__._route_cache
        with self.__class__._cache_lock:
            if key not in cache:
                return None
            route = cache.pop(key)
            cache[key] = route
            return dict(route)

    def _store_cached_route(self, key, route):
        cache = self.__class__._route_cache
        with self.__class__._cache_lock:
            if key in cache:
                cache.pop(key)
            cache[key] = dict(route)
            while len(cache) > ROUTER_CACHE_SIZE:
                cache.popitem(last=False)
