import json

import requests

from app.config import (
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_TIMEOUT_SECONDS,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_URL,
)


class LLM:
    _session = requests.Session()

    def _payload(self, prompt, stream, options=None):
        payload = {
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": stream,
            "keep_alive": OLLAMA_KEEP_ALIVE,
            "options": {
                "num_predict": LLM_MAX_TOKENS,
                "temperature": 0.1,
            },
        }
        if options:
            payload["options"].update(options)
        return payload

    def generate(self, prompt, options=None):
        try:
            response = self.__class__._session.post(
                OLLAMA_URL,
                json=self._payload(prompt, stream=False, options=options),
                timeout=LLM_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json()["response"]
        except requests.RequestException as exc:
            raise RuntimeError("Failed to generate a response from the LLM service.") from exc

    def stream_generate(self, prompt, options=None):
        try:
            with self.__class__._session.post(
                OLLAMA_URL,
                json=self._payload(prompt, stream=True, options=options),
                timeout=LLM_TIMEOUT_SECONDS,
                stream=True,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    payload = json.loads(line)

                    text = payload.get("response") or ""
                    if text:
                        yield text

                    if payload.get("done"):
                        break
        except requests.RequestException as exc:
            raise RuntimeError("Failed to generate a response from the LLM service.") from exc

    def warmup(self):
        try:
            response = self.__class__._session.post(
                OLLAMA_URL,
                json=self._payload(
                    "Reply with OK only.",
                    stream=False,
                    options={"num_predict": 1, "temperature": 0},
                ),
                timeout=30,
            )
            response.raise_for_status()
        except requests.RequestException:
            # Warmup is best-effort only. The app should still start if Ollama is not ready yet.
            return
