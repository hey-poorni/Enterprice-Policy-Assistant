import hashlib
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Ensure stdout supports UTF-8 encoding on Windows console streams
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("EnterprisePolicyAssistant")

def get_logger(name: str) -> logging.Logger:
    """Returns a logger instance with the given name."""
    return logging.getLogger(f"EnterprisePolicyAssistant.{name}")

def calculate_file_hash(file_path: Path) -> str:
    """Calculates the MD5 hash of a file for change tracking."""
    hasher = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {e}")
        return ""

def scan_policy_directory(directory: Path) -> Dict[str, Dict[str, Any]]:
    """
    Scans the policy directory recursively for PDF files and collects metadata.
    Returns a dictionary mapping relative paths to details: hash, mtime, size.
    """
    scan_results = {}
    if not directory.exists():
        return scan_results
    
    for file_path in directory.rglob("*.pdf"):
        if file_path.is_file():
            # Get relative path for clean dictionary keys
            rel_path = file_path.relative_to(directory).as_posix()
            try:
                stat = file_path.stat()
                scan_results[rel_path] = {
                    "hash": calculate_file_hash(file_path),
                    "mtime": stat.st_mtime,
                    "size": stat.st_size
                }
            except Exception as e:
                logger.error(f"Error reading file stats for {file_path}: {e}")
                
    return scan_results
