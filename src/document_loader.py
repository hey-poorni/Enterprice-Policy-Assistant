import pypdf
from pathlib import Path
from typing import List, Dict, Any
from src.utils import get_logger

logger = get_logger("document_loader")

def load_pdf_document(file_path: Path, relative_path: str) -> List[Dict[str, Any]]:
    """
    Reads a single PDF file and extracts text page-by-page.
    Each returned page contains a dict with keys: 'text', 'page_num', 'source', 'department'.
    """
    pages_data = []
    # Identify department from parent folder name
    # e.g. HR, IT, Security, SOPs, etc. If it is in the root, department = "General"
    parts = Path(relative_path).parts
    department = parts[0] if len(parts) > 1 else "General"
    
    try:
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            num_pages = len(reader.pages)
            logger.info(f"Loading '{relative_path}' ({num_pages} pages) for department '{department}'")
            
            for page_idx in range(num_pages):
                page = reader.pages[page_idx]
                text = page.extract_text()
                
                # Simple cleaning of text
                if text:
                    text_clean = clean_text(text)
                else:
                    text_clean = ""
                
                pages_data.append({
                    "text": text_clean,
                    "page_num": page_idx + 1,
                    "source": relative_path,
                    "department": department
                })
    except Exception as e:
        logger.error(f"Failed to load PDF document at {file_path}: {e}")
        
    return pages_data

def clean_text(text: str) -> str:
    """Cleans text extracted from PDF to remove excess whitespaces, weird symbols, etc."""
    if not text:
        return ""
    # Replace multiple spaces with a single space
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        cleaned_line = " ".join(line.split())
        if cleaned_line:
            cleaned_lines.append(cleaned_line)
    return "\n".join(cleaned_lines)

def load_all_policies(policies_dir: Path) -> List[Dict[str, Any]]:
    """
    Scans policies_dir recursively and loads all PDF files.
    Returns a flat list of page dictionaries.
    """
    all_pages = []
    if not policies_dir.exists():
        logger.warning(f"Policies directory {policies_dir} does not exist.")
        return all_pages
        
    for file_path in policies_dir.rglob("*.pdf"):
        if file_path.is_file():
            rel_path = file_path.relative_to(policies_dir).as_posix()
            pages_data = load_pdf_document(file_path, rel_path)
            all_pages.extend(pages_data)
            
    logger.info(f"Loaded a total of {len(all_pages)} pages from policy documents.")
    return all_pages
