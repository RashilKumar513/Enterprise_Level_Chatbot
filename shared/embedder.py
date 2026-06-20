from typing import Union

from sentence_transformers import SentenceTransformer

from shared.config import EMBEDDING_MODEL, setup_logging

logger = setup_logging(__name__)


class Embedder:
    def __init__(self) -> None:
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info("Embedding model loaded")

    def embed(self, texts: Union[str, list[str]]) -> list[list[float]]:
        if isinstance(texts, str):
            texts = [texts]
        vectors = self.model.encode(texts).tolist()
        logger.info("Generated embeddings for %d text(s)", len(texts))
        return vectors
