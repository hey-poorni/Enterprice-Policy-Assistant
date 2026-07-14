import json
import numpy as np
import faiss
from pathlib import Path
from typing import List, Dict, Any, Tuple
from rank_bm25 import BM25Okapi
import config
from src.utils import get_logger
from src.embeddings import generate_embeddings

logger = get_logger("vector_store")

class HybridVectorStore:
    def __init__(self):
        self.index = None
        self.chunks: List[Dict[str, Any]] = []
        self.bm25 = None
        self.dimension = 768  # text-embedding-004 embedding size

    def build_index(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        """
        Builds both the FAISS index and the BM25 index in memory.
        """
        logger.info(f"Building hybrid index for {len(chunks)} chunks.")
        self.chunks = chunks
        
        # 1. Build FAISS index
        embeddings_np = np.array(embeddings).astype('float32')
        # Check dimensions
        if embeddings_np.shape[1] != self.dimension:
            logger.warning(f"Embedding dimension mismatch. Expected {self.dimension}, got {embeddings_np.shape[1]}. Updating store dimension.")
            self.dimension = embeddings_np.shape[1]
            
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner Product (Cosine Similarity if normalized)
        # Normalize embeddings for Cosine Similarity
        faiss.normalize_L2(embeddings_np)
        self.index.add(embeddings_np)
        
        # 2. Build BM25 index
        self._initialize_bm25()
        logger.info("Successfully built hybrid index (FAISS FlatIP and BM25Okapi).")

    def _initialize_bm25(self):
        """Initializes BM25 index using the current chunks."""
        if not self.chunks:
            self.bm25 = None
            return
            
        # Tokenize chunk texts for BM25 (lowercased word tokens)
        tokenized_corpus = [self._tokenize(chunk["text"]) for chunk in self.chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)
        logger.info("Initialized BM25 index.")

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenizer that splits text into lowercased words."""
        # Remove common punctuation and convert to lowercase
        cleaned = "".join([char.lower() if char.isalnum() or char.isspace() else " " for char in text])
        return [word for word in cleaned.split() if len(word) > 1]

    def save(self, index_path: Path, chunks_path: Path):
        """Saves the FAISS index and chunk texts to disk."""
        if self.index is None or not self.chunks:
            logger.error("Cannot save empty vector store.")
            return
            
        try:
            # Create parents directories
            index_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save FAISS index
            faiss.write_index(self.index, str(index_path))
            
            # Save chunks metadata
            with open(chunks_path, "w", encoding="utf-8") as f:
                json.dump(self.chunks, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Saved FAISS index to {index_path} and chunks to {chunks_path}")
        except Exception as e:
            logger.error(f"Error saving vector store: {e}")
            raise e

    def load(self, index_path: Path, chunks_path: Path) -> bool:
        """Loads the FAISS index and chunk texts from disk, then initializes BM25 in memory."""
        if not index_path.exists() or not chunks_path.exists():
            logger.warning("FAISS index or chunks file does not exist on disk.")
            return False
            
        try:
            logger.info(f"Loading FAISS index from {index_path}")
            self.index = faiss.read_index(str(index_path))
            
            logger.info(f"Loading chunks from {chunks_path}")
            with open(chunks_path, "r", encoding="utf-8") as f:
                self.chunks = json.load(f)
                
            # Initialize BM25 search index in memory
            self._initialize_bm25()
            return True
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            return False

    def search_semantic(self, query: str, top_n: int = 20) -> List[Tuple[int, float]]:
        """Performs semantic search on FAISS and returns a list of (chunk_index, score)."""
        if self.index is None or not self.chunks:
            logger.warning("FAISS index is not initialized.")
            return []
            
        try:
            # Generate embedding for the query
            query_emb = generate_embeddings([query])[0]
            query_np = np.array([query_emb]).astype('float32')
            faiss.normalize_L2(query_np)
            
            # Search
            k = min(top_n, len(self.chunks))
            distances, indices = self.index.search(query_np, k)
            
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx != -1:  # FAISS returns -1 for empty slots or failures
                    results.append((int(idx), float(dist)))
            return results
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []

    def search_keyword(self, query: str, top_n: int = 20) -> List[Tuple[int, float]]:
        """Performs keyword search on BM25 and returns a list of (chunk_index, score)."""
        if self.bm25 is None or not self.chunks:
            logger.warning("BM25 index is not initialized.")
            return []
            
        try:
            tokenized_query = self._tokenize(query)
            # Get raw scores
            scores = self.bm25.get_scores(tokenized_query)
            # Find indices of top_n items sorted by score descending
            top_indices = np.argsort(scores)[::-1][:top_n]
            
            results = []
            for idx in top_indices:
                if scores[idx] > 0.0:  # Only return matching documents
                    results.append((int(idx), float(scores[idx])))
            return results
        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            return []

    def search_hybrid(self, query: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Combines semantic and keyword search using Reciprocal Rank Fusion (RRF).
        Returns the top_n combined chunks with their metadata.
        """
        if not self.chunks:
            logger.warning("No chunks available to search.")
            return []
            
        # Get candidates (top 20) from both search engines
        semantic_results = self.search_semantic(query, top_n=20)
        keyword_results = self.search_keyword(query, top_n=20)
        
        # Reciprocal Rank Fusion (RRF)
        # RRF_Score = Sum( 1 / (60 + rank) )
        k = 60
        rrf_scores = {}
        
        # Process semantic ranks
        for rank, (idx, _) in enumerate(semantic_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + (1.0 / (k + rank + 1))
            
        # Process keyword ranks
        for rank, (idx, _) in enumerate(keyword_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + (1.0 / (k + rank + 1))
            
        # Sort chunks by final RRF score in descending order
        sorted_indices = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        # Retrieve the top_n chunks
        selected_chunks = []
        for idx in sorted_indices[:top_n]:
            chunk_info = self.chunks[idx].copy()
            # Include RRF score for reference if needed
            chunk_info["rrf_score"] = rrf_scores[idx]
            selected_chunks.append(chunk_info)
            
        # Fallback to pure semantic search if BM25 didn't find matches and RRF list is short
        if len(selected_chunks) < top_n and semantic_results:
            for idx, _ in semantic_results:
                if idx not in rrf_scores:
                    chunk_info = self.chunks[idx].copy()
                    chunk_info["rrf_score"] = 0.0
                    selected_chunks.append(chunk_info)
                    if len(selected_chunks) >= top_n:
                        break
                        
        logger.info(f"Hybrid search retrieved {len(selected_chunks)} chunks for query: '{query}'")
        return selected_chunks[:top_n]
