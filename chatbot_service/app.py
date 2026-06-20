import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from datetime import timedelta

import streamlit as st

from chatbot_service.chat_store import (
    ensure_active_chat,
    get_active_chat_id,
    persist_assistant_message,
    persist_sources,
    persist_user_message,
    remove_chat,
    rename_chat,
    start_new_chat,
    switch_chat,
)
from chatbot_service.grounding import sources_are_relevant
from chatbot_service.llm import LLM, NOT_FOUND_MESSAGE
from chatbot_service.query_handler import (
    build_chat_history,
    is_followup_request,
    try_direct_metadata_answer,
)
from chatbot_service.retriever import Retriever
from shared.chat_db import get_chat_session, list_chat_sessions
from shared.database import get_all_documents

UPLOAD_APP_URL = "http://127.0.0.1:8000"
REFRESH_SECONDS = 5

st.set_page_config(
    page_title="DocumentBrain",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --bg-main: #0d0d0d;
        --bg-sidebar: #171717;
        --bg-card: #212121;
        --bg-hover: #2a2a2a;
        --border: #333333;
        --text-primary: #ececec;
        --text-muted: #9b9b9b;
        --accent: #8b5cf6;
        --accent-soft: rgba(139, 92, 246, 0.15);
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: var(--bg-main) !important;
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 6rem;
        max-width: 780px;
    }

    /* Hide default Streamlit header/footer clutter */
    header[data-testid="stHeader"] { background: transparent; }
    .stApp { background: var(--bg-main); }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: var(--bg-sidebar) !important;
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0.5rem;
    }
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stCaption {
        color: var(--text-muted) !important;
    }

    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px 4px 20px 4px;
        border-bottom: 1px solid var(--border);
        margin-bottom: 12px;
    }
    .sidebar-brand-icon {
        width: 40px; height: 40px;
        background: linear-gradient(135deg, #6366f1, #a855f7);
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.3rem;
        flex-shrink: 0;
        box-shadow: 0 4px 12px rgba(99,102,241,0.3);
    }
    .sidebar-brand-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: var(--text-primary) !important;
        line-height: 1.2;
        margin: 0;
    }
    .sidebar-brand-sub {
        font-size: 0.72rem;
        color: var(--text-muted) !important;
        margin-top: 2px;
    }

    .sidebar-section-title {
        color: var(--text-muted) !important;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin: 18px 0 8px 2px;
    }

    .chat-list-scroll {
        max-height: 200px;
        overflow-y: auto;
        padding-right: 4px;
        margin-bottom: 4px;
    }
    .chat-list-scroll::-webkit-scrollbar { width: 4px; }
    .chat-list-scroll::-webkit-scrollbar-thumb {
        background: #444; border-radius: 4px;
    }

    [data-testid="stSidebar"] .stButton > button {
        background: transparent;
        border: 1px solid var(--border);
        color: var(--text-primary) !important;
        border-radius: 10px;
        font-weight: 500;
        transition: background 0.15s ease;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: var(--bg-hover);
        border-color: #555;
        color: var(--text-primary) !important;
    }

    [data-testid="stSidebar"] .new-chat-btn > button {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 0.55rem 1rem !important;
    }
    [data-testid="stSidebar"] .new-chat-btn > button:hover {
        background: var(--bg-hover) !important;
    }

    [data-testid="stSidebar"] .chat-active > button {
        background: var(--accent-soft) !important;
        border: 1px solid rgba(139,92,246,0.4) !important;
        color: #c4b5fd !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] .chat-item > button {
        background: transparent !important;
        border: none !important;
        padding: 8px 10px !important;
        font-size: 0.85rem !important;
        text-align: left !important;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    [data-testid="stSidebar"] .chat-item > button:hover {
        background: var(--bg-hover) !important;
    }
    [data-testid="stSidebar"] .icon-btn > button {
        background: transparent !important;
        border: none !important;
        padding: 4px 6px !important;
        min-width: 0 !important;
        font-size: 0.8rem !important;
        opacity: 0.7;
    }
    [data-testid="stSidebar"] .icon-btn > button:hover {
        opacity: 1;
        background: var(--bg-hover) !important;
    }

    .doc-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 10px 12px;
        margin-bottom: 6px;
        font-size: 0.82rem;
    }
    .doc-card strong { color: var(--text-primary) !important; }
    .doc-card span { color: var(--text-muted) !important; }

    .new-doc-banner {
        background: #1a2e1a;
        border: 1px solid #2d5a2d;
        color: #86efac !important;
        padding: 8px 12px;
        border-radius: 8px;
        margin-bottom: 10px;
        font-size: 0.82rem;
    }

    .upload-link {
        display: inline-block;
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 10px 14px;
        color: #c4b5fd !important;
        text-decoration: none;
        font-size: 0.85rem;
        font-weight: 500;
        width: 100%;
        text-align: center;
        transition: background 0.15s;
    }
    .upload-link:hover { background: var(--bg-hover); }

    .rename-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 12px;
        margin: 8px 0;
    }

    /* ── Main chat area ── */
    .chat-header {
        padding: 8px 0 20px 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 20px;
    }
    .chat-header-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0;
    }
    .chat-header-sub {
        font-size: 0.8rem;
        color: var(--text-muted);
        margin-top: 4px;
    }

    .empty-state {
        text-align: center;
        padding: 60px 20px;
        color: var(--text-muted);
    }
    .empty-state-icon { font-size: 2.5rem; margin-bottom: 12px; }
    .empty-state h3 {
        color: var(--text-primary);
        font-size: 1.1rem;
        font-weight: 600;
        margin: 0 0 8px 0;
    }
    .empty-state p { font-size: 0.88rem; margin: 0; }

    .stChatMessage {
        border-radius: 12px !important;
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
    }

    [data-testid="stChatInput"] textarea {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        border-radius: 14px !important;
    }

  hr { border-color: var(--border) !important; margin: 12px 0 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def load_retriever() -> Retriever:
    return Retriever()


@st.cache_resource
def load_llm() -> LLM:
    return LLM()


retriever = load_retriever()
llm = load_llm()

if "known_doc_count" not in st.session_state:
    st.session_state.known_doc_count = len(get_all_documents())

if "new_docs_banner" not in st.session_state:
    st.session_state.new_docs_banner = False

if "renaming_chat_id" not in st.session_state:
    st.session_state.renaming_chat_id = None

active_chat_id = ensure_active_chat()


def fetch_documents() -> list[dict]:
    return get_all_documents()


def has_documents() -> bool:
    return len(fetch_documents()) > 0


def format_sources(sources: list[dict]) -> str:
    if not sources:
        return ""
    lines = ["\n\n---\n**Sources**"]
    seen: set[str] = set()
    for source in sources:
        filename = source["filename"]
        if filename in seen:
            continue
        seen.add(filename)
        preview = source["chunk_text"][:160].replace("\n", " ").strip()
        lines.append(f"\n• **{filename}** — _{preview}..._")
    return "\n".join(lines)


def render_source_viewer(sources: list[dict]) -> None:
    if not sources:
        st.caption("Source excerpts appear here after you ask a question.")
        return
    seen: set[str] = set()
    for source in sources:
        filename = source["filename"]
        if filename in seen:
            continue
        seen.add(filename)
        with st.expander(f"📄 {filename}", expanded=False):
            st.caption(source["chunk_text"][:600])


def render_sidebar_brand() -> None:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-brand-icon">🧠</div>
            <div>
                <p class="sidebar-brand-title">DocumentBrain</p>
                <p class="sidebar-brand-sub">Document Q&A Assistant</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_rename_form() -> None:
    sid = st.session_state.renaming_chat_id
    if not sid:
        return
    chat = get_chat_session(sid)
    if not chat:
        st.session_state.renaming_chat_id = None
        return
    st.markdown('<div class="rename-card">', unsafe_allow_html=True)
    st.caption(f"Renaming: **{chat['title']}**")
    with st.form("rename_chat_form"):
        new_title = st.text_input("Chat name", value=chat["title"], max_chars=80, label_visibility="collapsed")
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Save", use_container_width=True, type="primary")
        with col2:
            cancelled = st.form_submit_button("Cancel", use_container_width=True)
        if submitted and new_title.strip():
            rename_chat(sid, new_title)
            st.session_state.renaming_chat_id = None
            st.rerun()
        if cancelled:
            st.session_state.renaming_chat_id = None
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_chat_sidebar() -> None:
    st.markdown('<div class="new-chat-btn">', unsafe_allow_html=True)
    if st.button("✏️  New chat", use_container_width=True, key="new_chat"):
        start_new_chat()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<p class="sidebar-section-title">Chats</p>', unsafe_allow_html=True)

    chats = list_chat_sessions()
    if not chats:
        st.caption("No chats yet. Start a new conversation.")
        return

    st.markdown('<div class="chat-list-scroll">', unsafe_allow_html=True)
    for chat in chats:
        sid = chat["session_id"]
        title = chat["title"]
        is_active = sid == get_active_chat_id()
        display_title = title if len(title) <= 28 else title[:27] + "…"

        row = st.columns([0.68, 0.16, 0.16])
        with row[0]:
            css_class = "chat-active" if is_active else "chat-item"
            st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
            if st.button(display_title, key=f"open_{sid}", use_container_width=True, help=title):
                if not is_active:
                    switch_chat(sid)
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        with row[1]:
            st.markdown('<div class="icon-btn">', unsafe_allow_html=True)
            if st.button("✏️", key=f"rename_{sid}", help="Rename chat"):
                st.session_state.renaming_chat_id = sid
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        with row[2]:
            st.markdown('<div class="icon-btn">', unsafe_allow_html=True)
            if st.button("🗑️", key=f"delete_{sid}", help="Delete chat"):
                remove_chat(sid)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


@st.fragment(run_every=timedelta(seconds=REFRESH_SECONDS))
def live_document_sidebar() -> None:
    documents = fetch_documents()
    current_count = len(documents)

    if current_count > st.session_state.known_doc_count:
        st.session_state.new_docs_banner = True
        st.session_state.known_doc_count = current_count

    if st.session_state.new_docs_banner:
        st.markdown(
            '<div class="new-doc-banner">✨ New document detected — ready to chat!</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<p class="sidebar-section-title">Documents</p>', unsafe_allow_html=True)
    if documents:
        for doc in documents:
            pages = doc.get("page_count") or "—"
            st.markdown(
                f'<div class="doc-card">📄 <strong>{doc["filename"]}</strong>'
                f'<br><span style="color:#9b9b9b;font-size:0.8rem">'
                f'{doc.get("filetype", "")} · {pages} pages</span></div>',
                unsafe_allow_html=True,
            )
    else:
        st.caption("No documents yet. Upload via the Upload App.")

    if st.button("🔄 Refresh documents", use_container_width=True, key="refresh_docs"):
        st.session_state.known_doc_count = current_count
        st.session_state.new_docs_banner = False
        st.rerun()


# ------------------- Sidebar -------------------
with st.sidebar:
    render_sidebar_brand()
    render_chat_sidebar()
    render_rename_form()
    st.markdown("---")
    live_document_sidebar()
    st.markdown("---")
    st.markdown('<p class="sidebar-section-title">Upload</p>', unsafe_allow_html=True)
    st.markdown(
        f'<a class="upload-link" href="{UPLOAD_APP_URL}" target="_blank">'
        f'📤 Open Upload App</a>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.markdown('<p class="sidebar-section-title">References</p>', unsafe_allow_html=True)
    render_source_viewer(st.session_state.last_sources)

# ------------------- Main chat header -------------------
_active = get_chat_session(get_active_chat_id())
_chat_title = _active["title"] if _active else "New chat"
_doc_count = len(fetch_documents())

st.markdown(
    f"""
    <div class="chat-header">
        <p class="chat-header-title">{_chat_title}</p>
        <p class="chat-header-sub">
            {_doc_count} document{"s" if _doc_count != 1 else ""} indexed
            · Answers from your uploads only
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ------------------- Chat history -------------------
if not st.session_state.messages:
    st.markdown(
        """
        <div class="empty-state">
            <div class="empty-state-icon">💬</div>
            <h3>Start a conversation</h3>
            <p>Ask about your documents — try "summarize" or ask about page counts.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ------------------- Input -------------------
question = st.chat_input("Ask about your documents... (try: summarize, or ask a follow-up)")

if question:
    chat_id = get_active_chat_id()
    persist_user_message(chat_id, question)
    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.new_docs_banner = False
    st.session_state.known_doc_count = len(fetch_documents())

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Reading your documents..."):
            try:
                if not has_documents():
                    answer = (
                        f"No documents indexed yet. "
                        f"Upload files at the **[Upload App]({UPLOAD_APP_URL})** first."
                    )
                    persist_sources(chat_id, [])
                    st.markdown(answer)
                else:
                    documents = fetch_documents()
                    history = build_chat_history(st.session_state.messages)
                    is_followup = is_followup_request(question)

                    direct = None
                    if not is_followup:
                        direct = try_direct_metadata_answer(question, documents)

                    if direct:
                        answer = direct
                        persist_sources(chat_id, [])
                        st.markdown(answer)
                    else:
                        if is_followup and st.session_state.last_sources:
                            sources = st.session_state.last_sources
                            context, extra = retriever.answer_question(
                                question, chat_history=history
                            )
                            if extra:
                                seen = {s["chunk_id"] for s in sources}
                                for s in extra:
                                    if s["chunk_id"] not in seen:
                                        sources.append(s)
                        else:
                            context, sources = retriever.answer_question(
                                question, chat_history=history
                            )

                        persist_sources(chat_id, sources)

                        if not sources:
                            answer = NOT_FOUND_MESSAGE
                            st.markdown(answer)
                        elif not is_followup and not sources_are_relevant(sources):
                            answer = NOT_FOUND_MESSAGE
                            st.markdown(answer)
                        elif not context:
                            answer = NOT_FOUND_MESSAGE
                            st.markdown(answer)
                        else:
                            answer = llm.generate(
                                question,
                                context,
                                sources=sources,
                                chat_history=history,
                            )
                            if answer == NOT_FOUND_MESSAGE:
                                full_answer = answer
                            elif sources and not is_followup:
                                full_answer = answer + format_sources(sources)
                            else:
                                full_answer = answer
                            st.markdown(full_answer)
                            answer = full_answer
            except Exception as exc:
                answer = "Something went wrong. Please try again."
                persist_sources(chat_id, [])
                st.error(f"{answer}\n\n_{exc}_")

    persist_assistant_message(chat_id, answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()
