import os
import time
from typing import List, Dict, Any, Optional, Tuple
from google import genai
from google.genai import types
from google.genai.errors import APIError
from src.utils import get_logger
from src.embeddings import get_gemini_client
import config

logger = get_logger("gemini")

# A set of low-level keyword checking for prompt injections and off-topic questions
INJECTION_KEYWORDS = [
    "ignore previous instructions", "reveal your system prompt", "reveal your prompt",
    "show hidden files", "developer mode", "jailbreak", "bypass instructions",
    "forget what i said", "you are now a", "act as a"
]

OFF_TOPIC_KEYWORDS = [
    "write code", "how to write a python script", "python programming", "javascript",
    "who is the president", "explain quantum physics", "medical advice",
    "stock market tips", "how to cure", "legal representation"
]

def check_security_and_scope(query: str) -> Tuple[bool, str]:
    """
    Analyzes the query for prompt injection and out-of-scope content.
    Returns (is_secure_and_in_scope, explanation_response).
    """
    query_lower = query.lower()
    
    # 1. Check for prompt injection
    for kw in INJECTION_KEYWORDS:
        if kw in query_lower:
            logger.warning(f"Security Alert: Prompt injection attempt detected via keyword: '{kw}'")
            return False, "I cannot fulfill this request. I am designed exclusively to answer questions about official company policies based on retrieved documents."
            
    # 2. Check for obvious off-topic queries
    for kw in OFF_TOPIC_KEYWORDS:
        if kw in query_lower:
            logger.info(f"Scope Check: Off-topic query filtered: '{kw}'")
            return False, "I am designed exclusively to answer questions about official company policies. I cannot provide assistance with programming, general knowledge, medical, legal, or financial topics."
            
    return True, ""

def format_rag_prompt(query: str, chunks: List[Dict[str, Any]], history: List[Dict[str, str]]) -> Tuple[str, List[types.Content]]:
    """
    Formats the prompts and formats the conversation history for the Gemini Client.
    We pass system instructions and history as structured contents.
    """
    # Build context from chunks
    context_str = ""
    for idx, chunk in enumerate(chunks):
        context_str += f"--- Context Chunk {idx+1} ---\n"
        context_str += f"Source: {chunk['source']}\n"
        context_str += f"Department: {chunk['department']}\n"
        context_str += f"Page: {chunk['page_num']}\n"
        context_str += f"Content:\n{chunk['text']}\n\n"

    # We will build the contents list for Gemini chat API
    contents = []
    
    # 1. Format conversation history
    # The history list is a list of dicts: {'role': 'user'/'model', 'text': '...'}
    for msg in history:
        role = msg["role"]
        # Map simple roles to Gemini roles ('user' -> 'user', 'model' -> 'model')
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["text"])]
            )
        )
        
    # 2. Append the current query with the context
    prompt = f"""Retrieved Policy Context Chunks:
{context_str}

User Question: {query}
"""
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        )
    )
    
    return prompt, contents


def _execute_with_retry(client, model: str, contents: Any, config_options: Any) -> Any:
    """Executes a content generation call with automatic retries for transient errors."""
    max_retries = 3
    retry_delay = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Sending query to Gemini using model: {model} (attempt {attempt + 1}/{max_retries})")
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config_options
            )
        except APIError as e:
            is_transient = e.code in [429, 503] or "high demand" in str(e).lower() or "unavailable" in str(e).lower()
            if is_transient and attempt < max_retries - 1:
                sleep_time = retry_delay * (2 ** attempt)
                logger.warning(f"Gemini API transient error ({e.code}) on model {model}: {e.message}. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
            else:
                raise e


def generate_policy_response(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    conversation_history: List[Dict[str, str]]
) -> str:
    """
    Generates a response from Gemini using RAG.
    Applies security pre-checks and manages system instructions.
    Automatically handles rate-limiting or high-demand errors via fallback models.
    """
    # 1. Run security and scope checks
    is_safe, response_message = check_security_and_scope(query)
    if not is_safe:
        return response_message
        
    # 2. If no context was retrieved, return the standard 'not found' message immediately
    if not retrieved_chunks:
        return (
            "I couldn't find information related to your question in the available company policy documents. "
            "Please consult HR or the appropriate department for clarification."
        )
        
    try:
        client = get_gemini_client()
        _, contents = format_rag_prompt(query, retrieved_chunks, conversation_history)
        
        # Configure model parameters
        config_options = types.GenerateContentConfig(
            system_instruction=config.SYSTEM_INSTRUCTION,
            temperature=0.1,  # Low temperature for deterministic, fact-grounded responses
            max_output_tokens=8192,
            # Block safety categories to protect the model
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                )
            ]
        )
        
        primary_model = config.GENERATION_MODEL
        fallback_models = ["gemini-flash-lite-latest", "gemini-flash-latest"]
        
        response = None
        try:
            response = _execute_with_retry(client, primary_model, contents, config_options)
        except APIError as e:
            # Check if this error warrants trying a fallback model (e.g. daily limit hit or server overload)
            is_exhausted_or_congested = e.code in [429, 503] or "quota" in str(e).lower() or "demand" in str(e).lower()
            if is_exhausted_or_congested:
                logger.warning(f"Primary model '{primary_model}' failed with error: {e.message}. Attempting fallback models...")
                for backup_model in fallback_models:
                    try:
                        logger.info(f"Attempting fallback model: {backup_model}")
                        response = _execute_with_retry(client, backup_model, contents, config_options)
                        logger.info(f"Fallback to '{backup_model}' succeeded!")
                        break
                    except APIError as fallback_err:
                        logger.error(f"Fallback model '{backup_model}' also failed: {fallback_err.message}")
                
                # If all fallback models failed, raise the final exception
                if not response:
                    raise e
            else:
                raise e
        
        if not response or not response.text:
            logger.error("Gemini returned an empty response.")
            return "An unexpected error occurred. The response generated was empty."
            
        return response.text
        
    except APIError as e:
        logger.error(f"Gemini API Error: {e}")
        return f"Gemini API error occurred: {e.message}. Please try again later or contact your administrator."
    except Exception as e:
        logger.error(f"Unexpected error in Gemini response generation: {e}")
        return "An unexpected error occurred while generating the response. Please consult the log files for details."


