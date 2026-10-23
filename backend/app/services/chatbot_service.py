"""Hospital Chatbot Service with RAG."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from typing import Dict, List, Optional
from app.core.logging import get_logger
from app.core.config import settings
from app.ai.llm.factory import llm_provider
from rag.embeddings import EmbeddingService
from rag.retriever import FAISSRetriever
from rag.prompts import HOSPITAL_CHATBOT_SYSTEM, HOSPITAL_CHATBOT_USER

logger = get_logger(__name__)

class ChatbotService:
    def __init__(self):
        self.embedding_service = None
        self.retriever = None
        self._loaded = False
    
    def load(self):
        try:
            self.embedding_service = EmbeddingService(model_name=settings.EMBEDDING_MODEL)
            self.embedding_service.load()
            self.retriever = FAISSRetriever(settings.FAISS_INDEX_DIR)
            self._loaded = self.retriever.load()
            if self._loaded:
                logger.info('Chatbot RAG pipeline loaded')
            else:
                logger.warning('RAG index not found - run build_rag_index.py first')
        except Exception as e:
            logger.error(f'Failed to load chatbot: {e}')
    
    def chat(self, message: str, history: List[Dict] = None) -> Dict:
        if not self._loaded:
            self.load()
        
        # Retrieve relevant context
        sources = []
        context = 'No context available.'
        if self._loaded and self.embedding_service:
            query_emb = self.embedding_service.encode_query(message)
            results = self.retriever.search(query_emb, top_k=settings.RETRIEVAL_TOP_K)
            if results:
                context = '\n\n'.join([r['content'] for r in results])
                sources = [{'source': r['source'], 'score': r['score']} for r in results]
        
        # Format history
        history_text = ''
        if history:
            for msg in history[-5:]:  # Last 5 messages
                role = 'Patient' if msg.get('role') == 'user' else 'Assistant'
                history_text += f'{role}: {msg.get("content", "")}\n'
        
        # Generate response
        try:
            prompt = HOSPITAL_CHATBOT_SYSTEM.format(context=context, history=history_text)
            full_prompt = f'{prompt}\n\nPatient: {message}\n\nAssistant:'
            response = llm_provider.generate(full_prompt, context={'type': 'chatbot'})
        except Exception as e:
            logger.error(f'LLM generation failed: {e}')
            if sources:
                response = f'Based on hospital information: {context[:500]}...'
            else:
                response = "I'm having trouble processing your request. Please try again or contact the hospital directly."
        
        return {
            'response': response,
            'sources': sources
        }
    
    @property
    def is_available(self):
        return self._loaded

chatbot_service = ChatbotService()
