import logging
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

CHROMA_PATH = DATABASE_DIR / "chroma_db"
SQLITE_DB = DATABASE_DIR / "metadata.db"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
OLLAMA_MODEL = "llama3"
CHUNK_SIZE = 500
TOP_K = 8

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}

TESSERACT_CMD = os.environ.get("TESSERACT_CMD", "")

# Upload app admin credentials (set via environment variables in production)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_LEVEL = logging.INFO


def setup_logging(name: str) -> logging.Logger:
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        force=True,
    )
    return logging.getLogger(name)
