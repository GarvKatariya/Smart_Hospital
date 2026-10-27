from google import genai
from .provider import LLMProvider
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class GeminiProvider(LLMProvider):
    def __init__(self):
        self._available = False
        if settings.GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
                self.model = 'gemini-3.6-flash'
                self._available = True
                logger.info('Gemini LLM provider initialized')
            except Exception as e:
                logger.warning(f'Failed to initialize Gemini: {e}')
    
    def generate(self, prompt, context=None):
        if not self._available:
            raise RuntimeError('Gemini provider not available')
        response = self.client.models.generate_content(model=self.model, contents=prompt)
        return response.text
    
    def is_available(self):
        return self._available
