from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import pytesseract
from docx import Document
from PIL import Image
from pypdf import PdfReader

from shared.config import TESSERACT_CMD, setup_logging

logger = setup_logging(__name__)

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

WORDS_PER_PAGE_ESTIMATE = 300


@dataclass
class ProcessResult:
    text: str
    page_count: int
    word_count: int
    char_count: int


class DocumentProcessor:
    """Extract text and metadata from document bytes."""

    def extract_pdf(self, file_bytes: bytes) -> ProcessResult:
        reader = PdfReader(BytesIO(file_bytes))
        page_count = len(reader.pages)
        text_parts: list[str] = []

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        text = "\n".join(text_parts)
        words = text.split()
        logger.info(
            "PDF: %d pages, %d words extracted",
            page_count,
            len(words),
        )
        return ProcessResult(
            text=text,
            page_count=page_count,
            word_count=len(words),
            char_count=len(text),
        )

    def extract_docx(self, file_bytes: bytes) -> ProcessResult:
        doc = Document(BytesIO(file_bytes))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        text = "\n".join(paragraphs)
        words = text.split()
        page_count = max(1, len(words) // WORDS_PER_PAGE_ESTIMATE)
        logger.info(
            "DOCX: ~%d pages (estimated), %d words extracted",
            page_count,
            len(words),
        )
        return ProcessResult(
            text=text,
            page_count=page_count,
            word_count=len(words),
            char_count=len(text),
        )

    def extract_image(self, file_bytes: bytes) -> ProcessResult:
        try:
            image = Image.open(BytesIO(file_bytes))
            text = pytesseract.image_to_string(image)
        except pytesseract.TesseractNotFoundError as exc:
            raise ValueError(
                "Tesseract OCR is not installed. "
                "Install Tesseract for Windows and set TESSERACT_CMD "
                "environment variable if needed."
            ) from exc

        words = text.split()
        logger.info("Image: 1 page, %d words via OCR", len(words))
        return ProcessResult(
            text=text,
            page_count=1,
            word_count=len(words),
            char_count=len(text),
        )

    def process_bytes(self, file_bytes: bytes, filename: str) -> ProcessResult:
        suffix = Path(filename).suffix.lower()

        if suffix == ".pdf":
            return self.extract_pdf(file_bytes)
        if suffix == ".docx":
            return self.extract_docx(file_bytes)
        if suffix in {".png", ".jpg", ".jpeg"}:
            return self.extract_image(file_bytes)

        raise ValueError(
            f"Unsupported file type '{suffix}'. "
            "Allowed types: PDF, DOCX, PNG, JPG, JPEG."
        )
