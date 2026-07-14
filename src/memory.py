import streamlit as st
from typing import List, Dict
from src.utils import get_logger

logger = get_logger("memory")

MEMORY_KEY = "chat_history"

def initialize_memory():
    """Initializes the conversation memory in streamlit session state if it does not exist."""
    if MEMORY_KEY not in st.session_state:
        st.session_state[MEMORY_KEY] = []
        logger.info("Initialized fresh chat memory in session state.")

def get_history() -> List[Dict[str, str]]:
    """Retrieves the conversation history from session state."""
    initialize_memory()
    return st.session_state[MEMORY_KEY]

def add_message(role: str, text: str):
    """
    Adds a message to the conversation history.
    role: 'user' or 'model' (as required by google-genai).
    """
    initialize_memory()
    if role not in ["user", "model"]:
        raise ValueError(f"Invalid message role: {role}. Role must be 'user' or 'model'.")
    st.session_state[MEMORY_KEY].append({
        "role": role,
        "text": text
    })
    logger.debug(f"Added '{role}' message to chat history.")

def clear_memory():
    """Clears the chat memory, effectively starting a new session."""
    st.session_state[MEMORY_KEY] = []
    logger.info("Cleared conversation memory for a new session.")
