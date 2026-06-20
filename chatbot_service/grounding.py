"""Verify answers stay grounded in retrieved document chunks."""

import re

NOT_FOUND_PHRASE = "could not find this information in the uploaded documents"

# Common signs the model is using outside knowledge
OUTSOURCING_PHRASES = (
    "as an ai",
    "as a language model",
    "i don't have access",
    "generally speaking",
    "in general,",
    "typically,",
    "usually,",
    "it is commonly known",
    "wikipedia",
    "according to my knowledge",
    "based on my training",
    "i'm not able to browse",
    "outside of the document",
    "beyond the document",
    "not in the provided",
)

STOP_WORDS = frozenset(
    """
    a an the is are was were be been being have has had do does did
    will would could should may might shall can need dare ought
    i you he she it we they me him her us them my your his its our their
    this that these those what which who whom whose where when why how
    and or but if then else so because as of at by for with about into
    through during before after above below to from up down in out on off
    over under again further once here there all each few more most other
    some such no nor not only own same than too very just also now
    tell give explain please answer question document file uploaded
    """.split()
)

# Chroma cosine distance — lower = more similar. Above this = likely irrelevant.
RELEVANCE_DISTANCE_THRESHOLD = 1.35


def extract_source_texts(sources: list[dict]) -> str:
    """Combine all source chunk text for grounding checks."""
    parts = [s.get("chunk_text", "") for s in sources if s.get("chunk_text")]
    return " ".join(parts).lower()


def sources_are_relevant(sources: list[dict]) -> bool:
    """True if at least one retrieved chunk is sufficiently similar."""
    if not sources:
        return False

    distances = [
        s["distance"]
        for s in sources
        if s.get("distance") is not None
    ]
    if not distances:
        return bool(sources)

    return min(distances) <= RELEVANCE_DISTANCE_THRESHOLD


def _significant_words(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]{3,}", text.lower())
    return {w for w in words if w not in STOP_WORDS}


def detect_outsourcing_phrases(answer: str) -> bool:
    lower = answer.lower()
    return any(phrase in lower for phrase in OUTSOURCING_PHRASES)


def answer_is_grounded(answer: str, sources: list[dict]) -> bool:
    """
    Check that the answer's key terms appear in the source chunks.
    Prevents the model from inventing facts not in the documents.
    """
    if not answer or not answer.strip():
        return False

    lower = answer.lower()
    if NOT_FOUND_PHRASE in lower:
        return True

    if detect_outsourcing_phrases(answer):
        return False

    source_text = extract_source_texts(sources)
    if not source_text.strip():
        return False

    answer_words = _significant_words(answer)
    if not answer_words:
        return True

    source_words = _significant_words(source_text)

    # Numbers in answer must appear in source (prevents invented stats)
    answer_numbers = set(re.findall(r"\b\d+\b", answer))
    source_numbers = set(re.findall(r"\b\d+\b", source_text))
    if answer_numbers and not answer_numbers.issubset(source_numbers):
        # Allow page/word counts from metadata passed in context
        extra_nums = answer_numbers - source_numbers
        if len(extra_nums) > 1:
            return False

    overlap = answer_words & source_words
    overlap_ratio = len(overlap) / len(answer_words)

    # At least 35% of significant answer words must come from sources
    return overlap_ratio >= 0.35


def filter_relevant_sources(sources: list[dict]) -> list[dict]:
    """Drop chunks that are too dissimilar to the query."""
    if not sources:
        return []

    has_distances = any(s.get("distance") is not None for s in sources)
    if not has_distances:
        return sources

    return [
        s for s in sources
        if s.get("distance") is None
        or s["distance"] <= RELEVANCE_DISTANCE_THRESHOLD
    ]
