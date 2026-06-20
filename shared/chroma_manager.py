import shutil
from typing import Any

import chromadb
from chromadb.config import Settings

from shared.config import CHROMA_PATH, setup_logging

logger = setup_logging(__name__)

COLLECTION_NAME = "document_brain"


def _create_client() -> chromadb.PersistentClient:
    """Create a fresh ChromaDB client (safe for multi-process on Windows)."""
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(CHROMA_PATH),
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True,
        ),
    )


def _get_collection(client: chromadb.PersistentClient):
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


class ChromaManager:
    def add_chunks(
        self,
        ids: list[str],
        chunks: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, str]],
    ) -> None:
        client = _create_client()
        collection = _get_collection(client)
        collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.info("Added %d chunks to ChromaDB", len(ids))

    def delete_chunks(self, chunk_ids: list[str]) -> None:
        if not chunk_ids:
            return
        client = _create_client()
        collection = _get_collection(client)
        collection.delete(ids=chunk_ids)
        logger.info("Deleted %d chunks from ChromaDB", len(chunk_ids))

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> dict[str, Any]:
        try:
            return self._query(query_embedding, top_k)
        except Exception as exc:
            logger.error("ChromaDB search failed: %s", exc)
            if self._needs_rebuild():
                logger.warning("Rebuilding ChromaDB index from SQLite...")
                self.rebuild_from_sqlite()
                return self._query(query_embedding, top_k)
            raise

    def _query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> dict[str, Any]:
        client = _create_client()
        collection = _get_collection(client)
        count = collection.count()

        if count == 0:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        n_results = min(top_k, count)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        logger.info(
            "ChromaDB search returned %d results",
            len(results.get("ids", [[]])[0]),
        )
        return results

    def count(self) -> int:
        try:
            client = _create_client()
            collection = _get_collection(client)
            return collection.count()
        except Exception as exc:
            logger.error("ChromaDB count failed: %s", exc)
            from shared.database import get_chunk_count
            return get_chunk_count()

    def _needs_rebuild(self) -> bool:
        """True if SQLite has chunks but Chroma index is missing or broken."""
        from shared.database import get_chunk_count
        return get_chunk_count() > 0

    def rebuild_from_sqlite(self, embedder=None) -> int:
        """
        Rebuild the full ChromaDB index from SQLite chunk records.
        Used when the on-disk HNSW index is corrupted or out of sync.
        """
        from shared.database import get_all_chunks_with_documents

        rows = get_all_chunks_with_documents()
        if not rows:
            return 0

        if embedder is None:
            from shared.embedder import Embedder
            embedder = Embedder()

        if CHROMA_PATH.exists():
            shutil.rmtree(CHROMA_PATH, ignore_errors=True)
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)

        client = _create_client()
        collection = _get_collection(client)

        ids: list[str] = []
        chunks: list[str] = []
        metadatas: list[dict[str, str]] = []

        for row in rows:
            ids.append(row["chunk_id"])
            chunks.append(row["chunk_text"])
            metadatas.append(
                {
                    "chunk_id": row["chunk_id"],
                    "document_id": row["document_id"],
                    "filename": row["filename"],
                    "chunk_text": row["chunk_text"][:1000],
                }
            )

        embeddings = embedder.embed(chunks)
        collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        logger.info("Rebuilt ChromaDB index with %d chunks", len(ids))
        return len(ids)
