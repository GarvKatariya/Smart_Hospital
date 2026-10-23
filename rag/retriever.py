"""FAISS-based retriever for RAG."""
import faiss
import numpy as np
import json
import os
from typing import List, Dict, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)

class FAISSRetriever:
    def __init__(self, index_dir: str):
        self.index = None
        self.chunks_metadata = []
        self.index_dir = index_dir
        self._loaded = False
    
    def build_index(self, embeddings: np.ndarray, chunks: List[Dict]):
        """Build FAISS index from embeddings."""
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity for normalized vectors)
        self.index.add(embeddings.astype(np.float32))
        self.chunks_metadata = chunks
        logger.info(f'Built FAISS index with {len(chunks)} chunks, dim={dimension}')
    
    def save(self):
        os.makedirs(self.index_dir, exist_ok=True)
        faiss.write_index(self.index, os.path.join(self.index_dir, 'hospital.faiss'))
        with open(os.path.join(self.index_dir, 'chunks_metadata.json'), 'w') as f:
            json.dump(self.chunks_metadata, f, indent=2)
        logger.info(f'Index saved to {self.index_dir}')
    
    def load(self) -> bool:
        try:
            index_path = os.path.join(self.index_dir, 'hospital.faiss')
            meta_path = os.path.join(self.index_dir, 'chunks_metadata.json')
            if not os.path.exists(index_path):
                return False
            self.index = faiss.read_index(index_path)
            with open(meta_path) as f:
                self.chunks_metadata = json.load(f)
            self._loaded = True
            logger.info(f'FAISS index loaded: {self.index.ntotal} vectors')
            return True
        except Exception as e:
            logger.error(f'Failed to load index: {e}')
            return False
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
        if not self._loaded:
            return []
        query = query_embedding.reshape(1, -1).astype(np.float32)
        scores, indices = self.index.search(query, top_k)
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.chunks_metadata) and idx >= 0:
                result = self.chunks_metadata[idx].copy()
                result['score'] = float(scores[0][i])
                results.append(result)
        return results
