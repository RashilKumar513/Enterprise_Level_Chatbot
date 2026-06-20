"""Persistent chat sessions and messages in SQLite."""

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any

from shared.config import SQLITE_DB, setup_logging

logger = setup_logging(__name__)

_conn = sqlite3.connect(str(SQLITE_DB), check_same_thread=False)
_conn.row_factory = sqlite3.Row
_cursor = _conn.cursor()


def init_chat_tables() -> None:
    _cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT 'New chat',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_sources_json TEXT
        )
        """
    )
    _cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            message_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
        )
        """
    )
    _conn.commit()
    logger.info("Chat tables ready")


def _now_iso() -> str:
    return datetime.now().isoformat()


def create_chat_session(title: str = "New chat") -> str:
    session_id = str(uuid.uuid4())
    now = _now_iso()
    _cursor.execute(
        """
        INSERT INTO chat_sessions (session_id, title, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        """,
        (session_id, title, now, now),
    )
    _conn.commit()
    return session_id


def list_chat_sessions() -> list[dict[str, Any]]:
    _cursor.execute(
        """
        SELECT session_id, title, created_at, updated_at
        FROM chat_sessions
        ORDER BY updated_at DESC
        """
    )
    return [dict(row) for row in _cursor.fetchall()]


def get_chat_session(session_id: str) -> dict[str, Any] | None:
    _cursor.execute(
        """
        SELECT session_id, title, created_at, updated_at, last_sources_json
        FROM chat_sessions
        WHERE session_id = ?
        """,
        (session_id,),
    )
    row = _cursor.fetchone()
    return dict(row) if row else None


def chat_session_exists(session_id: str) -> bool:
    _cursor.execute(
        "SELECT 1 FROM chat_sessions WHERE session_id = ?",
        (session_id,),
    )
    return _cursor.fetchone() is not None


def rename_chat_session(session_id: str, title: str) -> bool:
    title = title.strip()
    if not title:
        return False
    _cursor.execute(
        """
        UPDATE chat_sessions
        SET title = ?, updated_at = ?
        WHERE session_id = ?
        """,
        (title, _now_iso(), session_id),
    )
    _conn.commit()
    return _cursor.rowcount > 0


def delete_chat_session(session_id: str) -> bool:
    if not chat_session_exists(session_id):
        return False
    _cursor.execute(
        "DELETE FROM chat_messages WHERE session_id = ?",
        (session_id,),
    )
    _cursor.execute(
        "DELETE FROM chat_sessions WHERE session_id = ?",
        (session_id,),
    )
    _conn.commit()
    return True


def get_chat_messages(session_id: str) -> list[dict[str, str]]:
    _cursor.execute(
        """
        SELECT role, content
        FROM chat_messages
        WHERE session_id = ?
        ORDER BY sort_order ASC
        """,
        (session_id,),
    )
    return [dict(row) for row in _cursor.fetchall()]


def add_chat_message(session_id: str, role: str, content: str) -> str:
    message_id = str(uuid.uuid4())
    _cursor.execute(
        "SELECT COALESCE(MAX(sort_order), -1) FROM chat_messages WHERE session_id = ?",
        (session_id,),
    )
    next_order = int(_cursor.fetchone()[0]) + 1
    now = _now_iso()
    _cursor.execute(
        """
        INSERT INTO chat_messages
        (message_id, session_id, role, content, created_at, sort_order)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (message_id, session_id, role, content, now, next_order),
    )
    _cursor.execute(
        """
        UPDATE chat_sessions
        SET updated_at = ?
        WHERE session_id = ?
        """,
        (now, session_id),
    )
    _conn.commit()
    return message_id


def set_session_sources(session_id: str, sources: list[dict[str, Any]]) -> None:
    payload = json.dumps(sources) if sources else None
    _cursor.execute(
        """
        UPDATE chat_sessions
        SET last_sources_json = ?, updated_at = ?
        WHERE session_id = ?
        """,
        (payload, _now_iso(), session_id),
    )
    _conn.commit()


def get_session_sources(session_id: str) -> list[dict[str, Any]]:
    session = get_chat_session(session_id)
    if not session or not session.get("last_sources_json"):
        return []
    try:
        data = json.loads(session["last_sources_json"])
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def auto_title_from_message(message: str, max_len: int = 48) -> str:
    text = " ".join(message.strip().split())
    if not text:
        return "New chat"
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def maybe_set_session_title_from_first_message(
    session_id: str,
    user_message: str,
) -> None:
    session = get_chat_session(session_id)
    if not session or session["title"] != "New chat":
        return
    _cursor.execute(
        "SELECT COUNT(*) FROM chat_messages WHERE session_id = ? AND role = 'user'",
        (session_id,),
    )
    if int(_cursor.fetchone()[0]) != 1:
        return
    rename_chat_session(session_id, auto_title_from_message(user_message))


init_chat_tables()
