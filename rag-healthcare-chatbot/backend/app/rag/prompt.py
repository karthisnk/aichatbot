import re

from app.config import PROMPT_CHUNK_CHAR_LIMIT, PROMPT_MAX_CHUNKS


class PromptBuilder:
    def build(self, query, chunks, history=None, detailed=False, max_chunks=None, chunk_char_limit=None):
        history = history or []
        history_block = self._build_history_block(history)
        max_chunks = max_chunks or PROMPT_MAX_CHUNKS
        chunk_char_limit = chunk_char_limit or PROMPT_CHUNK_CHAR_LIMIT
        context_block = self._build_context_block(
            chunks[:max_chunks],
            chunk_char_limit=chunk_char_limit,
        )

        if detailed:
            return f"""
You are a healthcare application assistant.

Answer only from the provided context.
The user asked for a detailed explanation, so provide complete step-by-step guidance.
Do not summarize into a short answer.
Capture all important actionable details supported by context, including sequence, options, warnings, and required fields.
Use readable Markdown structure:
- Start with a short heading in bold.
- Use numbered steps for the main flow.
- Under each step, add bullet points for exact actions and clarifications.
- Keep each sentence short and readable.
- If there are alternatives or edge cases, add a separate bullet section.
Do not produce one long paragraph.
Do not mention figure numbers, screenshots, image labels, or references like "see figure".
If some context is missing, explicitly say what is unavailable and continue with what is supported.
If nothing is supported, say:
"I could not find this in the knowledge base. Please check with the L3 administration team."

Previous conversation:
{history_block}

Context:
{context_block}

Current question:
{query}

Answer:
"""

        return f"""
You are a healthcare application assistant.

Answer only from the provided context.
Keep the answer concise, direct, and practical, but include enough detail to be useful.
Rewrite manual-style content into clear user-facing instructions.
Format the main response as short bullet points (2 to 5 bullets).
Do not use generic numbered step-by-step formatting unless the user explicitly asks for steps.
Each bullet should be one practical action or insight, written in plain user language.
Do not mention figure numbers, screenshots, image labels, or references like "see figure" or "shown above".
Make the answer fully understandable on its own, even if the user cannot see the manual images.
When the source mentions a menu or button, describe where to find it in simple words.
Use short paragraphs only when a list is not suitable.
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

    def _build_context_block(self, chunks, chunk_char_limit=PROMPT_CHUNK_CHAR_LIMIT):
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

            formatted_chunks.append(f"{header}\n{self._limit_text(text, chunk_char_limit)}")

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
