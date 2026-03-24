import re

from app.config import PROMPT_CHUNK_CHAR_LIMIT, PROMPT_MAX_CHUNKS


class PromptBuilder:
    def build(self, query, chunks, history=None):
        history = history or []
        history_block = self._build_history_block(history)
        context_block = self._build_context_block(chunks[:PROMPT_MAX_CHUNKS])

        return f"""
You are a healthcare application assistant.

Answer only from the provided context.
Keep the answer concise, direct, and practical, but include enough detail to be useful.
Use numbered steps when the context describes a procedure.
Rewrite manual-style content into clear user-facing instructions.
Do not mention figure numbers, screenshots, image labels, or references like "see figure" or "shown above".
Make the answer fully understandable on its own, even if the user cannot see the manual images.
When the source mentions a menu or button, describe where to find it in simple words.
Use short paragraphs or short lists only when needed.
If some details are especially important, highlight only a few key words or phrases using Markdown bold like **this**.
Do not overuse bold formatting.
If the answer is not supported by the context, say:
"I could not find this in the knowledge base. Please check with the L3 administration team."
If the context is partial, answer only what is supported and then say:
"For anything beyond this, please check with the L3 administration team."

Previous conversation:
{history_block}

Context:
{context_block}

Current question:
{query}

Answer:
"""

    def _build_history_block(self, history):
        if not history:
            return "No previous conversation."

        formatted_turns = []
        for turn in history[-2:]:
            role = (turn.get("role") or "user").strip().title()
            text = (turn.get("text") or "").strip()
            if text:
                formatted_turns.append(f"{role}: {self._limit_text(text, 140)}")

        return "\n".join(formatted_turns) if formatted_turns else "No previous conversation."

    def _build_context_block(self, chunks):
        if not chunks:
            return "No context found."

        formatted_chunks = []
        for index, chunk in enumerate(chunks, start=1):
            text = self._clean_chunk_text(chunk.get("text", ""))
            section = chunk.get("section") or "General"
            domain = chunk.get("domain") or "general"
            chunk_type = chunk.get("type") or "text"
            page = chunk.get("page")

            header = f"[{index}] section={section} | domain={domain} | type={chunk_type}"
            if page is not None:
                header += f" | page={page}"

            formatted_chunks.append(f"{header}\n{self._limit_text(text, PROMPT_CHUNK_CHAR_LIMIT)}")

        return "\n\n".join(formatted_chunks)

    def _clean_chunk_text(self, text):
        cleaned = text or ""
        cleaned = re.sub(r"\bfigure\s+\d+(?:[-.]\d+)?[a-z]?\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bfig\.\s*\d+(?:[-.]\d+)?[a-z]?\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\n\s*Domain:\s.*", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"\n\s*Type:\s.*", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"\n\s*Keywords:\s.*", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"\n\s*Image path:\s.*", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def _limit_text(self, text, limit):
        normalized = (text or "").strip()
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3].rstrip() + "..."
