import google.generativeai as genai
from .provider import LLMProvider
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class GeminiProvider(LLMProvider):
    def __init__(self):
        self._available = False
        if settings.GEMINI_API_KEY:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.model = genai.GenerativeModel('gemini-2.0-flash')
                self._available = True
                logger.info('Gemini LLM provider initialized')
            except Exception as e:
                logger.warning(f'Failed to initialize Gemini: {e}')
    
    def generate(self, prompt, context=None):
        if not self._available:
            raise RuntimeError('Gemini provider not available')
        response = self.model.generate_content(prompt)
        return response.text
    
    def is_available(self):
        return self._available
