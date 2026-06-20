from shared.config import CHUNK_SIZE, setup_logging

logger = setup_logging(__name__)


def chunk_text(text: str) -> list[str]:
    words = text.split()
    chunks: list[str] = []

    for start in range(0, len(words), CHUNK_SIZE):
        chunk = " ".join(words[start : start + CHUNK_SIZE])
        if chunk.strip():
            chunks.append(chunk)

    logger.info("Created %d chunks from document text", len(chunks))
    return chunks
