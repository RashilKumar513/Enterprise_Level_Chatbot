from typing import Any

from chatbot_service.grounding import filter_relevant_sources
from chatbot_service.query_handler import (
    is_followup_request,
    is_summary_request,
    match_filename_in_question,
)
from shared.chroma_manager import ChromaManager
from shared.config import TOP_K, setup_logging
from shared.database import (
    get_all_documents,
    get_chunks_for_document,
    get_document,
)
from shared.embedder import Embedder

logger = setup_logging(__name__)

SUMMARY_TOP_K = 20


class Retriever:
    def __init__(self) -> None:
        self.embedder = Embedder()
        self.chroma = ChromaManager()

    def answer_question(
        self,
        question: str,
        chat_history: list[dict] | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Build context and sources for a question.
        Reuses prior sources for follow-up questions when possible.
        """
        documents = get_all_documents()
        if not documents:
            return "", []

        if is_followup_request(question) and chat_history:
            search_query = self._followup_search_query(question, chat_history)
        else:
            search_query = question

        if is_summary_request(question):
            sources = self._sources_for_summary(search_query, documents)
        else:
            top_k = SUMMARY_TOP_K if len(documents) == 1 else TOP_K
            if is_followup_request(question):
                top_k = SUMMARY_TOP_K
            sources = self.search(search_query, top_k=top_k)

        sources = filter_relevant_sources(sources)
        context = self._build_context(sources, documents, chat_history)
        return context, sources

    def _followup_search_query(
        self,
        question: str,
        chat_history: list[dict],
    ) -> str:
        """Combine previous question with follow-up for better retrieval."""
        prev_user = ""
        for msg in reversed(chat_history):
            if msg.get("role") == "user":
                prev_user = msg.get("content", "")
                break
        if prev_user:
            return f"{prev_user} {question}"
        return question

    def _sources_for_summary(
        self,
        question: str,
        documents: list[dict],
    ) -> list[dict[str, Any]]:
        """Load all chunks from target document(s) for summarization."""
        filenames = [d["filename"] for d in documents]
        target_name = match_filename_in_question(question, filenames)

        if target_name:
            target_docs = [d for d in documents if d["filename"] == target_name]
        elif len(documents) == 1:
            target_docs = documents
        else:
            # Multiple docs, no name mentioned — use vector search for best match
            hits = self.search(question, top_k=SUMMARY_TOP_K)
            if not hits:
                return []
            best_doc_id = hits[0]["document_id"]
            target_docs = [d for d in documents if d["document_id"] == best_doc_id]

        sources: list[dict[str, Any]] = []
        for doc in target_docs:
            chunks = get_chunks_for_document(doc["document_id"])
            for chunk in chunks:
                sources.append(
                    {
                        "chunk_id": chunk["chunk_id"],
                        "document_id": doc["document_id"],
                        "filename": doc["filename"],
                        "chunk_text": chunk["chunk_text"],
                        "filetype": doc.get("filetype"),
                        "upload_date": doc.get("upload_date"),
                        "page_count": doc.get("page_count"),
                        "word_count": doc.get("word_count"),
                    }
                )

        logger.info(
            "Summary mode: loaded %d chunks from %d document(s)",
            len(sources),
            len(target_docs),
        )
        return sources

    def search(self, query: str, top_k: int = TOP_K) -> list[dict[str, Any]]:
        query_embedding = self.embedder.embed(query)[0]
        try:
            results = self.chroma.search(query_embedding, top_k=top_k)
        except Exception as exc:
            logger.error("Search failed: %s", exc)
            return []

        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        enriched: list[dict[str, Any]] = []

        for idx, chunk_id in enumerate(ids):
            metadata = metadatas[idx] if idx < len(metadatas) else {}
            document_id = metadata.get("document_id", "")
            filename = metadata.get("filename", "unknown")
            chunk_text = documents[idx] if idx < len(documents) else ""

            doc_meta = get_document(document_id) if document_id else None
            if doc_meta:
                filename = doc_meta.get("filename", filename)

            enriched.append(
                {
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_text": chunk_text,
                    "distance": distances[idx] if idx < len(distances) else None,
                    "filetype": doc_meta.get("filetype") if doc_meta else None,
                    "upload_date": doc_meta.get("upload_date") if doc_meta else None,
                    "page_count": doc_meta.get("page_count") if doc_meta else None,
                    "word_count": doc_meta.get("word_count") if doc_meta else None,
                }
            )

        logger.info("Retriever found %d relevant chunks", len(enriched))
        return enriched

    def _build_context(
        self,
        sources: list[dict[str, Any]],
        all_documents: list[dict],
        chat_history: list[dict] | None = None,
    ) -> str:
        """Build LLM context with metadata, chat history, and chunk text."""
        blocks: list[str] = []

        seen_docs: set[str] = set()
        meta_lines = ["=== DOCUMENT METADATA ==="]
        for doc in all_documents:
            doc_id = doc["document_id"]
            if doc_id in seen_docs:
                continue
            seen_docs.add(doc_id)
            pages = doc.get("page_count") or max(1, (doc.get("word_count") or 0) // 300)
            meta_lines.append(
                f"File: {doc['filename']} | Type: {doc.get('filetype', '?')} | "
                f"Pages: {pages} | Words: {doc.get('word_count', 0)}"
            )
        blocks.append("\n".join(meta_lines))

        if chat_history:
            hist_lines = ["=== CHAT HISTORY (for follow-up questions) ==="]
            for msg in chat_history[-6:]:
                role = msg.get("role", "user").upper()
                hist_lines.append(f"{role}: {msg.get('content', '')[:800]}")
            blocks.append("\n".join(hist_lines))

        if sources:
            blocks.append("=== DOCUMENT CONTENT ===")
            for idx, source in enumerate(sources, start=1):
                blocks.append(
                    f"[Excerpt {idx} from {source['filename']}]\n"
                    f"{source['chunk_text']}"
                )

        return "\n\n".join(blocks)
