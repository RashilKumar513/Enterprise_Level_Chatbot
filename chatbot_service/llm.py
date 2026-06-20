import ollama

from chatbot_service.grounding import (
    answer_is_grounded,
    detect_outsourcing_phrases,
)
from chatbot_service.query_handler import is_followup_request, is_summary_request
from shared.config import OLLAMA_MODEL, setup_logging

logger = setup_logging(__name__)

NOT_FOUND_MESSAGE = (
    "I could not find this information in the uploaded documents."
)


class LLM:
    def __init__(self, model: str = OLLAMA_MODEL) -> None:
        self.model = model

    def generate(
        self,
        question: str,
        context: str,
        sources: list[dict],
        chat_history: list[dict] | None = None,
    ) -> str:
        if not context.strip() or not sources:
            return NOT_FOUND_MESSAGE

        source_excerpts = "\n\n".join(
            f"[From {s['filename']}]: {s['chunk_text']}"
            for s in sources
        )

        if is_followup_request(question):
            task = (
                "The user wants MORE DETAIL about your previous answer. "
                "Use ONLY the SOURCE EXCERPTS and CHAT HISTORY below. "
                "Do NOT add any new facts not found in those excerpts."
            )
        elif is_summary_request(question):
            task = (
                "Summarize using ONLY the SOURCE EXCERPTS below. "
                "4-6 sentences. Every fact must come from the excerpts."
            )
        else:
            task = (
                "Answer the question using ONLY the SOURCE EXCERPTS below. "
                "1-4 sentences. Copy facts exactly as stated in the excerpts."
            )

        system_prompt = f"""You are DocumentBrain — a STRICT document-only Q&A assistant.

ABSOLUTE RULES (violating any rule is forbidden):
1. You may ONLY use facts written in the SOURCE EXCERPTS below.
2. You have ZERO outside knowledge. Pretend you know nothing except the excerpts.
3. Do NOT guess, infer, assume, or add information not explicitly in the excerpts.
4. Do NOT use phrases like "generally", "typically", "as an AI", or "based on my knowledge".
5. If the excerpts do not contain the answer, reply with EXACTLY:
   "{NOT_FOUND_MESSAGE}"
6. Never mention Wikipedia, the internet, or your training data.

{task}"""

        history_block = ""
        if chat_history and is_followup_request(question):
            lines = []
            for msg in chat_history[-4:]:
                role = msg.get("role", "user").upper()
                lines.append(f"{role}: {msg.get('content', '')[:500]}")
            history_block = "\n\nCHAT HISTORY:\n" + "\n".join(lines)

        user_prompt = f"""SOURCE EXCERPTS (your ONLY source of truth):
{source_excerpts}
{history_block}

DOCUMENT METADATA (for page/word counts only):
{context.split('=== DOCUMENT CONTENT ===')[0] if '=== DOCUMENT CONTENT ===' in context else ''}

QUESTION: {question}

Answer using ONLY the SOURCE EXCERPTS above. If not found, say exactly: "{NOT_FOUND_MESSAGE}"
ANSWER:"""

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                options={
                    "temperature": 0.0,
                    "top_p": 0.1,
                    "num_predict": 400,
                },
            )
            answer = response["message"]["content"].strip()

            # Clean common prefixes
            for prefix in (
                "Based on the provided context,",
                "Based on the context,",
                "Based on the source excerpts,",
                "According to the document,",
                "According to the excerpts,",
            ):
                if answer.lower().startswith(prefix.lower()):
                    answer = answer[len(prefix):].strip()

            # Reject outsourced answers
            if detect_outsourcing_phrases(answer):
                logger.warning("Rejected outsourced answer")
                return NOT_FOUND_MESSAGE

            if NOT_FOUND_MESSAGE.lower() in answer.lower():
                return NOT_FOUND_MESSAGE

            if not answer_is_grounded(answer, sources):
                logger.warning("Answer failed grounding check — rejecting")
                return NOT_FOUND_MESSAGE

            logger.info("Generated grounded answer")
            return answer

        except Exception as exc:
            logger.error("Ollama request failed: %s", exc)
            return (
                f"Could not connect to Ollama. "
                f"Ensure Ollama is running and model '{self.model}' is installed. "
                f"Error: {exc}"
            )
