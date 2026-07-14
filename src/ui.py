import streamlit as st
from typing import Callable, List, Dict, Any
from src.memory import get_history, clear_memory
from src.utils import get_logger

logger = get_logger("ui")

# Custom premium CSS styling to create a modern enterprise interface
CUSTOM_CSS = """
<style>
    /* Main Layout Customizations */
    .stApp {
        background: linear-gradient(135deg, #eef2f6 0%, #f1f5f9 50%, #f5eef8 100%) !important;
        color: #0f172a;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Main Card Container - mimics the rounded white container in Dribbble */
    .block-container {
        background-color: rgba(255, 255, 255, 0.8) !important;
        border-radius: 24px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.04), 0 1px 3px rgba(0, 0, 0, 0.02) !important;
        padding: 3rem !important;
        margin-top: 2rem !important;
        margin-bottom: 2rem !important;
        border: 1px solid rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(20px) !important;
    }
    
    /* Header Styling */
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 0.2rem;
        padding-top: 1rem;
        letter-spacing: -0.02em;
    }
    
    .subtitle {
        font-size: 1.1rem;
        color: #475569;
        margin-bottom: 2rem;
    }
    
    /* Sidebar styling - Glassmorphic Sidebar */
    section[data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.5) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.4) !important;
        backdrop-filter: blur(15px) !important;
    }
    
    section[data-testid="stSidebar"] .sidebar-title {
        font-size: 1.5rem;
        font-weight: 800;
        color: #0f172a !important;
        margin-bottom: 1.5rem;
    }

    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] caption {
        color: #334155 !important;
    }
    
    /* Chat bubbles styling - Premium rounded white cards */
    .stChatMessage {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1;
        border-radius: 16px !important;
        margin-bottom: 1rem !important;
        padding: 1.1rem !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02) !important;
        color: #0f172a !important;
    }
    
    .stChatMessage[data-testid="stChatMessageUser"] {
        background-color: #eff6ff !important;
        border: 1px solid #bfdbfe;
        color: #1e3a8a !important;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.04) !important;
    }
    
    /* Status indicators */
    .status-badge {
        display: inline-block;
        padding: 0.35rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 1.5rem;
    }
    
    .status-badge.ready {
        background-color: rgba(16, 185, 129, 0.08) !important;
        color: #065f46 !important;
        border: 1px solid rgba(16, 185, 129, 0.2) !important;
    }
    
    .status-badge.loading {
        background-color: rgba(245, 158, 11, 0.08) !important;
        color: #92400e !important;
        border: 1px solid rgba(245, 158, 11, 0.2) !important;
    }
    
    .status-badge.error {
        background-color: rgba(239, 68, 68, 0.08) !important;
        color: #991b1b !important;
        border: 1px solid rgba(239, 68, 68, 0.2) !important;
    }
    
    /* Buttons customization - Bold dark slate buttons */
    .stButton>button {
        background-color: #0f172a !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        border: 1px solid #0f172a !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton>button p, .stButton>button span {
        color: #ffffff !important;
    }
    
    .stButton>button:hover {
        background-color: #1e293b !important;
        border-color: #1e293b !important;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.15) !important;
    }
    
    .stButton>button:hover p, .stButton>button:hover span {
        color: #ffffff !important;
    }
    
    /* Info banners */
    .stAlert {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        color: #0f172a !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02) !important;
    }

    /* Fix visible typed text inside text inputs, textareas, and chat inputs */
    input, textarea, select {
        color: #0f172a !important;
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
    }
    
    div[data-testid="stChatInput"] textarea {
        color: #0f172a !important;
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.02) !important;
    }

    div[data-testid="stChatInput"] {
        background-color: transparent !important;
    }

    /* Focus styling */
    input:focus, textarea:focus {
        border-color: #0f172a !important;
        color: #0f172a !important;
        box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.1) !important;
    }

    /* Hide Streamlit deploy button and main menu, but keep the header container so the expand button stays visible */
    [data-testid="stDeployButton"] {
        display: none !important;
    }
    #MainMenu, [data-testid="stMainMenu"] {
        display: none !important;
    }
    footer {
        display: none !important;
        visibility: hidden !important;
    }

    /* Darken sidebar collapse/expand arrows for accessibility */
    [data-testid="collapsedControl"] svg,
    [data-testid="baseButton-header"] svg,
    [data-testid="collapsedControl"] button,
    [data-testid="baseButton-header"] button {
        color: #0f172a !important;
        fill: #0f172a !important;
    }
</style>
"""

