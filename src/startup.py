import json
from pathlib import Path
from typing import Callable, Optional
import config
from src.utils import get_logger, scan_policy_directory
from src.document_loader import load_all_policies
from src.chunking import chunk_documents
from src.embeddings import generate_embeddings
from src.vector_store import HybridVectorStore

logger = get_logger("startup")

def check_need_rebuild(current_scan: dict, metadata_path: Path, faiss_path: Path, chunks_path: Path) -> bool:
    """
    Compares current scan metadata with stored metadata on disk.
    Returns True if any file has been added, removed, or modified, or if index files are missing.
    """
    # 1. Check if index files exist on disk
    if not faiss_path.exists() or not chunks_path.exists() or not metadata_path.exists():
        logger.info("Missing index or metadata files. Rebuild required.")
        return True
        
    # 2. Try loading stored metadata
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            stored_metadata = json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read stored metadata: {e}. Rebuild required.")
        return True
        
    # 3. Compare file sets
    if set(current_scan.keys()) != set(stored_metadata.keys()):
        logger.info("Set of policy documents has changed. Rebuild required.")
        return True
        
    # 4. Compare file details (hash, size)
    for rel_path, current_details in current_scan.items():
        stored_details = stored_metadata[rel_path]
        if current_details["hash"] != stored_details["hash"]:
            logger.info(f"File modified (hash mismatch): {rel_path}. Rebuild required.")
            return True
        # Allow slight modification time mismatch but check file size as a safety measure
        if current_details["size"] != stored_details["size"]:
            logger.info(f"File size mismatch: {rel_path}. Rebuild required.")
            return True
            
    logger.info("No modifications detected. Index is up to date.")
    return False

def initialize_knowledge_base(
    store: HybridVectorStore,
    progress_callback: Optional[Callable[[str], None]] = None
) -> bool:
    """
    Determines whether a vector database already exists and is up to date.
    Loads it directly if valid, or rebuilds it from scratch if needed.
    Runs updates through an optional callback to display progress on UI.
    """
    def report_progress(msg: str):
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)

    # Make sure target directory structure exists
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Scan policies directory
    current_scan = scan_policy_directory(config.DATA_DIR)
    
    # Check if empty folder
    if not current_scan:
        report_progress("The policy folder is currently empty. Please place PDF files in the policies folders.")
        logger.warning("Empty policy folder detected.")
        raise ValueError("The policy directory is empty. Please place company policy PDF files inside the data/policies/ directory.")
        
    # 2. Check if index needs to be rebuilt
    need_rebuild = check_need_rebuild(
        current_scan,
        config.METADATA_PATH,
        config.FAISS_INDEX_PATH,
        config.CHUNKS_PATH
    )
    
    if not need_rebuild:
        # Load index files from disk
        report_progress("Organizing policy information...")
        success = store.load(config.FAISS_INDEX_PATH, config.CHUNKS_PATH)
        if success:
            report_progress("Enterprise knowledge base is ready.")
            return True
        else:
            report_progress("Failed to load existing knowledge base. Rebuilding...")
            
    # 3. Rebuild the database
    report_progress("Reading company documents...")
    pages_data = load_all_policies(config.DATA_DIR)
    
    if not pages_data:
        report_progress("No readable content found in policies. Rebuilding failed.")
        raise ValueError("No readable text content could be extracted from the PDF policy files.")
        
    report_progress("Organizing policy information...")
    chunks = chunk_documents(pages_data, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
    
    if not chunks:
        report_progress("No text chunks generated. Rebuilding failed.")
        raise ValueError("Document text splitting generated zero chunks. Rebuilding failed.")
        
    report_progress("Building enterprise knowledge base...")
    # Get chunk texts for embedding generation
    chunk_texts = [chunk["formatted_text"] for chunk in chunks]
    embeddings = generate_embeddings(chunk_texts)
    
    # Build FAISS index and BM25 in memory
    store.build_index(chunks, embeddings)
    
    # Save indices to disk
    store.save(config.FAISS_INDEX_PATH, config.CHUNKS_PATH)
    
    # Save scanned metadata
    with open(config.METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(current_scan, f, ensure_ascii=False, indent=2)
        
    report_progress("Enterprise knowledge base is ready.")
    return True
