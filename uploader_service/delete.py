from shared.chroma_manager import ChromaManager
from shared.database import delete_document_record, get_chunk_ids_for_document
from shared.config import setup_logging

logger = setup_logging(__name__)
_chroma = ChromaManager()


def remove_document(document_id: str) -> dict:
    """Remove a document from SQLite (including file blob) and ChromaDB."""
    chunk_ids = get_chunk_ids_for_document(document_id)
    doc = delete_document_record(document_id)

    if not doc:
        raise ValueError("Document not found.")

    _chroma.delete_chunks(chunk_ids)

    return {
        "status": "success",
        "document_id": document_id,
        "filename": doc["filename"],
    }
