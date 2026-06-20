FOLLOWUP_KEYWORDS = (
    "explain", "elaborate", "more detail", "in detail", "clarify",
    "what do you mean", "expand", "simplify", "again", "tell me more",
    "can you explain", "please explain", "go deeper", "break it down",
    "make it clearer", "don't understand", "didn't understand",
    "what does that mean", "say it simply",
)

SUMMARY_KEYWORDS = (
    "summarize", "summarise", "summary", "overview", "brief",
    "short note", "short abt", "short about", "describe the document",
    "what is this document about", "what is the document about",
    "give me a summary", "main points", "key points",
)

PAGE_KEYWORDS = (
    "how many pages", "number of pages", "page count", "total pages",
    "pages in", "pages does", "pages are",
)

WORD_KEYWORDS = (
    "how many words", "word count", "number of words",
)

CHUNK_KEYWORDS = (
    "how many chunks", "number of chunks",
)

WORDS_PER_PAGE_ESTIMATE = 300


def is_followup_request(question: str) -> bool:
    q = question.lower().strip()
    return any(kw in q for kw in FOLLOWUP_KEYWORDS)


def is_summary_request(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in SUMMARY_KEYWORDS)


def is_metadata_request(question: str) -> bool:
    q = question.lower()
    return any(
        kw in q
        for kw in PAGE_KEYWORDS + WORD_KEYWORDS + CHUNK_KEYWORDS
    )


def match_filename_in_question(question: str, filenames: list[str]) -> str | None:
    q = question.lower()
    for name in filenames:
        if name.lower() in q:
            return name
        stem = name.rsplit(".", 1)[0].lower()
        if stem and stem in q:
            return name
    return None


def _estimate_pages(doc: dict) -> int:
    pages = doc.get("page_count") or 0
    if pages > 0:
        return pages
    words = doc.get("word_count") or 0
    if words > 0:
        return max(1, words // WORDS_PER_PAGE_ESTIMATE)
    chunks = doc.get("chunk_count") or 0
    return max(1, chunks) if chunks > 0 else 0


def try_direct_metadata_answer(
    question: str,
    documents: list[dict],
) -> str | None:
    if not documents:
        return None

    q = question.lower()
    target = match_filename_in_question(
        question, [d["filename"] for d in documents]
    )
    docs = (
        [d for d in documents if d["filename"] == target]
        if target
        else documents
    )

    if any(kw in q for kw in PAGE_KEYWORDS):
        lines = []
        for doc in docs:
            pages = _estimate_pages(doc)
            label = "page(s)"
            if doc.get("filetype") == ".docx" and not doc.get("page_count"):
                label = "page(s) (estimated)"
            lines.append(f"**{doc['filename']}**: {pages} {label}")
        return "\n".join(lines)

    if any(kw in q for kw in WORD_KEYWORDS):
        lines = []
        for doc in docs:
            words = doc.get("word_count") or 0
            if words == 0:
                words = (doc.get("chunk_count") or 0) * WORDS_PER_PAGE_ESTIMATE
            lines.append(f"**{doc['filename']}**: {words:,} words")
        return "\n".join(lines)

    if any(kw in q for kw in CHUNK_KEYWORDS):
        lines = []
        for doc in docs:
            chunks = doc.get("chunk_count") or 0
            lines.append(f"**{doc['filename']}**: {chunks} chunks")
        return "\n".join(lines)

    return None


def build_chat_history(messages: list[dict], max_turns: int = 4) -> list[dict]:
    """Return recent chat turns for LLM context (excludes sources footer)."""
    history: list[dict] = []
    for msg in messages[-max_turns * 2 :]:
        content = msg.get("content", "")
        if msg.get("role") == "assistant" and "---\n**Sources**" in content:
            content = content.split("---\n**Sources**")[0].strip()
        history.append({"role": msg["role"], "content": content})
    return history
