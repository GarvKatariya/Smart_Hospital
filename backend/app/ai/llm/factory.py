from app.core.config import settings
from app.core.logging import get_logger
from .provider import LLMProvider

logger = get_logger(__name__)

def get_llm_provider() -> LLMProvider:
    if settings.GEMINI_API_KEY and getattr(settings, 'LLM_PROVIDER', 'gemini') == 'gemini':
        try:
            from .gemini import GeminiProvider
            provider = GeminiProvider()
            if provider.is_available():
                logger.info('Using Gemini LLM provider')
                return provider
        except Exception as e:
            logger.warning(f'Failed to create Gemini provider: {e}')
    
    # Fallback to mock
    logger.info('Using Mock LLM provider (demo mode)')
    from .mock import MockLLMProvider
    return MockLLMProvider()

# Singleton
llm_provider = get_llm_provider()
