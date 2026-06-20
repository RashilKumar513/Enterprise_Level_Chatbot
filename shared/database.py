import sqlite3
from typing import Any
from shared.config import SQLITE_DB, setup_logging

logger = setup_logging(__name__)

_conn = sqlite3.connect(
    str(SQLITE_DB),
    check_same_thread=False,
)
_conn.row_factory = sqlite3.Row
_cursor = _conn.cursor()

# Columns returned for lists (excludes large file_data blob)
_DOC_LIST_COLUMNS = (
    "document_id, filename, filetype, upload_date, file_size, "
    "page_count, word_count, char_count, chunk_count"
)


def init_db() -> None:
    _cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            filetype TEXT NOT NULL,
            upload_date TEXT NOT NULL,
            file_data BLOB NOT NULL,
            file_size INTEGER NOT NULL DEFAULT 0,
            page_count INTEGER NOT NULL DEFAULT 0,
            word_count INTEGER NOT NULL DEFAULT 0,
            char_count INTEGER NOT NULL DEFAULT 0,
            chunk_count INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    _cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            chunk_text TEXT NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents(document_id)
        )
        """
    )
    _cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            created_at TEXT NOT NULL
        )
        """
    )
    _migrate_schema()
    _seed_default_admin()
    _conn.commit()
    logger.info("SQLite database initialized at %s", SQLITE_DB)


def _migrate_schema() -> None:
    """Add file_data columns to existing databases created before this version."""
    _cursor.execute("PRAGMA table_info(documents)")
    columns = {row[1] for row in _cursor.fetchall()}

    if "file_data" not in columns:
        _cursor.execute("ALTER TABLE documents ADD COLUMN file_data BLOB")
        logger.info("Added file_data column to documents table")

    if "file_size" not in columns:
        _cursor.execute(
            "ALTER TABLE documents ADD COLUMN file_size INTEGER DEFAULT 0"
        )
        logger.info("Added file_size column to documents table")

    for col in ("page_count", "word_count", "char_count", "chunk_count"):
        if col not in columns:
            _cursor.execute(
                f"ALTER TABLE documents ADD COLUMN {col} INTEGER DEFAULT 0"
            )
            logger.info("Added %s column to documents table", col)


def insert_document(
    document_id: str,
    filename: str,
    filetype: str,
    upload_date: str,
    file_data: bytes,
    page_count: int = 0,
    word_count: int = 0,
    char_count: int = 0,
    chunk_count: int = 0,
) -> None:
    """Store document metadata and raw file bytes in SQLite."""
    _cursor.execute(
        """
        INSERT INTO documents (
            document_id, filename, filetype, upload_date, file_data, file_size,
            page_count, word_count, char_count, chunk_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            document_id,
            filename,
            filetype,
            upload_date,
            file_data,
            len(file_data),
            page_count,
            word_count,
            char_count,
            chunk_count,
        ),
    )
    _conn.commit()
    logger.info(
        "Stored document %s (%s, %d bytes) in database",
        document_id,
        filename,
        len(file_data),
    )


def insert_chunk(
    chunk_id: str,
    document_id: str,
    chunk_text: str,
) -> None:
    _cursor.execute(
        """
        INSERT INTO chunks (chunk_id, document_id, chunk_text)
        VALUES (?, ?, ?)
        """,
        (chunk_id, document_id, chunk_text),
    )
    _conn.commit()


def get_document(document_id: str) -> dict[str, Any] | None:
    _cursor.execute(
        f"""
        SELECT {_DOC_LIST_COLUMNS}
        FROM documents
        WHERE document_id = ?
        """,
        (document_id,),
    )
    row = _cursor.fetchone()
    return dict(row) if row else None


def get_file_data(document_id: str) -> tuple[bytes, str, str] | None:
    """Return (file_bytes, filename, filetype) for a stored document."""
    _cursor.execute(
        """
        SELECT file_data, filename, filetype
        FROM documents
        WHERE document_id = ?
        """,
        (document_id,),
    )
    row = _cursor.fetchone()
    if row is None or row[0] is None:
        return None
    return bytes(row[0]), row[1], row[2]


def get_all_documents() -> list[dict[str, Any]]:
    _cursor.execute(
        f"""
        SELECT {_DOC_LIST_COLUMNS}
        FROM documents
        ORDER BY upload_date DESC
        """
    )
    return [dict(row) for row in _cursor.fetchall()]


def get_all_chunks_with_documents() -> list[dict[str, Any]]:
    _cursor.execute(
        """
        SELECT c.chunk_id, c.document_id, c.chunk_text, d.filename
        FROM chunks c
        JOIN documents d ON c.document_id = d.document_id
        ORDER BY d.upload_date ASC
        """
    )
    return [dict(row) for row in _cursor.fetchall()]


def get_chunks_for_document(document_id: str) -> list[dict[str, Any]]:
    """Return all text chunks for a document in insertion order."""
    _cursor.execute(
        """
        SELECT chunk_id, chunk_text
        FROM chunks
        WHERE document_id = ?
        ORDER BY rowid ASC
        """,
        (document_id,),
    )
    return [dict(row) for row in _cursor.fetchall()]


def get_chunk_count() -> int:
    _cursor.execute("SELECT COUNT(*) FROM chunks")
    return int(_cursor.fetchone()[0])


def get_chunk_ids_for_document(document_id: str) -> list[str]:
    _cursor.execute(
        "SELECT chunk_id FROM chunks WHERE document_id = ?",
        (document_id,),
    )
    return [row[0] for row in _cursor.fetchall()]


def delete_document_record(document_id: str) -> dict[str, Any] | None:
    doc = get_document(document_id)
    if not doc:
        return None

    _cursor.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
    _cursor.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
    _conn.commit()
    logger.info("Deleted document %s (%s) from database", document_id, doc["filename"])
    return doc


def has_indexed_documents() -> bool:
    _cursor.execute("SELECT COUNT(*) FROM documents")
    return int(_cursor.fetchone()[0]) > 0


def _seed_default_admin() -> None:
    """Create default admin user from environment if no users exist."""
    from datetime import datetime

    from shared.auth import hash_password
    from shared.config import ADMIN_PASSWORD, ADMIN_USERNAME

    _cursor.execute("SELECT COUNT(*) FROM users")
    if int(_cursor.fetchone()[0]) > 0:
        return

    _cursor.execute(
        """
        INSERT INTO users (username, password_hash, role, created_at)
        VALUES (?, ?, 'admin', ?)
        """,
        (
            ADMIN_USERNAME,
            hash_password(ADMIN_PASSWORD),
            datetime.now().isoformat(),
        ),
    )
    logger.info("Created default admin user '%s'", ADMIN_USERNAME)


def get_user_password_hash(username: str) -> str | None:
    _cursor.execute(
        "SELECT password_hash FROM users WHERE username = ?",
        (username,),
    )
    row = _cursor.fetchone()
    return row[0] if row else None


def user_exists(username: str) -> bool:
    _cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
    return _cursor.fetchone() is not None


init_db()
