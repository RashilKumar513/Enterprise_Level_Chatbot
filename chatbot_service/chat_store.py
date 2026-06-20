"""Persist and restore chat sessions across page refreshes."""

from typing import Any

import streamlit as st

from shared.chat_db import (
    add_chat_message,
    chat_session_exists,
    create_chat_session,
    delete_chat_session,
    get_chat_messages,
    get_session_sources,
    list_chat_sessions,
    maybe_set_session_title_from_first_message,
    rename_chat_session,
    set_session_sources,
)


def get_active_chat_id() -> str:
    return st.session_state.active_chat_id


def load_chat_into_state(session_id: str) -> None:
    st.session_state.active_chat_id = session_id
    st.session_state.messages = get_chat_messages(session_id)
    st.session_state.last_sources = get_session_sources(session_id)
    st.query_params["chat"] = session_id


def ensure_active_chat() -> str:
    """Restore chat from URL or most recent session; create one if needed."""
    param_id = st.query_params.get("chat")

    if param_id and chat_session_exists(param_id):
        target_id = param_id
    else:
        sessions = list_chat_sessions()
        if sessions:
            target_id = sessions[0]["session_id"]
        else:
            target_id = create_chat_session()

    if st.session_state.get("active_chat_id") != target_id:
        load_chat_into_state(target_id)
    elif "messages" not in st.session_state:
        load_chat_into_state(target_id)
    elif st.query_params.get("chat") != target_id:
        st.query_params["chat"] = target_id

    return target_id


def start_new_chat() -> str:
    session_id = create_chat_session()
    load_chat_into_state(session_id)
    st.session_state.renaming_chat_id = None
    return session_id


def switch_chat(session_id: str) -> None:
    if not chat_session_exists(session_id):
        return
    load_chat_into_state(session_id)
    st.session_state.renaming_chat_id = None


def persist_user_message(session_id: str, content: str) -> None:
    add_chat_message(session_id, "user", content)
    maybe_set_session_title_from_first_message(session_id, content)


def persist_assistant_message(session_id: str, content: str) -> None:
    add_chat_message(session_id, "assistant", content)


def persist_sources(session_id: str, sources: list[dict[str, Any]]) -> None:
    set_session_sources(session_id, sources)
    st.session_state.last_sources = sources


def rename_chat(session_id: str, new_title: str) -> bool:
    return rename_chat_session(session_id, new_title.strip())


def remove_chat(session_id: str) -> str | None:
    """
    Delete a chat. Returns the session_id to switch to, or None if a new chat was created.
    """
    was_active = st.session_state.get("active_chat_id") == session_id
    delete_chat_session(session_id)

    if not was_active:
        return session_id

    remaining = list_chat_sessions()
    if remaining:
        next_id = remaining[0]["session_id"]
        load_chat_into_state(next_id)
        return next_id

    new_id = create_chat_session()
    load_chat_into_state(new_id)
    return new_id
