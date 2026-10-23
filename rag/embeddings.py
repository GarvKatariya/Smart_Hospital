"""Embedding generation for RAG."""
import numpy as np
from typing import List
from app.core.logging import get_logger

logger = get_logger(__name__)

class EmbeddingService:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = None
        self.model_name = model_name
        self._loaded = False
    
    def load(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            self._loaded = True
            logger.info(f'Embedding model {self.model_name} loaded')
        except Exception as e:
            logger.error(f'Failed to load embedding model: {e}')
    
    def encode(self, texts: List[str]) -> np.ndarray:
        if not self._loaded:
            self.load()
        if not self._loaded:
            raise RuntimeError('Embedding model not available')
        return self.model.encode(texts, normalize_embeddings=True)
    
    def encode_query(self, query: str) -> np.ndarray:
        return self.encode([query])[0]
