from datetime import datetime
from pathlib import Path
from uuid import uuid4

from shared.chroma_manager import ChromaManager
from shared.config import ALLOWED_EXTENSIONS, setup_logging
from shared.database import insert_chunk, insert_document
from shared.embedder import Embedder
from uploader_service.chunker import chunk_text
from uploader_service.processor import DocumentProcessor

logger = setup_logging(__name__)

_processor = DocumentProcessor()
_embedder = Embedder()
_chroma = ChromaManager()


def ingest_document(filename: str, file_bytes: bytes) -> dict:
    """Process, index, and store a document in the database."""
    if not filename:
        raise ValueError("Filename is required")

    if not file_bytes:
        raise ValueError("File is empty.")

    filetype = Path(filename).suffix.lower()
    if filetype not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type. "
            f"Please upload: PDF, DOCX, PNG, JPG, or JPEG."
        )

    safe_name = Path(filename).name
    document_id = str(uuid4())

    result = _processor.process_bytes(file_bytes, safe_name)
    text = result.text

    if not text.strip():
        raise ValueError(
            "No text could be extracted from this file. "
            "Try a different document or a clearer image."
        )

    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("This document appears to be empty.")

    embeddings = _embedder.embed(chunks)
    chunk_ids: list[str] = []
    metadatas: list[dict[str, str]] = []

    for chunk in chunks:
        chunk_id = str(uuid4())
        chunk_ids.append(chunk_id)
        insert_chunk(chunk_id, document_id, chunk)
        metadatas.append(
            {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "filename": safe_name,
                "chunk_text": chunk[:1000],
            }
        )

    _chroma.add_chunks(
        ids=chunk_ids,
        chunks=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    insert_document(
        document_id=document_id,
        filename=safe_name,
        filetype=filetype,
        upload_date=datetime.now().isoformat(),
        file_data=file_bytes,
        page_count=result.page_count,
        word_count=result.word_count,
        char_count=result.char_count,
        chunk_count=len(chunks),
    )

    logger.info(
        "Indexed %s: %d pages, %d chunks, %d bytes",
        document_id,
        result.page_count,
        len(chunks),
        len(file_bytes),
    )

    return {
        "status": "success",
        "document_id": document_id,
        "filename": safe_name,
        "chunks": len(chunks),
        "page_count": result.page_count,
        "word_count": result.word_count,
        "file_size": len(file_bytes),
    }
