import os
import time
from typing import List
from google import genai
from google.genai.errors import APIError
from src.utils import get_logger
import config

logger = get_logger("embeddings")

def get_gemini_client() -> genai.Client:
    """
    Initializes and returns the Google GenAI Client.
    Validates that GEMINI_API_KEY is present in the environment.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is missing from environment. Please add it to your .env file.")
        raise ValueError("GEMINI_API_KEY is not set. Please configure it in your environment/variables.")
    
    # Initialize the client. Under the hood, this client reads GEMINI_API_KEY
    return genai.Client(api_key=api_key)

def generate_embeddings(texts: List[str], batch_size: int = 100) -> List[List[float]]:
    """
    Generates embeddings for a list of texts using the configured Gemini embedding model.
    Uses batching to avoid API rate limits and improve network efficiency.
    """
    client = get_gemini_client()
    embeddings = []
    
    logger.info(f"Generating embeddings for {len(texts)} chunks using model '{config.EMBEDDING_MODEL}'")
    
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        logger.info(f"Processing embedding batch {i // batch_size + 1} ({len(batch_texts)} texts)")
        
        # Implement retry logic for API calls
        max_retries = 3
        retry_delay = 2
        for attempt in range(max_retries):
            try:
                response = client.models.embed_content(
                    model=config.EMBEDDING_MODEL,
                    contents=batch_texts
                )
                
                # Check response structure
                if not response.embeddings:
                    raise ValueError("No embeddings returned in API response.")
                
                # The response structure has .embeddings list where each item has .values list
                batch_embeddings = [emb.values for emb in response.embeddings]
                embeddings.extend(batch_embeddings)
                break
            except APIError as e:
                logger.warning(f"API Error during embedding generation (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise e
                time.sleep(retry_delay * (attempt + 1))
            except Exception as e:
                logger.error(f"Unexpected error during embedding generation: {e}")
                raise e
                
    logger.info(f"Successfully generated {len(embeddings)} embeddings.")
    return embeddings