def setup_page_config():
    """Sets up page configurations like title, layout, and tab icons."""
    st.set_page_config(
        page_title="EMPsupport",
        page_icon="src/favicon.png",
        layout="centered",
        initial_sidebar_state="expanded"
    )
    # Inject Custom CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

def render_sidebar(kb_status: str, rebuild_callback: Callable[[], None]):
    """
    Renders the sidebar components including KB status and control buttons.
    """
    with st.sidebar:
        st.markdown("<div class='sidebar-title'>EMPsupport</div>", unsafe_allow_html=True)
        st.markdown("---")
        
        # Display Knowledge Base Status
        st.subheader("Knowledge Base Status")
        if kb_status == "ready":
            st.markdown('<span class="status-badge ready">🟢 Ready</span>', unsafe_allow_html=True)
            st.caption("All policy documents are loaded and verified.")
        elif kb_status.startswith("error"):
            st.markdown('<span class="status-badge error">🔴 Error</span>', unsafe_allow_html=True)
            st.caption(f"Startup scan issue: {kb_status.split(':', 1)[1] if ':' in kb_status else kb_status}")
        else:
            st.markdown('<span class="status-badge loading">🟡 Updating</span>', unsafe_allow_html=True)
            st.caption(kb_status)
            
        st.markdown("---")
        
        # New Chat Control
        st.subheader("Chat Controls")
        if st.button("🔄 New Chat Session", use_container_width=True):
            clear_memory()
            st.rerun()
            
        st.markdown("---")
        st.caption("🔒 **Security & Grounding Notice**")
        st.caption(
            "This assistant is restricted strictly to official company policy data. "
            "Conversations are fully isolated and securely managed. Prompt injections and off-topic requests are rejected."
        )

def render_welcome_message():
    """Renders the main header welcome content."""
    st.markdown("<div class='main-title'>Enterprise Policy Assistant</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Ask questions and search company policies using secure grounded RAG</div>", unsafe_allow_html=True)
    
    # Showcase cards explaining the scope
    cols = st.columns(3)
    with cols[0]:
        st.info("🔍 **Hybrid Search**\nCombines keyword and semantics for accurate document retrieval.")
    with cols[1]:
        st.info("🛡️ **Injection Proof**\nBlocks untrusted system prompts and off-topic requests.")
    with cols[2]:
        st.info("📌 **Citations**\nReplies include document name, page reference, and confidence score.")

def render_chat_interface(
    kb_ready: bool,
    on_query_submit: Callable[[str], None]
):
    """
    Renders the central conversation layout, rendering history bubbles
    and handling the chat input field.
    """
    # 1. Render History
    history = get_history()
    
    # If history is empty, show welcome banner
    if not history:
        render_welcome_message()
    else:
        # Loop through and display messages
        for message in history:
            role = "user" if message["role"] == "user" else "assistant"
            with st.chat_message(role):
                st.markdown(message["text"])
                
    # 2. Render Chat Input
    if not kb_ready:
        st.warning("Please wait for the enterprise knowledge base to initialize before asking questions.")
        return
        
    query = st.chat_input("Enter your question about company policies...")
    if query:
        # Display the user message instantly
        with st.chat_message("user"):
            st.markdown(query)
            
        # Invoke the backend response callback
        on_query_submit(query)
