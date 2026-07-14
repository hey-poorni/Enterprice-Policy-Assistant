import streamlit as st
import config
from src.utils import get_logger
from src.vector_store import HybridVectorStore
from src.startup import initialize_knowledge_base
from src.gemini import generate_policy_response
from src.memory import initialize_memory, add_message, get_history
from src.ui import setup_page_config, render_sidebar, render_chat_interface

logger = get_logger("app")

def main():
    # 1. Page Config and styling
    setup_page_config()
    
    # 2. Initialize Memory
    initialize_memory()
    
    # 3. Instantiate Hybrid Vector Store in session state so it persists
    if "vector_store" not in st.session_state:
        st.session_state.vector_store = HybridVectorStore()
        st.session_state.kb_ready = False
        st.session_state.kb_status = "Not initialized"
        
    store = st.session_state.vector_store
    
    # 4. Perform startup check once when app begins
    if not st.session_state.kb_ready and st.session_state.kb_status == "Not initialized":
        # Render a nice startup container
        st.markdown("### 🏢 Enterprise Policy Portal")
        
        # A container to show the progress dynamically
        status_placeholder = st.empty()
        
        def update_kb_status(msg: str):
            st.session_state.kb_status = msg
            status_placeholder.info(f"🔄 **Setup**: {msg}")
            
        with st.spinner("Initializing Enterprise Knowledge Base..."):
            try:
                # initialize_knowledge_base will return True or raise an exception
                success = initialize_knowledge_base(store, progress_callback=update_kb_status)
                if success:
                    st.session_state.kb_ready = True
                    st.session_state.kb_status = "ready"
                    st.success("✅ Knowledge base loaded successfully!")
                    st.rerun()
            except Exception as e:
                error_msg = f"error: {str(e)}"
                st.session_state.kb_status = error_msg
                
                # Check for empty policies folder error
                if "policy directory is empty" in str(e).lower():
                    st.error("❌ Knowledge base initialization failed. Policies folder is empty.")
                    st.warning("Please add company policy PDF files to the data/policies folder and refresh the page.")
                else:
                    st.error(f"❌ Critical error during startup initialization: {e}")
                    st.info("💡 Tip: If you are running this locally, verify that your GEMINI_API_KEY is properly set in your .env file.")
                
                logger.error(f"Startup initialization crash: {e}", exc_info=True)
                return
                
    # 5. Once initialized (or failed), render normal sidebar & chat
    if st.session_state.kb_ready or st.session_state.kb_status.startswith("error"):
        
        # Render sidebar
        render_sidebar(
            st.session_state.kb_status,
            rebuild_callback=None # Rebuilds happen automatically via scanning, can rerun
        )
        
        # Handle chat query submission
        def handle_user_query(query: str):
            # Display spinner while generating response
            with st.spinner("Searching policies and generating response..."):
                try:
                    # Get previous history for grounding the context
                    history = get_history().copy()
                    
                    # Search vector store for top 5 chunks
                    retrieved_chunks = store.search_hybrid(query, top_n=config.TOP_K)
                    
                    # Generate response via Gemini
                    response = generate_policy_response(
                        query=query,
                        retrieved_chunks=retrieved_chunks,
                        conversation_history=history
                    )
                    
                    # Add current turn to session history
                    add_message("user", query)
                    add_message("model", response)
                    
                except Exception as e:
                    logger.error(f"Error handling query: {e}", exc_info=True)
                    st.error(f"An error occurred while generating response: {e}")
                    add_message("user", query)
                    add_message("model", f"Sorry, an error occurred: {str(e)}")
                    
            st.rerun()
            
        # Render main chat layout
        render_chat_interface(
            kb_ready=st.session_state.kb_ready,
            on_query_submit=handle_user_query
        )

if __name__ == "__main__":
    main()
