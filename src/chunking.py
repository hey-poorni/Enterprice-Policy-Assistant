from typing import List, Dict, Any
from src.utils import get_logger

logger = get_logger("chunking")

def split_text_into_chunks(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Splits a single text string into overlapping chunks based on character length."""
    if not text:
        return []
        
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += (chunk_size - chunk_overlap)
        
    return chunks

def chunk_documents(pages: List[Dict[str, Any]], chunk_size: int, chunk_overlap: int) -> List[Dict[str, Any]]:
    """
    Chunks a list of extracted pages into smaller text segments while preserving metadata.
    Each chunk is represented as a dictionary:
    - 'chunk_id': unique string identifier.
    - 'text': the actual text content of the chunk.
    - 'formatted_text': text with source prefix for indexing.
    - 'source': source PDF relative path.
    - 'page_num': page number of the source document.
    - 'department': department folder name.
    """
    logger.info(f"Chunking {len(pages)} pages with size={chunk_size}, overlap={chunk_overlap}")
    all_chunks = []
    chunk_counter = 0
    
    for page in pages:
        text = page["text"]
        if not text.strip():
            continue
            
        chunks = split_text_into_chunks(text, chunk_size, chunk_overlap)
        
        for idx, chunk in enumerate(chunks):
            # Prepend metadata to the chunk text to give the embedding model contextual awareness of document info
            source_info = f"Document: {page['source']} | Department: {page['department']} | Page: {page['page_num']}"
            formatted_text = f"[{source_info}]\n{chunk}"
            
            all_chunks.append({
                "chunk_id": f"{page['source'].replace('/', '_')}_p{page['page_num']}_c{idx}",
                "text": chunk,
                "formatted_text": formatted_text,
                "source": page["source"],
                "page_num": page["page_num"],
                "department": page["department"]
            })
            chunk_counter += 1
            
    logger.info(f"Generated {len(all_chunks)} chunks from document pages.")
    return all_chunks
