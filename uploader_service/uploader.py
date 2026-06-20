from fastapi import UploadFile

from shared.config import setup_logging

logger = setup_logging(__name__)


class FileUploader:
    """Read uploaded file bytes — files are stored in SQLite, not on disk."""

    async def read_bytes(self, uploaded_file: UploadFile) -> tuple[str, bytes]:
        if not uploaded_file.filename:
            raise ValueError("Uploaded file has no filename")

        filename = uploaded_file.filename
        file_bytes = await uploaded_file.read()

        if not file_bytes:
            raise ValueError("Uploaded file is empty.")

        logger.info("Read %d bytes from upload: %s", len(file_bytes), filename)
        return filename, file_bytes
